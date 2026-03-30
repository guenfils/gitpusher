"""Incident inbox, repository analysis, and deterministic test-plan runner."""
from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import tempfile
import hashlib
from datetime import datetime, timezone
from pathlib import Path

from core.git_manager import GitManager

MAX_INCIDENTS = 50
MAX_PLAN_STEPS = 12
MAX_REPAIR_ATTEMPTS = 5
SAFETY_GATE_CATEGORIES = ("typecheck", "test", "build")
DEFAULT_ALLOWED_PUSH_BRANCHES = ("main", "master", "develop", "staging", "release")
DEFAULT_ALLOWED_PUSH_REMOTES = ("origin", "gitlab")
APPROVAL_QUEUE_ACTIONS = ("repair", "commit", "push")
APP_ROOT = Path(__file__).resolve().parent.parent
REPAIR_AGENT_PATH = APP_ROOT / "core" / "repair_agent.py"
AI_RUNTIMES = {
    "codex": {
        "label": "ChatGPT / Codex",
        "description": "Uses the local Codex CLI session, like VS Code. Git Pusher does not store or send an OpenAI AI API key for this flow.",
        "bin": "codex",
    },
    "claude": {
        "label": "Claude",
        "description": "Uses the local Claude CLI session, like Claude Code. Git Pusher does not store or send an Anthropic AI API key for this flow.",
        "bin": "claude",
    },
}
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

APPROVAL_MODES = {
    "analyze_only": {
        "label": "Analyze Only",
        "description": "Analyze the repository and build the plan only. No repair, commit, or push.",
        "auto_repair": False,
        "auto_commit": False,
        "auto_push": False,
    },
    "repair_only": {
        "label": "Repair Only",
        "description": "Analyze the repository and run the repair loop, but stop before commit.",
        "auto_repair": True,
        "auto_commit": False,
        "auto_push": False,
    },
    "repair_commit": {
        "label": "Repair + Commit",
        "description": "Analyze, repair, and create a safe local commit once the gate is green.",
        "auto_repair": True,
        "auto_commit": True,
        "auto_push": False,
    },
    "repair_push": {
        "label": "Repair + Push",
        "description": "Analyze, repair, commit safely, and push to the selected remotes.",
        "auto_repair": True,
        "auto_commit": True,
        "auto_push": True,
    },
}


