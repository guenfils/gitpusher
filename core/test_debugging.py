"""Incident inbox, repository analysis, and deterministic test-plan runner."""
from __future__ import annotations

import json
import os
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path


MAX_INCIDENTS = 50
MAX_PLAN_STEPS = 12
MAX_REPAIR_ATTEMPTS = 5
APP_ROOT = Path(__file__).resolve().parent.parent
REPAIR_AGENT_PATH = APP_ROOT / "core" / "repair_agent.py"
DEFAULT_REPAIR_COMMAND_TEMPLATE = (
    f"python3 {shlex.quote(str(REPAIR_AGENT_PATH))} "
    "--repo {repo_path} --context {context_file}"
)
SKIP_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
    ".next",
    ".turbo",
    ".idea",
    ".vscode",
    "coverage",
}

LANGUAGE_BY_SUFFIX = {
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".py": "Python",
    ".java": "Java",
    ".go": "Go",
    ".rs": "Rust",
    ".php": "PHP",
    ".rb": "Ruby",
    ".cs": "C#",
}

SCRIPT_CATEGORIES = {
    "lint": {"lint", "eslint"},
    "typecheck": {"typecheck", "type-check", "check-types", "types", "tsc"},
    "test": {"test", "test:unit", "unit", "test:ci"},
    "build": {"build"},
}