class TestDebugSystem:
    def __init__(self):
        self._active_process = None
        self._git = GitManager()
        self._node_runtime = self._discover_node_runtime()
        self._ai_runtimes = self._discover_ai_runtimes()

    def _discover_ai_runtimes(self):
        runtimes = {}
        for key, meta in AI_RUNTIMES.items():
            bin_name = meta.get("bin") or key
            binary = shutil.which(bin_name)
            version = self._safe_capture([binary, "--version"]) if binary else ""
            runtimes[key] = {
                "available": bool(binary),
                "path": binary or "",
                "version": version,
            }
        return runtimes

    def ai_runtime_choices(self):
        return [(key, data["label"]) for key, data in AI_RUNTIMES.items()]

    def default_ai_runtime(self):
        if (self._ai_runtimes.get("codex") or {}).get("available"):
            return "codex"
        if (self._ai_runtimes.get("claude") or {}).get("available"):
            return "claude"
        return "codex"

    def get_ai_runtime(self, value=None):
        key = str(value or "").strip().lower() or self.default_ai_runtime()
        if key not in AI_RUNTIMES:
            key = self.default_ai_runtime()
        runtime = dict(AI_RUNTIMES[key])
        detected = dict(self._ai_runtimes.get(key) or {})
        runtime["key"] = key
        runtime["available"] = bool(detected.get("available"))
        runtime["path"] = str(detected.get("path") or "")
        runtime["version"] = str(detected.get("version") or "")
        return runtime

    def format_ai_runtime_summary(self):
        lines = []
        for key, meta in AI_RUNTIMES.items():
            runtime = self.get_ai_runtime(key)
            status = "available" if runtime.get("available") else "not found"
            details = runtime.get("version") or runtime.get("path") or meta.get("bin") or key
            lines.append(f"- {meta['label']}: {status} ({details})")
        return "\n".join(lines)

    def ai_runtime_summary_inline(self):
        parts = []
        for key, meta in AI_RUNTIMES.items():
            runtime = self.get_ai_runtime(key)
            status = "available" if runtime.get("available") else "not found"
            parts.append(f"{meta['label']}: {status}")
        return " | ".join(parts)

    def default_repair_command_template(self, runtime_key=None):
        runtime = self.get_ai_runtime(runtime_key)
        return (
            f"python3 {shlex.quote(str(REPAIR_AGENT_PATH))} "
            f"--runtime {runtime['key']} --repo {{repo_path}} --context {{context_file}}"
        )

    def default_approval_mode(self):
        return "repair_only"

    def approval_mode_choices(self):
        return [(key, data["label"]) for key, data in APPROVAL_MODES.items()]

    def get_approval_mode(self, value=None):
        key = str(value or "").strip() or self.default_approval_mode()
        if key not in APPROVAL_MODES:
            key = self.default_approval_mode()
        mode = dict(APPROVAL_MODES[key])
        mode["key"] = key
        return mode

    def default_push_policy(self):
        return {
            "allow_auto_push": False,
            "allowed_branches": list(DEFAULT_ALLOWED_PUSH_BRANCHES),
            "allowed_remotes": list(DEFAULT_ALLOWED_PUSH_REMOTES),
            "require_clean_start": True,
        }

    def normalize_push_policy(self, policy=None):
        defaults = self.default_push_policy()
        source = dict(policy or {})
        normalized = {
            "allow_auto_push": bool(source.get("allow_auto_push", defaults["allow_auto_push"])),
            "allowed_branches": self._normalize_csv_list(
                source.get("allowed_branches", defaults["allowed_branches"]),
                fallback=defaults["allowed_branches"],
            ),
            "allowed_remotes": self._normalize_csv_list(
                source.get("allowed_remotes", defaults["allowed_remotes"]),
                fallback=defaults["allowed_remotes"],
            ),
            "require_clean_start": bool(source.get("require_clean_start", defaults["require_clean_start"])),
            "source": str(source.get("source") or "manual").strip() or "manual",
        }
        return normalized

    def _normalize_csv_list(self, value, fallback=None):
        if isinstance(value, (list, tuple, set)):
            items = [str(item).strip() for item in value if str(item).strip()]
        else:
            items = [chunk.strip() for chunk in str(value or "").split(",") if chunk.strip()]
        if items:
            return items
        return [str(item).strip() for item in (fallback or []) if str(item).strip()]

    def _discover_node_runtime(self):
        system_node = shutil.which("node")
        system_npm = shutil.which("npm")
        if system_node and system_npm:
            version = self._safe_capture([system_node, "-v"])
            npm_version = self._safe_capture([system_npm, "-v"])
            return {
                "source": "system-path",
                "bin_dir": str(Path(system_node).resolve().parent),
                "node": system_node,
                "npm": system_npm,
                "node_version": version,
                "npm_version": npm_version,
            }

        candidates = []
        nvm_bin = str(os.environ.get("NVM_BIN") or "").strip()
        if nvm_bin:
            candidates.append(Path(nvm_bin))

        nvm_root = Path(os.environ.get("NVM_DIR") or (Path.home() / ".nvm"))
        versions_root = nvm_root / "versions" / "node"
        if versions_root.exists():
            version_dirs = [path for path in versions_root.iterdir() if path.is_dir() and path.name.startswith("v")]
            version_dirs.sort(key=self._node_version_sort_key, reverse=True)
            preferred = [path for path in version_dirs if path.name.startswith("v20.")]
            fallback = [path for path in version_dirs if path not in preferred]
            for path in preferred + fallback:
                candidates.append(path / "bin")

        seen = set()
        for bin_dir in candidates:
            bin_dir = Path(bin_dir).expanduser()
            if not bin_dir.exists():
                continue
            node_path = bin_dir / "node"
            npm_path = bin_dir / "npm"
            key = str(bin_dir.resolve())
            if key in seen or not node_path.exists() or not npm_path.exists():
                continue
            seen.add(key)
            env = os.environ.copy()
            env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
            version = self._safe_capture([str(node_path), "-v"], env=env)
            npm_version = self._safe_capture([str(npm_path), "-v"], env=env)
            if version:
                return {
                    "source": "nvm",
                    "bin_dir": str(bin_dir),
                    "node": str(node_path),
                    "npm": str(npm_path),
                    "node_version": version,
                    "npm_version": npm_version,
                }

        return {
            "source": "missing",
            "bin_dir": "",
            "node": "",
            "npm": "",
            "node_version": "",
            "npm_version": "",
        }

    def _node_version_sort_key(self, path):
        name = str(getattr(path, "name", path)).lstrip("v")
        parts = []
        for chunk in name.split("."):
            try:
                parts.append(int(chunk))
            except ValueError:
                parts.append(-1)
        return tuple(parts)

    def _safe_capture(self, cmd, env=None):
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        except Exception:
            return ""
        if result.returncode != 0:
            return ""
        return str(result.stdout or "").strip()

    def _command_env(self):
        env = os.environ.copy()
        bin_dir = str((self._node_runtime or {}).get("bin_dir") or "").strip()
        if bin_dir:
            env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
        tmp_root = Path(tempfile.gettempdir()) / "git-pusher-runtime"
        tmp_root.mkdir(parents=True, exist_ok=True)
        env.setdefault("TMPDIR", str(tmp_root))
        env.setdefault("TEMP", str(tmp_root))
        env.setdefault("TMP", str(tmp_root))
        env.setdefault("XDG_CACHE_HOME", str(tmp_root / "xdg-cache"))
        return env

    def node_runtime_summary(self):
        runtime = self._node_runtime or {}
        source = runtime.get("source") or "missing"
        version = runtime.get("node_version") or "unavailable"
        npm_version = runtime.get("npm_version") or "unavailable"
        if source == "missing":
            return "missing"
        return f"{version} / npm {npm_version} ({source})"

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

    def inspect_repair_history(self, incident):
        deployment_dir = Path(incident.get("deployment_dir") or "").expanduser()
        repair_dir = deployment_dir / "repair-loop"
        if not repair_dir.exists():
            return {
                "ok": False,
                "repair_dir": str(repair_dir),
                "attempts": [],
                "latest_attempt": None,
            }

        attempts = []
        for context_path in sorted(repair_dir.glob("attempt-*-context.json")):
            context = self._read_json(context_path)
            if not isinstance(context, dict):
                continue
            stem = context_path.stem.replace("-context", "")
            attempt = self._extract_attempt_number(stem, fallback=len(attempts) + 1)
            brief_file = repair_dir / f"{stem}-brief.md"
            output_file = repair_dir / f"{stem}-failed-output.log"
            command_log_file = repair_dir / f"{stem}-repair-command.log"
            prompt_file = repair_dir / f"{stem}-ai-prompt.md"
            if not prompt_file.exists():
                prompt_file = repair_dir / f"{stem}-codex-prompt.md"
            last_message_file = repair_dir / f"{stem}-ai-last-message.md"
            if not last_message_file.exists():
                last_message_file = repair_dir / f"{stem}-codex-last-message.md"
            failed_step = ((context.get("failedStep") or {}).get("step")) or {}
            diagnosis = context.get("diagnosis") or {}
            ai_runtime = context.get("aiRuntime") or {}
            ai_summary = self._read_text_excerpt(last_message_file, max_lines=20, max_chars=2200, tail=False)
            attempts.append(
                {
                    "attempt": attempt,
                    "context_file": str(context_path),
                    "brief_file": str(brief_file) if brief_file.exists() else "",
                    "output_file": str(output_file) if output_file.exists() else "",
                    "command_log_file": str(command_log_file) if command_log_file.exists() else "",
                    "prompt_file": str(prompt_file) if prompt_file.exists() else "",
                    "last_message_file": str(last_message_file) if last_message_file.exists() else "",
                    "failed_step_name": str(failed_step.get("name") or "").strip(),
                    "failed_step_command": str(failed_step.get("command") or "").strip(),
                    "diagnosis_category": str(diagnosis.get("category") or "").strip(),
                    "diagnosis_hint": str(diagnosis.get("hint") or "").strip(),
                    "ai_runtime_key": str(ai_runtime.get("key") or "").strip(),
                    "ai_runtime_label": str(ai_runtime.get("label") or "").strip(),
                    "snapshot_branch": str(((context.get("snapshot") or {}).get("branch")) or "").strip(),
                    "snapshot_tag": str(((context.get("snapshot") or {}).get("tag")) or "").strip(),
                    "ai_summary": ai_summary,
                }
            )

        attempts.sort(key=lambda item: item.get("attempt") or 0)
        latest_attempt = attempts[-1] if attempts else None
        return {
            "ok": bool(attempts),
            "repair_dir": str(repair_dir),
            "attempts": attempts,
            "latest_attempt": latest_attempt,
        }

    def new_automation_run_id(self, source="auto"):
        prefix = str(source or "flow").strip().lower() or "flow"
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        return f"{prefix}-{stamp}"

    def inspect_automation_history(self, incident):
        deployment_dir_raw = str((incident or {}).get("deployment_dir") or "").strip()
        if not deployment_dir_raw:
            return {
                "ok": False,
                "history_file": "",
                "entries": [],
                "entry_count": 0,
                "latest_entry": None,
                "latest_run_id": "",
                "latest_run_entries": [],
                "badge_status": "pending",
                "badge_text": "No automation activity",
            }
        deployment_dir = Path(deployment_dir_raw).expanduser()
        history_file = deployment_dir / "automation-history.jsonl"
        entries = []
        if history_file.exists():
            try:
                for raw_line in history_file.read_text(encoding="utf-8").splitlines():
                    raw_line = str(raw_line or "").strip()
                    if not raw_line:
                        continue
                    payload = json.loads(raw_line)
                    if isinstance(payload, dict):
                        entries.append(payload)
            except Exception:
                entries = []

        latest_entry = entries[-1] if entries else None
        latest_run_id = str((latest_entry or {}).get("run_id") or "").strip()
        latest_run_entries = [
            item for item in entries
            if str(item.get("run_id") or "").strip() == latest_run_id
        ] if latest_run_id else []

        status = str((latest_entry or {}).get("status") or "pending").strip().lower() or "pending"
        badge_map = {
            "ok": ("ok", "Flow healthy"),
            "warning": ("warning", "Flow warning"),
            "error": ("error", "Flow failed"),
            "pending": ("pending", "Flow running"),
            "info": ("info", "Flow info"),
        }
        badge_status, badge_text = badge_map.get(status, ("pending", "Flow running"))
        if latest_entry:
            badge_text = str(latest_entry.get("message") or badge_text).strip() or badge_text

        return {
            "ok": bool(entries),
            "history_file": str(history_file),
            "entries": entries[-40:],
            "entry_count": len(entries),
            "latest_entry": latest_entry,
            "latest_run_id": latest_run_id,
            "latest_run_entries": latest_run_entries[-20:],
            "badge_status": badge_status,
            "badge_text": badge_text,
        }

    def append_automation_history(
        self,
        incident,
        *,
        source="auto",
        run_id="",
        event="",
        status="info",
        message="",
        approval_mode="",
        approval_mode_label="",
        metadata=None,
    ):
        deployment_dir_raw = str((incident or {}).get("deployment_dir") or "").strip()
        if not deployment_dir_raw:
            return {"ok": False, "reason": "deployment dir unavailable"}
        deployment_dir = Path(deployment_dir_raw).expanduser()
        deployment_dir.mkdir(parents=True, exist_ok=True)
        history_file = deployment_dir / "automation-history.jsonl"
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "project_id": str((incident or {}).get("project_id") or "").strip(),
            "deployment_id": str((incident or {}).get("deployment_id") or "").strip(),
            "source": str(source or "auto").strip() or "auto",
            "run_id": str(run_id or "").strip(),
            "event": str(event or "").strip(),
            "status": str(status or "info").strip().lower() or "info",
            "message": str(message or "").strip(),
            "approval_mode": str(approval_mode or "").strip(),
            "approval_mode_label": str(approval_mode_label or "").strip(),
            "metadata": metadata or {},
        }
        self._append_text(history_file, json.dumps(payload, sort_keys=True) + "\n")
        return {
            "ok": True,
            "history_file": str(history_file),
            "entry": payload,
        }

    def inspect_approval_queue(self, incident):
        deployment_dir_raw = str((incident or {}).get("deployment_dir") or "").strip()
        if not deployment_dir_raw:
            return {
                "ok": False,
                "queue_file": "",
                "items": [],
                "pending_items": [],
                "latest_pending": None,
                "counts": {"pending": 0, "approved": 0, "rejected": 0, "total": 0},
            }
        deployment_dir = Path(deployment_dir_raw).expanduser()
        queue_file = deployment_dir / "approval-queue.json"
        payload = self._read_json(queue_file)
        items = []
        if isinstance(payload, dict):
            items = payload.get("items") or []
        items = [item for item in items if isinstance(item, dict)]
        items.sort(key=lambda item: str(item.get("created_at") or ""))
        pending = [item for item in items if str(item.get("status") or "").strip() == "pending"]
        latest_pending = pending[-1] if pending else None
        return {
            "ok": bool(items),
            "queue_file": str(queue_file),
            "items": items[-30:],
            "pending_items": pending,
            "latest_pending": latest_pending,
            "counts": {
                "pending": len(pending),
                "approved": len([item for item in items if item.get("status") == "approved"]),
                "rejected": len([item for item in items if item.get("status") == "rejected"]),
                "total": len(items),
            },
        }

    def enqueue_approval_request(
        self,
        incident,
        *,
        action,
        message,
        run_id="",
        source="auto",
        metadata=None,
    ):
        action = str(action or "").strip().lower()
        if action not in APPROVAL_QUEUE_ACTIONS:
            return {"ok": False, "reason": "unsupported approval action"}
        if not str((incident or {}).get("deployment_dir") or "").strip():
            return {"ok": False, "reason": "deployment dir unavailable"}
        queue = self.inspect_approval_queue(incident)
        queue_file = Path(queue["queue_file"])
        items = list(queue.get("items") or [])
        for item in reversed(items):
            if (
                str(item.get("status") or "") == "pending"
                and str(item.get("action") or "") == action
                and str(item.get("run_id") or "") == str(run_id or "").strip()
            ):
                item["message"] = str(message or "").strip()
                item["metadata"] = metadata or item.get("metadata") or {}
                queue_file.write_text(json.dumps({"items": items}, indent=2), encoding="utf-8")
                return {"ok": True, "item": item, "queue_file": str(queue_file), "deduped": True}

        approval_id = f"{action}-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
        item = {
            "id": approval_id,
            "action": action,
            "status": "pending",
            "message": str(message or "").strip(),
            "run_id": str(run_id or "").strip(),
            "source": str(source or "auto").strip() or "auto",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {},
        }
        items.append(item)
        queue_file.parent.mkdir(parents=True, exist_ok=True)
        queue_file.write_text(json.dumps({"items": items}, indent=2), encoding="utf-8")
        return {"ok": True, "item": item, "queue_file": str(queue_file), "deduped": False}

    def resolve_approval_request(
        self,
        incident,
        *,
        action="",
        approval_id="",
        decision="approved",
        note="",
        metadata=None,
    ):
        if not str((incident or {}).get("deployment_dir") or "").strip():
            return {"ok": False, "reason": "deployment dir unavailable"}
        queue = self.inspect_approval_queue(incident)
        queue_file = Path(queue["queue_file"])
        items = list(queue.get("items") or [])
        decision = str(decision or "approved").strip().lower()
        if decision not in {"approved", "rejected"}:
            decision = "approved"

        selected = None
        for item in reversed(items):
            if str(item.get("status") or "") != "pending":
                continue
            if approval_id and str(item.get("id") or "") == str(approval_id):
                selected = item
                break
            if action and str(item.get("action") or "") == str(action):
                selected = item
                break
            if not approval_id and not action:
                selected = item
                break

        if not selected:
            return {"ok": False, "reason": "no pending approval request found"}

        selected["status"] = decision
        selected["resolved_at"] = datetime.now(timezone.utc).isoformat()
        selected["resolution_note"] = str(note or "").strip()
        selected["resolution_metadata"] = metadata or {}
        queue_file.parent.mkdir(parents=True, exist_ok=True)
        queue_file.write_text(json.dumps({"items": items}, indent=2), encoding="utf-8")
        return {"ok": True, "item": selected, "queue_file": str(queue_file)}

    def _read_json(self, path):
        try:
            return json.loads(Path(path).read_text(encoding="utf-8"))
        except Exception:
            return None

    def _read_text_excerpt(self, path, max_lines=20, max_chars=2200, tail=True):
        try:
            text = Path(path).read_text(encoding="utf-8")
        except Exception:
            return ""
        text = str(text or "").strip()
        if not text:
            return ""
        lines = text.splitlines()
        if len(lines) > max_lines:
            lines = lines[-max_lines:] if tail else lines[:max_lines]
        text = "\n".join(lines).strip()
        if len(text) > max_chars:
            text = text[-max_chars:] if tail else text[:max_chars]
        return text.strip()

    def _extract_attempt_number(self, stem, fallback=0):
        try:
            return int(str(stem).split("-")[1])
        except Exception:
            return int(fallback or 0)

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
            "node_runtime": self.node_runtime_summary(),
            "ai_runtimes": self.ai_runtime_summary_inline(),
            "architecture": architecture,
            "languages": languages,
            "frameworks": frameworks,
            "workspace_count": len(workspace_manifests),
            "dockerfiles": dockerfiles,
            "github_workflows": github_workflows,
            "root_scripts": sorted((root_manifest or {}).get("scripts", {}).keys()),
            "plan": plan,
        }

    def inspect_repo_state(self, repo_path):
        root = Path(repo_path).expanduser()
        if not root.exists():
            return {"ok": False, "error": "Repository path does not exist."}
        if not self._git.is_git_repo(str(root)):
            return {"ok": False, "error": "Repository path is not a git repository."}

        branch = self._git.get_current_branch(str(root)) or "unknown"
        remote_url = self._git.get_remote_url(str(root), "origin")
        remotes = self._git.get_remotes(str(root))
        last_commit = self._git.get_last_commit(str(root)) or {}
        status_text = self._git.get_status(str(root))
        status_lines = [line for line in status_text.splitlines() if line.strip()]
        changed_files = self._git.get_changed_files(str(root))
        untracked = [
            line[3:].strip()
            for line in status_lines
            if line.startswith("?? ")
        ]
        tracked_changes = [line for line in status_lines if not line.startswith("?? ")]
        diff_stat = self._git_capture(
            root,
            ["git", "diff", "--stat", "--compact-summary"],
        )
        diff_files = [
            line.strip()
            for line in self._git_capture(root, ["git", "diff", "--name-only"]).splitlines()
            if line.strip()
        ]
        upstream = self._git_capture(
            root,
            ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"],
        )
        ahead = 0
        behind = 0
        if upstream:
            ahead_behind = self._git_capture(
                root,
                ["git", "rev-list", "--left-right", "--count", f"HEAD...{upstream}"],
            )
            try:
                ahead_value, behind_value = [int(chunk) for chunk in ahead_behind.split()]
                ahead = ahead_value
                behind = behind_value
            except Exception:
                ahead = 0
                behind = 0
        return {
            "ok": True,
            "repo_path": str(root),
            "branch": branch,
            "remote_url": remote_url,
            "remotes": remotes,
            "last_commit": last_commit,
            "status_lines": status_lines,
            "changed_files": changed_files,
            "untracked_files": untracked,
            "tracked_change_count": len(tracked_changes),
            "untracked_count": len(untracked),
            "diff_stat": diff_stat,
            "diff_files": diff_files,
            "upstream": upstream,
            "ahead": ahead,
            "behind": behind,
            "dirty": bool(status_lines),
        }

    def build_commit_message(self, incident, repair_history):
        latest = ((repair_history or {}).get("latest_attempt")) or {}
        diagnosis = str(latest.get("diagnosis_category") or "").strip()
        failed_step = str(latest.get("failed_step_name") or "").strip()
        summary = self.strip_log_tags(str((incident or {}).get("summary") or "").strip())
        summary = " ".join(summary.split())
        if diagnosis and failed_step:
            return f"Fix NovaDeploy {diagnosis} failure in {failed_step}"
        if diagnosis:
            return f"Fix NovaDeploy {diagnosis} failure"
        if summary:
            clipped = summary[:56].rstrip()
            if len(summary) > 56:
                clipped += "..."
            return f"Fix NovaDeploy failure: {clipped}"
        return "Fix NovaDeploy deployment failure"

    def build_safety_gate(self, plan, results=None, run_ok=False, executed=False):
        steps = list(plan or [])
        results = list(results or [])
        required_categories = []
        for step in steps:
            category = str(step.get("category") or "").strip().lower()
            if category in SAFETY_GATE_CATEGORIES and category not in required_categories:
                required_categories.append(category)

        by_category = {}
        for item in results:
            step = item.get("step") or {}
            category = str(step.get("category") or "").strip().lower()
            by_category.setdefault(category, []).append(item)

        checks = []
        for category in required_categories:
            category_results = by_category.get(category, [])
            passed = [item for item in category_results if item.get("ok")]
            failed = [item for item in category_results if not item.get("ok")]
            if passed:
                status = "passed"
            elif failed:
                status = "failed"
            elif executed:
                status = "not-run"
            else:
                status = "pending"
            names = [
                str(((item.get("step") or {}).get("name")) or "").strip()
                for item in (passed or failed or category_results)
                if str(((item.get("step") or {}).get("name")) or "").strip()
            ]
            checks.append(
                {
                    "category": category,
                    "status": status,
                    "steps": names,
                }
            )

        if not steps:
            return {
                "ok": False,
                "executed": False,
                "required_categories": [],
                "checks": [],
                "summary": "Analyze the repository to build the safety gate.",
            }

        if not required_categories:
            return {
                "ok": bool(executed and run_ok),
                "executed": bool(executed),
                "required_categories": [],
                "checks": [],
                "summary": (
                    "No required typecheck/test/build gates detected. Last validation passed."
                    if executed and run_ok
                    else "Run validation to open the safety gate."
                ),
            }

        gate_ok = bool(executed and run_ok and all(item["status"] == "passed" for item in checks))
        if gate_ok:
            summary = "Safety gate open. Required checks passed."
        elif executed:
            summary = "Safety gate blocked. Required checks are not fully green."
        else:
            summary = "Run validation to evaluate required checks."
        return {
            "ok": gate_ok,
            "executed": bool(executed),
            "required_categories": required_categories,
            "checks": checks,
            "summary": summary,
        }

    def format_repo_state(self, repo_state):
        if not repo_state.get("ok"):
            return repo_state.get("error", "Repository state unavailable.")

        lines = [
            f"Repo: {repo_state.get('repo_path')}",
            f"Branch: {repo_state.get('branch')}",
            f"Dirty: {'yes' if repo_state.get('dirty') else 'no'}",
        ]
        remote_url = str(repo_state.get("remote_url") or "").strip()
        if remote_url:
            lines.append(f"Origin: {remote_url}")
        last_commit = repo_state.get("last_commit") or {}
        if last_commit:
            lines.append(
                "HEAD: "
                f"{last_commit.get('hash') or 'unknown'} | "
                f"{last_commit.get('message') or 'No message'}"
            )
        if repo_state.get("upstream"):
            lines.append(
                f"Upstream: {repo_state.get('upstream')} | ahead {repo_state.get('ahead') or 0} / behind {repo_state.get('behind') or 0}"
            )
        remotes = repo_state.get("remotes") or {}
        if remotes:
            remote_names = ", ".join(sorted(remotes.keys()))
            lines.append(f"Remotes: {remote_names}")
        changed_files = repo_state.get("changed_files") or []
        untracked_files = repo_state.get("untracked_files") or []
        status_lines = repo_state.get("status_lines") or []
        lines.append(f"Status entries: {len(status_lines)}")
        diff_stat = str(repo_state.get("diff_stat") or "").strip()
        if diff_stat:
            lines.extend(["", "Diff stat:", diff_stat])
        if changed_files:
            lines.append("")
            lines.append("Changed files:")
            for item in changed_files[:12]:
                lines.append(
                    f"{item.get('file')}  (+{item.get('added') or 0} / -{item.get('removed') or 0})"
                )
        elif untracked_files:
            lines.append("")
            lines.append("Untracked files:")
            for item in untracked_files[:12]:
                lines.append(item)
        return "\n".join(lines)

    def format_safety_gate(self, gate):
        if not gate:
            return "Safety gate not initialized."

        lines = [str(gate.get("summary") or "Safety gate unavailable.")]
        required = gate.get("required_categories") or []
        if required:
            lines.append("")
            lines.append("Required checks:")
            for item in gate.get("checks") or []:
                status = str(item.get("status") or "pending").upper()
                label = str(item.get("category") or "unknown")
                step_names = ", ".join(item.get("steps") or [])
                if step_names:
                    lines.append(f"- {label}: {status} ({step_names})")
                else:
                    lines.append(f"- {label}: {status}")
        elif gate.get("executed"):
            lines.append("")
            lines.append("No required typecheck/test/build gates were detected for this plan.")

        return "\n".join(lines)

    def evaluate_push_guard(
        self,
        repo_state,
        *,
        initial_repo_state=None,
        push_github=False,
        push_gitlab=False,
        policy=None,
    ):
        policy = self.normalize_push_policy(policy)
        target_remotes = []
        if push_github:
            target_remotes.append("origin")
        if push_gitlab:
            target_remotes.append("gitlab")

        issues = []
        warnings = []
        if not repo_state.get("ok"):
            issues.append(repo_state.get("error", "Repository state unavailable."))
        branch = str(repo_state.get("branch") or "").strip()
        remotes = repo_state.get("remotes") or {}
        if target_remotes and branch and branch not in policy["allowed_branches"]:
            issues.append(
                f"Branch '{branch}' is not in the allowed push list: {', '.join(policy['allowed_branches'])}."
            )
        for remote_name in target_remotes:
            if remote_name not in remotes:
                issues.append(f"Remote '{remote_name}' is not configured in this repository.")
            elif remote_name not in policy["allowed_remotes"]:
                issues.append(
                    f"Remote '{remote_name}' is not in the allowed push list: {', '.join(policy['allowed_remotes'])}."
                )

        if policy["source"] == "auto" and target_remotes and not policy["allow_auto_push"]:
            issues.append("Auto-push is disabled for this repository.")

        initial_repo_state = initial_repo_state or {}
        if policy["require_clean_start"] and initial_repo_state.get("dirty"):
            issues.append("The repository was already dirty before the automated flow started.")

        if target_remotes and repo_state.get("dirty"):
            warnings.append("Repository still has local changes; push should happen from a clean committed state.")
        if target_remotes and repo_state.get("behind"):
            warnings.append("Repository is behind its upstream branch; pushing may need a sync first.")

        ok = not issues
        if ok:
            summary = "Push guard open."
        else:
            summary = "Push guard blocked."

        return {
            "ok": ok,
            "summary": summary,
            "issues": issues,
            "warnings": warnings,
            "policy": policy,
            "target_remotes": target_remotes,
            "branch": branch,
        }

    def format_push_guard(self, guard):
        if not guard:
            return "Push guard not evaluated yet."
        lines = [guard.get("summary") or "Push guard unavailable."]
        policy = guard.get("policy") or {}
        lines.append(
            "Allowed branches: " + ", ".join(policy.get("allowed_branches") or ["none"])
        )
        lines.append(
            "Allowed remotes: " + ", ".join(policy.get("allowed_remotes") or ["none"])
        )
        lines.append(f"Auto-push allowed: {'yes' if policy.get('allow_auto_push') else 'no'}")
        if guard.get("target_remotes"):
            lines.append("Target remotes: " + ", ".join(guard["target_remotes"]))
        if guard.get("issues"):
            lines.append("")
            lines.append("Blocking issues:")
            for item in guard["issues"]:
                lines.append(f"- {item}")
        if guard.get("warnings"):
            lines.append("")
            lines.append("Warnings:")
            for item in guard["warnings"]:
                lines.append(f"- {item}")
        return "\n".join(lines)

    def build_debug_context(self, incident, repair_history, repo_state):
        latest_attempt = ((repair_history or {}).get("latest_attempt")) or {}
        diff_stat = str((repo_state or {}).get("diff_stat") or "").strip()
        diff_files = (repo_state or {}).get("diff_files") or []
        ai_summary = str(latest_attempt.get("ai_summary") or "").strip()
        context = {
            "project": str((incident or {}).get("project_name") or (incident or {}).get("project_id") or "").strip(),
            "deployment_id": str((incident or {}).get("deployment_id") or "").strip(),
            "summary": self.strip_log_tags(str((incident or {}).get("summary") or "").strip()),
            "ai_runtime": str(latest_attempt.get("ai_runtime_label") or latest_attempt.get("ai_runtime_key") or "").strip(),
            "failed_step_name": str(latest_attempt.get("failed_step_name") or "").strip(),
            "failed_step_command": str(latest_attempt.get("failed_step_command") or "").strip(),
            "diagnosis_category": str(latest_attempt.get("diagnosis_category") or "").strip(),
            "diagnosis_hint": str(latest_attempt.get("diagnosis_hint") or "").strip(),
            "ai_summary": ai_summary,
            "diff_stat": diff_stat,
            "diff_files": diff_files[:12],
        }
        return context

    def format_debug_context(self, context):
        if not context:
            return "No debug context available yet."
        lines = [
            f"Project: {context.get('project') or 'unknown'}",
            f"Deployment: {context.get('deployment_id') or 'unknown'}",
            f"Summary: {context.get('summary') or 'No summary'}",
            f"AI runtime: {context.get('ai_runtime') or 'unknown'}",
            f"Failed step: {context.get('failed_step_name') or 'unknown'}",
        ]
        if context.get("failed_step_command"):
            lines.append(f"Command: {context['failed_step_command']}")
        if context.get("diagnosis_category") or context.get("diagnosis_hint"):
            lines.append(
                "Diagnosis: "
                f"{context.get('diagnosis_category') or 'unknown'}"
                + (f" | {context.get('diagnosis_hint')}" if context.get("diagnosis_hint") else "")
            )
        if context.get("ai_summary"):
            lines.extend(["", "AI summary:", context["ai_summary"]])
        if context.get("diff_stat"):
            lines.extend(["", "Diff stat:", context["diff_stat"]])
        elif context.get("diff_files"):
            lines.extend(["", "Changed files:"])
            for item in context["diff_files"]:
                lines.append(item)
        return "\n".join(lines)

    def build_incident_metrics(self, incident, automation_history=None, repair_history=None, approval_queue=None):
        automation_history = automation_history or {}
        repair_history = repair_history or {}
        approval_queue = approval_queue or {}
        entries = automation_history.get("entries") or []
        attempts = repair_history.get("attempts") or []
        pending_approvals = approval_queue.get("pending_items") or []
        run_ids = {
            str(item.get("run_id") or "").strip()
            for item in entries
            if str(item.get("run_id") or "").strip()
        }
        commit_events = [
            item for item in entries
            if str(item.get("event") or "").strip() in {"flow_committed", "flow_commit_local_only"}
        ]
        push_events = [
            item for item in entries
            if str(item.get("event") or "").strip() == "flow_pushed"
        ]
        handoff_events = [
            item for item in entries
            if str(item.get("event") or "").strip() == "flow_handoff_ready"
        ]
        durations = ""
        if len(entries) >= 2:
            try:
                started = datetime.fromisoformat(str(entries[0]["timestamp"]).replace("Z", "+00:00"))
                ended = datetime.fromisoformat(str(entries[-1]["timestamp"]).replace("Z", "+00:00"))
                seconds = max(0, int((ended - started).total_seconds()))
                minutes, seconds = divmod(seconds, 60)
                hours, minutes = divmod(minutes, 60)
                durations = f"{hours}h {minutes}m {seconds}s" if hours else f"{minutes}m {seconds}s"
            except Exception:
                durations = ""
        return {
            "project": str((incident or {}).get("project_name") or (incident or {}).get("project_id") or "").strip(),
            "deployment_id": str((incident or {}).get("deployment_id") or "").strip(),
            "automation_entries": len(entries),
            "runs": len(run_ids),
            "repair_attempts": len(attempts),
            "commits": len(commit_events),
            "pushes": len(push_events),
            "handoffs": len(handoff_events),
            "pending_approvals": len(pending_approvals),
            "approved_approvals": int(((approval_queue.get("counts") or {}).get("approved")) or 0),
            "rejected_approvals": int(((approval_queue.get("counts") or {}).get("rejected")) or 0),
            "duration": durations,
        }

    def format_incident_metrics(self, metrics):
        if not metrics:
            return "No incident metrics yet."
        lines = [
            f"Project: {metrics.get('project') or 'unknown'}",
            f"Deployment: {metrics.get('deployment_id') or 'unknown'}",
            f"Automation entries: {metrics.get('automation_entries') or 0}",
            f"Runs detected: {metrics.get('runs') or 0}",
            f"Repair attempts: {metrics.get('repair_attempts') or 0}",
            f"Commits: {metrics.get('commits') or 0}",
            f"Pushes: {metrics.get('pushes') or 0}",
            f"Handoffs: {metrics.get('handoffs') or 0}",
            f"Pending approvals: {metrics.get('pending_approvals') or 0}",
            f"Approved approvals: {metrics.get('approved_approvals') or 0}",
            f"Rejected approvals: {metrics.get('rejected_approvals') or 0}",
        ]
        if metrics.get("duration"):
            lines.append(f"Observed duration: {metrics['duration']}")
        return "\n".join(lines)

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
                root,
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
                root,
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

    def _steps_from_manifest(self, repo_root, package_manager, relative_path, manifest, prefer_root=False):
        scripts = manifest.get("scripts") or {}
        steps = []
        for category, variants in SCRIPT_CATEGORIES.items():
            script_name = self._find_script_name(scripts, variants)
            if not script_name:
                continue
            script_body = str(scripts.get(script_name) or "").strip()
            if self._should_skip_root_turbo_wrapper(repo_root, relative_path, package_manager, script_body):
                continue
            scope_name = "repo" if relative_path == "." else relative_path
            command = self._build_script_command(
                repo_root,
                package_manager,
                relative_path,
                script_name,
                script_body=script_body,
            )
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

    def _build_script_command(self, repo_root, package_manager, relative_path, script_name, script_body=""):
        target = "." if relative_path in ("", ".") else relative_path
        quoted_target = shlex.quote(target)
        quoted_script = shlex.quote(script_name)
        turbo_command = self._build_turbo_root_command(repo_root, target, package_manager, script_body)
        if turbo_command:
            return turbo_command
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

    def _build_turbo_root_command(self, repo_root, target, package_manager, script_body):
        if target != "." or package_manager != "pnpm":
            return ""
        body = str(script_body or "").strip()
        if not body.startswith("turbo run "):
            return ""

        try:
            tokens = shlex.split(body)
        except ValueError:
            return ""
        if len(tokens) < 3 or tokens[0] != "turbo" or tokens[1] != "run":
            return ""

        cache_dir = self._turbo_cache_dir(repo_root)
        extra_args = tokens[2:]
        command_parts = ["pnpm", "exec", "turbo", "run"]
        command_parts.extend(extra_args)
        command_parts.extend(
            [
                "--cache-dir",
                str(cache_dir),
                "--summarize=false",
                "--log-order=stream",
                "--output-logs=full",
            ]
        )
        return " ".join(shlex.quote(part) for part in command_parts)

    def _should_skip_root_turbo_wrapper(self, repo_root, relative_path, package_manager, script_body):
        if relative_path != "." or package_manager != "pnpm":
            return False
        body = str(script_body or "").strip()
        if not body.startswith("turbo run "):
            return False
        turbo_json = Path(repo_root).expanduser() / "turbo.json"
        return turbo_json.exists()

    def _turbo_cache_dir(self, repo_root):
        root = Path(repo_root).expanduser().resolve()
        digest = hashlib.sha1(str(root).encode("utf-8")).hexdigest()[:12]
        cache_dir = Path(tempfile.gettempdir()) / "git-pusher-turbo-cache" / f"{root.name}-{digest}"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

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
        ai_runtime="",
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
        repo_state_before = self.inspect_repo_state(root)

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
                repo_state_before=repo_state_before,
                attempt=attempt,
                results=result.get("results") or [],
                failed_step=failed_step,
                repo_path=str(root),
                ai_runtime=ai_runtime,
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
                ai_runtime=ai_runtime,
            )
            on_event(
                {
                    "type": "repair_command_started",
                    "message": f"Running {self.get_ai_runtime(ai_runtime).get('label')} repair command for attempt {attempt}: {repair_command}",
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

    def resolve_rollback_snapshot(self, repo_path, repair_history):
        root = Path(repo_path).expanduser()
        latest = ((repair_history or {}).get("latest_attempt")) or {}
        for ref_type in ("snapshot_tag", "snapshot_branch"):
            ref_name = str(latest.get(ref_type) or "").strip()
            if not ref_name:
                continue
            resolved = self._git_ref(root, ["git", "rev-parse", ref_name])
            if resolved:
                return {
                    "ok": True,
                    "ref": ref_name,
                    "ref_type": ref_type,
                    "head": resolved,
                }
        return {
            "ok": False,
            "reason": "No rollback snapshot available for this repair attempt.",
        }

    def rollback_to_snapshot(
        self,
        repo_path,
        repair_history,
        on_event,
        push_github=False,
        push_gitlab=False,
        github_token="",
        gitlab_token="",
    ):
        root = Path(repo_path).expanduser()
        target = self.resolve_rollback_snapshot(root, repair_history)
        if not target.get("ok"):
            on_event({"type": "rollback_error", "message": target.get("reason", "Rollback snapshot unavailable.")})
            return {"ok": False, "target": target}

        rescue_snapshot = self.create_safety_snapshot(root, label="pre-rollback")
        if rescue_snapshot.get("ok"):
            on_event(
                {
                    "type": "rollback_rescue_snapshot",
                    "message": f"Pre-rollback snapshot created: {rescue_snapshot['branch']} | {rescue_snapshot['tag']}",
                    "snapshot": rescue_snapshot,
                }
            )
        else:
            on_event(
                {
                    "type": "rollback_rescue_snapshot_skipped",
                    "message": f"Pre-rollback snapshot skipped: {rescue_snapshot.get('reason')}",
                    "snapshot": rescue_snapshot,
                }
            )

        on_event({"type": "rollback_reset", "message": f"Resetting repository to snapshot {target['ref']}..."})
        reset_result = subprocess.run(
            ["git", "reset", "--hard", target["ref"]],
            cwd=str(root),
            capture_output=True,
            text=True,
        )
        reset_output = (reset_result.stdout or "") + (reset_result.stderr or "")
        if reset_output.strip():
            on_event({"type": "rollback_reset_output", "message": reset_output.strip()})
        if reset_result.returncode != 0:
            on_event({"type": "rollback_error", "message": "Rollback reset failed."})
            return {
                "ok": False,
                "target": target,
                "rescue_snapshot": rescue_snapshot,
            }

        clean_result = subprocess.run(
            ["git", "clean", "-fd"],
            cwd=str(root),
            capture_output=True,
            text=True,
        )
        clean_output = (clean_result.stdout or "") + (clean_result.stderr or "")
        if clean_output.strip():
            on_event({"type": "rollback_clean_output", "message": clean_output.strip()})

        branch = self._git.get_current_branch(str(root)) or "main"
        push_results = []
        any_push_ok = False

        if push_github:
            env = os.environ.copy()
            if github_token:
                env.update({"GIT_ASKPASS": "echo", "GIT_USERNAME": "x-token", "GIT_PASSWORD": github_token})
            push_result = subprocess.run(
                ["git", "push", "--force-with-lease", "origin", branch],
                cwd=str(root),
                capture_output=True,
                text=True,
                env=env,
            )
            push_output = (push_result.stdout or "") + (push_result.stderr or "")
            if push_output.strip():
                on_event({"type": "rollback_push_output", "message": f"GitHub: {push_output.strip()}"})
            ok_push = push_result.returncode == 0
            push_results.append({"target": "github", "ok": ok_push})
            any_push_ok = any_push_ok or ok_push

        if push_gitlab:
            env = os.environ.copy()
            if gitlab_token:
                env.update({"GIT_ASKPASS": "echo", "GIT_USERNAME": "oauth2", "GIT_PASSWORD": gitlab_token})
            push_result = subprocess.run(
                ["git", "push", "--force-with-lease", "gitlab", branch],
                cwd=str(root),
                capture_output=True,
                text=True,
                env=env,
            )
            push_output = (push_result.stdout or "") + (push_result.stderr or "")
            if push_output.strip():
                on_event({"type": "rollback_push_output", "message": f"GitLab: {push_output.strip()}"})
            ok_push = push_result.returncode == 0
            push_results.append({"target": "gitlab", "ok": ok_push})
            any_push_ok = any_push_ok or ok_push

        if push_results:
            if all(item["ok"] for item in push_results):
                on_event({"type": "rollback_push_done", "message": "Rollback push completed successfully."})
            elif any_push_ok:
                on_event({"type": "rollback_push_partial", "message": "Rollback push completed only partially."})
            else:
                on_event({"type": "rollback_push_failed", "message": "Rollback push failed."})

        repo_state = self.inspect_repo_state(root)
        return {
            "ok": True if not push_results else any(item["ok"] for item in push_results),
            "target": target,
            "rescue_snapshot": rescue_snapshot,
            "repo_state": repo_state,
            "push_results": push_results,
        }

    def safe_commit_changes(
        self,
        repo_path,
        commit_message,
        on_event,
    ):
        root = Path(repo_path).expanduser()
        repo_state = self.inspect_repo_state(root)
        if not repo_state.get("ok"):
            on_event({"type": "safe_commit_error", "message": repo_state.get("error", "Repository state unavailable.")})
            return {"ok": False, "repo_state": repo_state}
        if not repo_state.get("dirty"):
            on_event({"type": "safe_commit_skipped", "message": "No local changes detected. Nothing to commit."})
            return {"ok": False, "repo_state": repo_state, "reason": "clean"}

        snapshot = self.create_safety_snapshot(root, label="safe-commit")
        if snapshot.get("ok"):
            on_event(
                {
                    "type": "safe_commit_snapshot",
                    "message": f"Pre-commit snapshot created: {snapshot['branch']} | {snapshot['tag']}",
                    "snapshot": snapshot,
                }
            )
        else:
            on_event(
                {
                    "type": "safe_commit_snapshot_skipped",
                    "message": f"Pre-commit snapshot skipped: {snapshot.get('reason')}",
                    "snapshot": snapshot,
                }
            )

        on_event({"type": "safe_commit_stage", "message": "Staging repository changes..."})
        ok_add, out_add = self._git.add_all(str(root))
        if out_add.strip():
            on_event({"type": "safe_commit_stage_output", "message": out_add.strip()})
        if not ok_add:
            on_event({"type": "safe_commit_error", "message": "Failed to stage repository changes."})
            return {"ok": False, "snapshot": snapshot, "repo_state": repo_state}

        message = str(commit_message or "").strip() or "Fix NovaDeploy deployment failure"
        on_event({"type": "safe_commit_commit", "message": f"Creating commit: {message}"})
        ok_commit, out_commit = self._git.commit(str(root), message)
        if out_commit.strip():
            on_event({"type": "safe_commit_commit_output", "message": out_commit.strip()})
        if not ok_commit:
            on_event({"type": "safe_commit_error", "message": "Commit failed."})
            return {"ok": False, "snapshot": snapshot, "repo_state": repo_state}

        branch = self._git.get_current_branch(str(root)) or "main"
        final_repo_state = self.inspect_repo_state(root)
        return {
            "ok": True,
            "snapshot": snapshot,
            "repo_state": final_repo_state,
            "commit_message": message,
            "branch": branch,
        }

    def push_current_branch(
        self,
        repo_path,
        on_event,
        *,
        push_github=False,
        push_gitlab=False,
        github_token="",
        gitlab_token="",
        push_policy=None,
        initial_repo_state=None,
    ):
        root = Path(repo_path).expanduser()
        repo_state = self.inspect_repo_state(root)
        guard = self.evaluate_push_guard(
            repo_state,
            initial_repo_state=initial_repo_state,
            push_github=push_github,
            push_gitlab=push_gitlab,
            policy=push_policy,
        )
        if not guard.get("ok"):
            on_event({"type": "safe_push_guard_blocked", "message": guard.get("summary", "Push guard blocked.")})
            for item in guard.get("issues") or []:
                on_event({"type": "safe_push_guard_issue", "message": item})
            return {
                "ok": False,
                "reason": "push_guard_blocked",
                "guard": guard,
                "repo_state": repo_state,
                "push_results": [],
            }

        branch = self._git.get_current_branch(str(root)) or "main"
        push_results = []
        any_push_ok = False
        if push_github:
            env = {"GIT_ASKPASS": "echo", "GIT_USERNAME": "x-token", "GIT_PASSWORD": github_token} if github_token else None
            ok_push, out_push = self._git.push(str(root), "origin", branch, env=env)
            if out_push.strip():
                on_event({"type": "safe_push_output", "message": f"GitHub: {out_push.strip()}"})
            push_results.append({"target": "github", "ok": ok_push})
            any_push_ok = any_push_ok or ok_push

        if push_gitlab:
            env = {"GIT_ASKPASS": "echo", "GIT_USERNAME": "oauth2", "GIT_PASSWORD": gitlab_token} if gitlab_token else None
            ok_push, out_push = self._git.push(str(root), "gitlab", branch, env=env)
            if out_push.strip():
                on_event({"type": "safe_push_output", "message": f"GitLab: {out_push.strip()}"})
            push_results.append({"target": "gitlab", "ok": ok_push})
            any_push_ok = any_push_ok or ok_push

        if push_results:
            if all(item["ok"] for item in push_results):
                on_event({"type": "safe_push_done", "message": "Push completed successfully."})
            elif any_push_ok:
                on_event({"type": "safe_push_partial", "message": "Push completed only partially."})
            else:
                on_event({"type": "safe_push_failed", "message": "Push failed."})

        return {
            "ok": not push_results or any(item["ok"] for item in push_results),
            "guard": guard,
            "repo_state": repo_state,
            "branch": branch,
            "push_results": push_results,
        }

    def safe_commit_and_push(
        self,
        repo_path,
        commit_message,
        on_event,
        push_github=False,
        push_gitlab=False,
        github_token="",
        gitlab_token="",
        push_policy=None,
        initial_repo_state=None,
    ):
        commit_result = self.safe_commit_changes(
            repo_path=repo_path,
            commit_message=commit_message,
            on_event=on_event,
        )
        if not commit_result.get("ok"):
            return commit_result
        if not (push_github or push_gitlab):
            commit_result["push_results"] = []
            return commit_result

        push_result = self.push_current_branch(
            repo_path=repo_path,
            on_event=on_event,
            push_github=push_github,
            push_gitlab=push_gitlab,
            github_token=github_token,
            gitlab_token=gitlab_token,
            push_policy=push_policy,
            initial_repo_state=initial_repo_state or commit_result.get("repo_state"),
        )
        return {
            "ok": bool(commit_result.get("ok") and push_result.get("ok")),
            "snapshot": commit_result.get("snapshot"),
            "repo_state": push_result.get("repo_state") or commit_result.get("repo_state"),
            "commit_message": commit_result.get("commit_message"),
            "branch": commit_result.get("branch"),
            "push_results": push_result.get("push_results") or [],
            "guard": push_result.get("guard"),
            "commit_ok": True,
            "push_ok": bool(push_result.get("ok")),
            "reason": push_result.get("reason") or "",
        }

    def _run_streaming_command(self, repo_path, command, on_output, stop_event=None):
        process = subprocess.Popen(
            ["bash", "-lc", command],
            cwd=str(repo_path),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=self._command_env(),
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
        repo_state_before,
        attempt,
        results,
        failed_step,
        repo_path,
        ai_runtime="",
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
            "aiRuntime": self.get_ai_runtime(ai_runtime),
            "snapshot": snapshot,
            "repoStateBefore": repo_state_before,
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
        ai_runtime="",
    ):
        runtime = self.get_ai_runtime(ai_runtime)
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
            "ai_runtime": shlex.quote(runtime["key"]),
            "ai_runtime_raw": runtime["key"],
            "ai_runtime_label": runtime["label"],
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

    def _git_capture(self, repo_path, command):
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
            f"Node runtime: {analysis.get('node_runtime') or 'missing'}",
            f"Local AI runtimes: {analysis.get('ai_runtimes') or 'unknown'}",
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

    def format_repair_history(self, history):
        attempts = history.get("attempts") or []
        if not attempts:
            return "No repair artifacts yet for this incident."

        latest = history.get("latest_attempt") or attempts[-1]
        lines = [
            f"Repair folder: {history.get('repair_dir')}",
            f"Attempts detected: {len(attempts)}",
            f"Latest attempt: {latest.get('attempt')}",
            f"Latest AI runtime: {latest.get('ai_runtime_label') or latest.get('ai_runtime_key') or 'unknown'}",
            f"Latest diagnosis: {latest.get('diagnosis_category') or 'unknown'}",
            f"Latest failed step: {latest.get('failed_step_name') or 'unknown'}",
        ]
        if latest.get("snapshot_branch") or latest.get("snapshot_tag"):
            lines.append(
                "Snapshot: "
                f"{latest.get('snapshot_branch') or 'n/a'} | "
                f"{latest.get('snapshot_tag') or 'n/a'}"
            )
        if latest.get("ai_summary"):
            lines.extend(
                [
                    "",
                    "Latest AI summary:",
                    latest["ai_summary"],
                ]
            )

        lines.extend(["", "Attempts:"])
        for item in attempts:
            details = (
                f"attempt {item.get('attempt')} | "
                f"{item.get('ai_runtime_label') or item.get('ai_runtime_key') or 'unknown-ai'} | "
                f"{item.get('diagnosis_category') or 'unknown'} | "
                f"{item.get('failed_step_name') or 'unknown'}"
            )
            if item.get("last_message_file"):
                details += " | ai-summary"
            lines.append(details)

        return "\n".join(lines)

    def format_automation_history(self, history):
        entries = history.get("entries") or []
        if not entries:
            return "No automation activity recorded yet for this incident."

        latest = history.get("latest_entry") or entries[-1]
        lines = [
            f"History file: {history.get('history_file')}",
            f"Entries: {history.get('entry_count') or len(entries)}",
            f"Latest status: {str(latest.get('status') or 'pending').upper()}",
            f"Latest source: {latest.get('source') or 'unknown'}",
            f"Latest event: {latest.get('event') or 'unknown'}",
            f"Latest message: {latest.get('message') or 'No message'}",
        ]
        run_entries = history.get("latest_run_entries") or []
        if run_entries:
            lines.extend(["", "Latest run:"])
            for item in run_entries[-8:]:
                timestamp = str(item.get("timestamp") or "").strip()
                stamp = timestamp.replace("T", " ")[:19] if timestamp else "unknown-time"
                status = str(item.get("status") or "info").upper()
                source = str(item.get("source") or "flow").strip()
                event = str(item.get("event") or "event").strip()
                message = str(item.get("message") or "").strip()
                lines.append(f"{stamp} | {source} | {status} | {event}")
                if message:
                    lines.append(f"  {message}")
        else:
            lines.extend(["", "Recent activity:"])
            for item in entries[-8:]:
                timestamp = str(item.get("timestamp") or "").strip()
                stamp = timestamp.replace("T", " ")[:19] if timestamp else "unknown-time"
                status = str(item.get("status") or "info").upper()
                source = str(item.get("source") or "flow").strip()
                event = str(item.get("event") or "event").strip()
                message = str(item.get("message") or "").strip()
                lines.append(f"{stamp} | {source} | {status} | {event}")
                if message:
                    lines.append(f"  {message}")

        return "\n".join(lines)

    def format_approval_queue(self, queue):
        items = queue.get("items") or []
        if not items:
            return "No approval requests recorded for this incident."

        latest_pending = queue.get("latest_pending") or {}
        counts = queue.get("counts") or {}
        lines = [
            f"Queue file: {queue.get('queue_file')}",
            f"Pending: {counts.get('pending') or 0}",
            f"Approved: {counts.get('approved') or 0}",
            f"Rejected: {counts.get('rejected') or 0}",
        ]
        if latest_pending:
            lines.extend(
                [
                    "",
                    "Latest pending request:",
                    f"- Action: {latest_pending.get('action') or 'unknown'}",
                    f"- Message: {latest_pending.get('message') or 'No message'}",
                    f"- Source: {latest_pending.get('source') or 'unknown'}",
                ]
            )

        lines.extend(["", "Recent requests:"])
        for item in items[-8:]:
            lines.append(
                f"{item.get('created_at') or 'unknown'} | {item.get('action') or 'unknown'} | {item.get('status') or 'pending'}"
            )
            if item.get("message"):
                lines.append(f"  {item['message']}")
        return "\n".join(lines)

    def strip_log_tags(self, message):
        cursor = str(message or "")
        while cursor.startswith("["):
            end = cursor.find("]")
            if end <= 1:
                break
            cursor = cursor[end + 1 :].lstrip()
        return cursor or str(message or "")