class TestDebugSystem:
    def __init__(self):
        self._active_process = None

    def default_repair_command_template(self):
        return DEFAULT_REPAIR_COMMAND_TEMPLATE

    # ---------- Incidents ----------

    def list_incidents(self, root_dir, limit=MAX_INCIDENTS):
        root = Path(root_dir).expanduser()
        incidents = []
        if not root.exists():
            return incidents

        for project_dir in sorted(root.iterdir(), reverse=True):
            if not project_dir.is_dir():
                continue
            for deployment_dir in sorted(project_dir.iterdir(), reverse=True):
                if not deployment_dir.is_dir():
                    continue
                record = self._load_incident_record(project_dir, deployment_dir)
                if record:
                    incidents.append(record)

        incidents.sort(
            key=lambda item: item.get("sort_key") or "",
            reverse=True,
        )
        return incidents[: max(1, int(limit or MAX_INCIDENTS))]

    def _load_incident_record(self, project_dir, deployment_dir):
        json_candidates = [
            path
            for path in deployment_dir.glob("*.json")
            if path.name != "latest.json"
        ]
        json_candidates.sort(
            key=lambda path: path.stat().st_mtime if path.exists() else 0,
            reverse=True,
        )
        payload_path = json_candidates[0] if json_candidates else None
        if payload_path is None:
            latest_path = deployment_dir / "latest.json"
            if latest_path.exists():
                payload_path = latest_path
        if payload_path is None:
            return None

        payload = self._read_json(payload_path)
        if not isinstance(payload, dict):
            return None

        developer_logs = payload.get("developerLogs") or {}
        deployment = payload.get("deployment") or {}
        status = str(
            developer_logs.get("status")
            or deployment.get("status")
            or ""
        ).upper()
        if status != "FAILED":
            return None

        logs = developer_logs.get("logs") or []
        summary = str(payload.get("summary") or "").strip()
        if not summary:
            summary = self._summarize_logs(logs)

        exported_at = (
            str(payload.get("exportedAt") or "").strip()
            or self._iso_from_timestamp(payload_path.stat().st_mtime)
        )

        log_path = self._resolve_related_file(deployment_dir, payload_path.stem, ".log")
        summary_path = self._resolve_related_file(deployment_dir, payload_path.stem, ".summary.txt")

        return {
            "id": f"{project_dir.name}:{deployment_dir.name}:{payload_path.name}",
            "project_id": str(developer_logs.get("projectId") or project_dir.name),
            "project_name": str(developer_logs.get("projectName") or deployment.get("projectName") or "").strip(),
            "project_slug": str(developer_logs.get("projectSlug") or "").strip(),
            "deployment_id": str(developer_logs.get("deploymentId") or deployment.get("id") or deployment_dir.name),
            "environment_slug": str(
                (developer_logs.get("environment") or {}).get("slug")
                or (deployment.get("environment") or {}).get("slug")
                or ""
            ).strip(),
            "status": status,
            "summary": summary,
            "git_commit_sha": str(developer_logs.get("gitCommitSha") or deployment.get("gitCommitSha") or "").strip(),
            "exported_at": exported_at,
            "log_count": len(logs),
            "payload_path": str(payload_path),
            "log_path": str(log_path) if log_path else "",
            "summary_path": str(summary_path) if summary_path else "",
            "deployment_dir": str(deployment_dir),
            "payload": payload,
            "sort_key": exported_at,
        }

    def _resolve_related_file(self, deployment_dir, stem, suffix):
        candidate = deployment_dir / f"{stem}{suffix}"
        if candidate.exists():
            return candidate
        matches = sorted(deployment_dir.glob(f"*{suffix}"), key=lambda path: path.stat().st_mtime, reverse=True)
        return matches[0] if matches else None

    def _read_json(self, path):
        try:
            return json.loads(Path(path).read_text(encoding="utf-8"))
        except Exception:
            return None

    def _iso_from_timestamp(self, timestamp):
        return datetime.utcfromtimestamp(timestamp).isoformat() + "Z"

    def _summarize_logs(self, logs):
        for desired in ("error", "warn", "info"):
            for entry in reversed(list(logs or [])):
                level = str(entry.get("level") or "").lower()
                if level != desired:
                    continue
                message = self.strip_log_tags(str(entry.get("message") or "").strip())
                if message:
                    return message[:240]
        return "No summary available."

    # ---------- Repository analysis ----------

    def analyze_repository(self, repo_path):
        root = Path(repo_path).expanduser()
        if not root.exists():
            return {"ok": False, "error": "Repository path does not exist."}
        if not root.is_dir():
            return {"ok": False, "error": "Repository path is not a folder."}

        package_manager = self._detect_package_manager(root)
        root_manifest = self._read_package_json(root / "package.json")
        workspace_manifests = self._scan_package_manifests(root)
        languages = self._detect_languages(root)
        frameworks = self._detect_frameworks(root_manifest, workspace_manifests)
        architecture = self._detect_architecture(root, root_manifest, workspace_manifests, frameworks)

        dockerfiles = [
            str(path.relative_to(root))
            for path in sorted(root.glob("**/Dockerfile"))
            if not self._contains_skip_dir(path.relative_to(root).parts)
        ][:20]
        github_workflows = [
            str(path.relative_to(root))
            for path in sorted((root / ".github" / "workflows").glob("*.yml"))
        ] if (root / ".github" / "workflows").exists() else []

        plan = self._build_test_plan(root, package_manager, root_manifest, workspace_manifests)

        return {
            "ok": True,
            "repo_path": str(root),
            "repo_name": root.name,
            "is_git_repo": (root / ".git").exists(),
            "package_manager": package_manager,
            "architecture": architecture,
            "languages": languages,
            "frameworks": frameworks,
            "workspace_count": len(workspace_manifests),
            "dockerfiles": dockerfiles,
            "github_workflows": github_workflows,
            "root_scripts": sorted((root_manifest or {}).get("scripts", {}).keys()),
            "plan": plan,
        }

    def _detect_package_manager(self, root):
        if (root / "pnpm-lock.yaml").exists() or (root / "pnpm-workspace.yaml").exists():
            return "pnpm"
        if (root / "bun.lockb").exists() or (root / "bun.lock").exists():
            return "bun"
        if (root / "yarn.lock").exists():
            return "yarn"
        if (root / "package-lock.json").exists():
            return "npm"
        if (root / "requirements.txt").exists() or (root / "pyproject.toml").exists():
            return "python"
        return "unknown"

    def _read_package_json(self, path):
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def _scan_package_manifests(self, root):
        manifests = []
        for current_root, dirs, files in os.walk(root):
            rel_root = Path(current_root).relative_to(root)
            dirs[:] = [item for item in dirs if item not in SKIP_DIRS]
            if "package.json" not in files:
                continue
            manifest_path = Path(current_root) / "package.json"
            payload = self._read_package_json(manifest_path)
            if payload is None:
                continue
            manifests.append(
                {
                    "path": str(rel_root) if str(rel_root) != "." else ".",
                    "manifest_path": str(manifest_path),
                    "name": payload.get("name") or rel_root.name or root.name,
                    "scripts": payload.get("scripts") or {},
                    "dependencies": payload.get("dependencies") or {},
                    "devDependencies": payload.get("devDependencies") or {},
                }
            )
        manifests.sort(key=lambda item: item["path"])
        return manifests[:80]

    def _detect_languages(self, root):
        found = set()
        scanned = 0
        for current_root, dirs, files in os.walk(root):
            dirs[:] = [item for item in dirs if item not in SKIP_DIRS]
            for filename in files:
                suffix = Path(filename).suffix.lower()
                language = LANGUAGE_BY_SUFFIX.get(suffix)
                if language:
                    found.add(language)
                scanned += 1
                if scanned >= 1500:
                    break
            if scanned >= 1500:
                break
        return sorted(found)

    def _detect_frameworks(self, root_manifest, workspace_manifests):
        deps = {}
        for manifest in [root_manifest or {}] + [
            {
                "dependencies": item.get("dependencies") or {},
                "devDependencies": item.get("devDependencies") or {},
            }
            for item in workspace_manifests[:30]
        ]:
            for section in ("dependencies", "devDependencies"):
                deps.update(manifest.get(section) or {})

        detected = []
        markers = [
            ("next", "Next.js"),
            ("react", "React"),
            ("nest", "NestJS"),
            ("@nestjs/core", "NestJS"),
            ("express", "Express"),
            ("fastify", "Fastify"),
            ("prisma", "Prisma"),
            ("typeorm", "TypeORM"),
            ("sequelize", "Sequelize"),
            ("pytest", "Pytest"),
            ("django", "Django"),
            ("fastapi", "FastAPI"),
            ("flask", "Flask"),
        ]
        for dependency, label in markers:
            if dependency in deps and label not in detected:
                detected.append(label)
        return detected

    def _detect_architecture(self, root, root_manifest, workspace_manifests, frameworks):
        is_monorepo = (root / "pnpm-workspace.yaml").exists() or (root / "turbo.json").exists()
        app_like_manifests = [
            item
            for item in workspace_manifests
            if item["path"] != "." and item["path"].split(os.sep)[0] in {"apps", "packages", "services"}
        ]
        has_frontend = any(item in frameworks for item in ("Next.js", "React"))
        has_backend = any(item in frameworks for item in ("NestJS", "Express", "Fastify", "Django", "FastAPI", "Flask"))

        if is_monorepo or len(app_like_manifests) >= 2:
            return "monorepo"
        if has_frontend and has_backend:
            return "fullstack"
        if has_frontend:
            return "frontend-only"
        if has_backend:
            return "backend-only"
        if root_manifest:
            return "single-service"
        return "unknown"

    def _build_test_plan(self, root, package_manager, root_manifest, workspace_manifests):
        steps = []
        steps.extend(
            self._steps_from_manifest(
                package_manager,
                ".",
                root_manifest or {},
                prefer_root=True,
            )
        )

        existing_categories = {step["category"] for step in steps}
        for manifest in workspace_manifests:
            if len(steps) >= MAX_PLAN_STEPS:
                break
            if manifest["path"] == ".":
                continue
            workspace_steps = self._steps_from_manifest(
                package_manager,
                manifest["path"],
                manifest,
                prefer_root=False,
            )
            for step in workspace_steps:
                if len(steps) >= MAX_PLAN_STEPS:
                    break
                if step["category"] in existing_categories and manifest["path"].startswith("packages"):
                    continue
                steps.append(step)
                existing_categories.add(step["category"])

        if package_manager == "python" and not steps:
            if (root / "pytest.ini").exists() or (root / "tests").exists():
                steps.append(
                    {
                        "name": "Pytest",
                        "category": "test",
                        "command": "pytest",
                        "scope": "repo",
                        "reason": "Detected Python test configuration.",
                    }
                )

        return steps

    def _steps_from_manifest(self, package_manager, relative_path, manifest, prefer_root=False):
        scripts = manifest.get("scripts") or {}
        steps = []
        for category, variants in SCRIPT_CATEGORIES.items():
            script_name = self._find_script_name(scripts, variants)
            if not script_name:
                continue
            scope_name = "repo" if relative_path == "." else relative_path
            command = self._build_script_command(package_manager, relative_path, script_name)
            if not command:
                continue
            label = script_name if prefer_root else f"{scope_name}: {script_name}"
            steps.append(
                {
                    "name": label,
                    "category": category,
                    "command": command,
                    "scope": scope_name,
                    "reason": f"Detected '{script_name}' script in {scope_name}.",
                }
            )
        return steps

    def _find_script_name(self, scripts, candidates):
        for candidate in candidates:
            if candidate in scripts:
                return candidate
        return None

    def _build_script_command(self, package_manager, relative_path, script_name):
        target = "." if relative_path in ("", ".") else relative_path
        quoted_target = shlex.quote(target)
        quoted_script = shlex.quote(script_name)
        if package_manager == "pnpm":
            if target == ".":
                return f"pnpm {quoted_script}"
            return f"pnpm --dir {quoted_target} run {quoted_script}"
        if package_manager == "npm":
            if target == ".":
                return f"npm run {quoted_script}"
            return f"npm --prefix {quoted_target} run {quoted_script}"
        if package_manager == "yarn":
            if target == ".":
                return f"yarn run {quoted_script}"
            return f"yarn --cwd {quoted_target} run {quoted_script}"
        if package_manager == "bun":
            if target == ".":
                return f"bun run {quoted_script}"
            return f"bun --cwd {quoted_target} run {quoted_script}"
        return None

    def _contains_skip_dir(self, parts):
        return any(part in SKIP_DIRS for part in parts)

    # ---------- Execution ----------

    def run_plan(self, repo_path, steps, on_event, stop_event=None):
        root = Path(repo_path).expanduser()
        if not root.exists():
            on_event({"type": "runner_error", "message": "Repository path does not exist."})
            return {"ok": False, "results": []}

        results = []
        for index, step in enumerate(steps, start=1):
            if stop_event and stop_event.is_set():
                on_event({"type": "run_stopped", "message": "Execution stopped by user."})
                return {"ok": False, "results": results}

            command = step["command"]
            on_event(
                {
                    "type": "step_started",
                    "message": f"[{index}/{len(steps)}] {step['name']} -> {command}",
                    "step": step,
                }
            )
            run_result = self._run_streaming_command(
                root,
                command,
                on_output=lambda line: on_event(
                    {"type": "step_output", "message": line, "step": step}
                ),
                stop_event=stop_event,
            )
            success = run_result["ok"]
            results.append(
                {
                    "step": step,
                    "ok": success,
                    "returncode": run_result["returncode"],
                    "output": run_result["output"],
                }
            )
            on_event(
                {
                    "type": "step_finished",
                    "message": f"{step['name']} {'passed' if success else 'failed'} (exit {run_result['returncode']})",
                    "step": step,
                    "ok": success,
                    "returncode": run_result["returncode"],
                }
            )
            if not success:
                on_event({"type": "run_failed", "message": f"Stopped after failing step: {step['name']}"})
                return {"ok": False, "results": results}

        on_event({"type": "run_finished", "message": "Execution plan finished successfully."})
        return {"ok": True, "results": results}

    def start_repair_loop(
        self,
        repo_path,
        incident,
        analysis,
        plan,
        on_event,
        stop_event=None,
        max_attempts=3,
        repair_command_template="",
    ):
        root = Path(repo_path).expanduser()
        if not root.exists():
            on_event({"type": "repair_error", "message": "Repository path does not exist."})
            return {"ok": False, "attempts": 0}
        if not plan:
            on_event({"type": "repair_error", "message": "Execution plan is empty."})
            return {"ok": False, "attempts": 0}

        attempts_limit = max(1, min(MAX_REPAIR_ATTEMPTS, int(max_attempts or 1)))
        repair_dir = Path(incident.get("deployment_dir") or root / ".git-pusher-repair")
        repair_dir = repair_dir / "repair-loop"
        repair_dir.mkdir(parents=True, exist_ok=True)

        snapshot = self.create_safety_snapshot(root, label="test-debug")
        if snapshot.get("ok"):
            on_event(
                {
                    "type": "repair_snapshot",
                    "message": f"Safety snapshot created: {snapshot['branch']} | {snapshot['tag']}",
                    "snapshot": snapshot,
                }
            )
        else:
            on_event(
                {
                    "type": "repair_snapshot_skipped",
                    "message": f"Safety snapshot skipped: {snapshot.get('reason')}",
                    "snapshot": snapshot,
                }
            )

        last_context = None
        for attempt in range(1, attempts_limit + 1):
            if stop_event and stop_event.is_set():
                on_event({"type": "repair_stopped", "message": "Repair loop stopped by user."})
                return {
                    "ok": False,
                    "attempts": attempt - 1,
                    "snapshot": snapshot,
                    "repair_dir": str(repair_dir),
                }

            on_event(
                {
                    "type": "repair_attempt_started",
                    "message": f"Repair attempt {attempt}/{attempts_limit}: running validation plan",
                    "attempt": attempt,
                }
            )
            result = self.run_plan(root, plan, on_event, stop_event=stop_event)
            if result.get("ok"):
                on_event(
                    {
                        "type": "repair_success",
                        "message": f"Repair loop completed successfully on attempt {attempt}.",
                        "attempt": attempt,
                    }
                )
                return {
                    "ok": True,
                    "attempts": attempt,
                    "snapshot": snapshot,
                    "repair_dir": str(repair_dir),
                    "results": result.get("results") or [],
                }

            failed_step = self._find_failed_step(result.get("results") or [])
            context = self._build_repair_context(
                incident=incident,
                analysis=analysis,
                plan=plan,
                snapshot=snapshot,
                attempt=attempt,
                results=result.get("results") or [],
                failed_step=failed_step,
                repo_path=str(root),
            )
            context_paths = self._write_repair_context(repair_dir, context)
            last_context = context_paths
            on_event(
                {
                    "type": "repair_context_ready",
                    "message": f"Repair context written: {context_paths['brief_file']}",
                    "attempt": attempt,
                    "context": context_paths,
                }
            )

            if not str(repair_command_template or "").strip():
                on_event(
                    {
                        "type": "repair_handoff_ready",
                        "message": "Repair command is not configured. Context is ready for manual/AI repair.",
                        "attempt": attempt,
                    }
                )
                return {
                    "ok": False,
                    "handoff_ready": True,
                    "attempts": attempt,
                    "snapshot": snapshot,
                    "repair_dir": str(repair_dir),
                    "context": context_paths,
                    "results": result.get("results") or [],
                }

            repair_command = self._format_repair_command(
                repair_command_template,
                repo_path=str(root),
                context_file=context_paths["context_file"],
                brief_file=context_paths["brief_file"],
                incident_file=incident.get("payload_path") or "",
                project_id=incident.get("project_id") or "",
                deployment_id=incident.get("deployment_id") or "",
            )
            on_event(
                {
                    "type": "repair_command_started",
                    "message": f"Running repair command for attempt {attempt}: {repair_command}",
                    "attempt": attempt,
                }
            )
            repair_run = self._run_streaming_command(
                root,
                repair_command,
                on_output=lambda line: on_event(
                    {
                        "type": "repair_command_output",
                        "message": line,
                        "attempt": attempt,
                    }
                ),
                stop_event=stop_event,
            )
            self._append_text(
                Path(context_paths["command_log_file"]),
                repair_run["output"] + ("\n" if repair_run["output"] else ""),
            )
            if not repair_run["ok"]:
                on_event(
                    {
                        "type": "repair_command_failed",
                        "message": f"Repair command failed on attempt {attempt} (exit {repair_run['returncode']}).",
                        "attempt": attempt,
                    }
                )
                return {
                    "ok": False,
                    "handoff_ready": True,
                    "attempts": attempt,
                    "snapshot": snapshot,
                    "repair_dir": str(repair_dir),
                    "context": context_paths,
                    "results": result.get("results") or [],
                }

        on_event(
            {
                "type": "repair_attempts_exhausted",
                "message": f"Repair loop exhausted {attempts_limit} attempt(s) without reaching green.",
            }
        )
        return {
            "ok": False,
            "handoff_ready": True,
            "attempts": attempts_limit,
            "snapshot": snapshot,
            "repair_dir": str(repair_dir),
            "context": last_context,
        }

    def stop_active_run(self):
        process = self._active_process
        if process and process.poll() is None:
            process.terminate()

    def create_safety_snapshot(self, repo_path, label="repair-loop"):
        root = Path(repo_path).expanduser()
        if not (root / ".git").exists():
            return {"ok": False, "reason": "repository is not a git repo"}

        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        normalized = str(label or "repair-loop").strip().lower().replace(" ", "-")
        branch = f"backup-pre-{normalized}-{stamp}"
        tag = f"safety-pre-{normalized}-{stamp}"
        head = self._git_ref(root, ["git", "rev-parse", "HEAD"])
        if not head:
            return {"ok": False, "reason": "unable to resolve HEAD"}
        branch_result = subprocess.run(
            ["git", "branch", branch, head],
            cwd=str(root),
            capture_output=True,
            text=True,
        )
        if branch_result.returncode != 0:
            return {
                "ok": False,
                "reason": (branch_result.stderr or branch_result.stdout or "failed to create branch").strip(),
            }
        tag_result = subprocess.run(
            ["git", "tag", tag, head],
            cwd=str(root),
            capture_output=True,
            text=True,
        )
        if tag_result.returncode != 0:
            return {
                "ok": False,
                "reason": (tag_result.stderr or tag_result.stdout or "failed to create tag").strip(),
                "branch": branch,
                "head": head,
            }
        return {"ok": True, "branch": branch, "tag": tag, "head": head}

    def _run_streaming_command(self, repo_path, command, on_output, stop_event=None):
        process = subprocess.Popen(
            ["bash", "-lc", command],
            cwd=str(repo_path),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        self._active_process = process
        lines = []
        try:
            for line in iter(process.stdout.readline, ""):
                if stop_event and stop_event.is_set():
                    process.terminate()
                    break
                cleaned = line.rstrip("\n")
                lines.append(cleaned)
                on_output(cleaned)
        finally:
            process.wait()
            self._active_process = None
        interrupted = bool(stop_event and stop_event.is_set())
        return {
            "ok": process.returncode == 0 and not interrupted,
            "returncode": process.returncode,
            "output": "\n".join(lines).strip(),
        }

    def _find_failed_step(self, results):
        for item in results:
            if not item.get("ok"):
                return item
        return results[-1] if results else None

    def _build_repair_context(
        self,
        incident,
        analysis,
        plan,
        snapshot,
        attempt,
        results,
        failed_step,
        repo_path,
    ):
        failed_output = (failed_step or {}).get("output") or ""
        diagnosis = self._classify_failure(
            incident.get("summary") or "",
            failed_output,
            ((failed_step or {}).get("step") or {}).get("category") or "",
        )
        return {
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "attempt": attempt,
            "repoPath": repo_path,
            "incident": {
                "projectId": incident.get("project_id"),
                "projectName": incident.get("project_name"),
                "deploymentId": incident.get("deployment_id"),
                "summary": incident.get("summary"),
                "commitSha": incident.get("git_commit_sha"),
                "payloadPath": incident.get("payload_path"),
                "logPath": incident.get("log_path"),
            },
            "analysis": analysis,
            "plan": plan,
            "snapshot": snapshot,
            "failedStep": failed_step,
            "results": results,
            "diagnosis": diagnosis,
        }

    def _write_repair_context(self, repair_dir, context):
        attempt = context["attempt"]
        prefix = f"attempt-{attempt:02d}"
        context_file = repair_dir / f"{prefix}-context.json"
        brief_file = repair_dir / f"{prefix}-brief.md"
        output_file = repair_dir / f"{prefix}-failed-output.log"
        command_log_file = repair_dir / f"{prefix}-repair-command.log"

        context_file.write_text(json.dumps(context, indent=2), encoding="utf-8")

        failed_output = str(((context.get("failedStep") or {}).get("output")) or "").strip()
        output_file.write_text(failed_output + ("\n" if failed_output else ""), encoding="utf-8")

        brief_lines = [
            f"# Repair Attempt {attempt}",
            "",
            f"- Project: {context['incident'].get('projectName') or context['incident'].get('projectId')}",
            f"- Deployment: {context['incident'].get('deploymentId')}",
            f"- Commit: {context['incident'].get('commitSha') or 'unknown'}",
            f"- Repo: {context.get('repoPath')}",
            f"- Snapshot branch: {((context.get('snapshot') or {}).get('branch')) or 'not-created'}",
            f"- Snapshot tag: {((context.get('snapshot') or {}).get('tag')) or 'not-created'}",
            "",
            "## Failure Diagnosis",
            "",
            f"- Category: {context['diagnosis'].get('category')}",
            f"- Hint: {context['diagnosis'].get('hint')}",
            "",
            "## Failed Step",
            "",
            f"- Name: {(((context.get('failedStep') or {}).get('step')) or {}).get('name') or 'unknown'}",
            f"- Command: {(((context.get('failedStep') or {}).get('step')) or {}).get('command') or 'unknown'}",
            f"- Exit: {(context.get('failedStep') or {}).get('returncode')}",
            "",
            "## Next Action",
            "",
            "Apply a minimal repair for the failed step, then rerun the validation plan.",
            f"Context JSON: {context_file}",
            f"Failed Output: {output_file}",
        ]
        brief_file.write_text("\n".join(brief_lines) + "\n", encoding="utf-8")
        if not command_log_file.exists():
            command_log_file.write_text("", encoding="utf-8")

        return {
            "context_file": str(context_file),
            "brief_file": str(brief_file),
            "output_file": str(output_file),
            "command_log_file": str(command_log_file),
        }

    def _format_repair_command(
        self,
        template,
        repo_path,
        context_file,
        brief_file,
        incident_file,
        project_id,
        deployment_id,
    ):
        values = {
            "repo_path": shlex.quote(repo_path),
            "repo_path_raw": repo_path,
            "context_file": shlex.quote(context_file),
            "context_file_raw": context_file,
            "brief_file": shlex.quote(brief_file),
            "brief_file_raw": brief_file,
            "incident_file": shlex.quote(incident_file),
            "incident_file_raw": incident_file,
            "project_id": shlex.quote(project_id),
            "project_id_raw": project_id,
            "deployment_id": shlex.quote(deployment_id),
            "deployment_id_raw": deployment_id,
            "repair_agent": shlex.quote(str(REPAIR_AGENT_PATH)),
            "repair_agent_raw": str(REPAIR_AGENT_PATH),
            "git_pusher_root": shlex.quote(str(APP_ROOT)),
            "git_pusher_root_raw": str(APP_ROOT),
        }
        return str(template).format_map(values)

    def _classify_failure(self, summary, failed_output, step_category):
        haystack = "\n".join([str(summary or ""), str(failed_output or "")]).lower()
        if "ts" in haystack and "error" in haystack:
            return {
                "category": "typecheck",
                "hint": "TypeScript/type-check failure. Inspect missing types, incompatible signatures, or invalid imports.",
            }
        if "eslint" in haystack or "prettier" in haystack or "lint" in str(step_category).lower():
            return {
                "category": "lint",
                "hint": "Lint failure. Fix formatting, unused variables, or rule violations without changing behavior.",
            }
        if "cannot find module" in haystack or "module not found" in haystack:
            return {
                "category": "dependency",
                "hint": "Dependency/import resolution failure. Check package installation, workspace links, and import paths.",
            }
        if "prisma" in haystack:
            return {
                "category": "prisma",
                "hint": "Prisma/build context failure. Verify schema availability, generated client, and Docker copy order.",
            }
        if "test" in str(step_category).lower() or "expected" in haystack or "assert" in haystack:
            return {
                "category": "tests",
                "hint": "Test failure. Reproduce locally, inspect assertions, fixtures, and environment assumptions.",
            }
        if "docker" in haystack or "build" in str(step_category).lower():
            return {
                "category": "build",
                "hint": "Build failure. Check scripts, build context, environment variables, and generated artifacts.",
            }
        return {
            "category": "unknown",
            "hint": "General failure. Focus first on the failed step output and the deployment summary.",
        }

    def _git_ref(self, repo_path, command):
        result = subprocess.run(command, cwd=str(repo_path), capture_output=True, text=True)
        if result.returncode != 0:
            return ""
        return (result.stdout or "").strip()

    def _append_text(self, path, text):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with Path(path).open("a", encoding="utf-8") as handle:
            handle.write(text)

    # ---------- Formatting ----------

    def format_analysis_summary(self, analysis):
        if not analysis.get("ok"):
            return analysis.get("error", "Analysis failed.")

        lines = [
            f"Repository: {analysis.get('repo_name')}",
            f"Architecture: {analysis.get('architecture')}",
            f"Package manager: {analysis.get('package_manager')}",
            f"Languages: {', '.join(analysis.get('languages') or ['Unknown'])}",
            f"Frameworks: {', '.join(analysis.get('frameworks') or ['Unknown'])}",
            f"Git repo: {'yes' if analysis.get('is_git_repo') else 'no'}",
            f"Workspace manifests: {analysis.get('workspace_count')}",
        ]
        if analysis.get("dockerfiles"):
            lines.append("Dockerfiles: " + ", ".join(analysis["dockerfiles"][:4]))
        if analysis.get("github_workflows"):
            lines.append("CI workflows: " + ", ".join(analysis["github_workflows"][:4]))
        return "\n".join(lines)

    def format_plan(self, plan):
        if not plan:
            return "No automatic checks were detected yet."
        return "\n".join(
            f"{index}. {step['name']}  ->  {step['command']}"
            for index, step in enumerate(plan, start=1)
        )

    def strip_log_tags(self, message):
        cursor = str(message or "")
        while cursor.startswith("["):
            end = cursor.find("]")
            if end <= 1:
                break
            cursor = cursor[end + 1 :].lstrip()
        return cursor or str(message or "")
