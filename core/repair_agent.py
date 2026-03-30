#!/usr/bin/env python3
"""Invoke a local AI CLI as the automatic repair worker for a failed incident."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parent.parent
SYSTEM_GUIDE_PATH = APP_ROOT / "test-debuging-system"
SUPPORTED_RUNTIMES = {"codex", "claude"}


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _trim_text(value: str, max_lines: int = 180, max_chars: int = 18000, tail: bool = True) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    lines = text.splitlines()
    if len(lines) > max_lines:
        text = "\n".join(lines[-max_lines:] if tail else lines[:max_lines])
    if len(text) > max_chars:
        text = text[-max_chars:] if tail else text[:max_chars]
    return text.strip()


def _artifact_stem(context_path: Path) -> str:
    stem = context_path.stem
    if stem.endswith("-context"):
        return stem[: -len("-context")]
    return stem


def _format_plan(plan: list[dict]) -> str:
    if not plan:
        return "- No plan detected."
    lines = []
    for index, step in enumerate(plan[:12], start=1):
        lines.append(
            f"{index}. {step.get('name') or 'Unnamed'} | "
            f"{step.get('category') or 'unknown'} | "
            f"{step.get('command') or 'unknown command'}"
        )
    return "\n".join(lines)


def _format_analysis(analysis: dict) -> str:
    if not analysis:
        return "- No repository analysis available."
    lines = [
        f"- Repo: {analysis.get('repo_name') or 'unknown'}",
        f"- Architecture: {analysis.get('architecture') or 'unknown'}",
        f"- Package manager: {analysis.get('package_manager') or 'unknown'}",
        f"- Frameworks: {', '.join(analysis.get('frameworks') or []) or 'unknown'}",
        f"- Languages: {', '.join(analysis.get('languages') or []) or 'unknown'}",
        f"- Workspaces: {analysis.get('workspace_count') or 0}",
    ]
    workflows = analysis.get("github_workflows") or []
    if workflows:
        lines.append(f"- GitHub workflows: {', '.join(workflows[:5])}")
    dockerfiles = analysis.get("dockerfiles") or []
    if dockerfiles:
        lines.append(f"- Dockerfiles: {', '.join(dockerfiles[:5])}")
    return "\n".join(lines)


def _build_prompt(context: dict, repo_path: Path, runtime_label: str) -> str:
    incident = context.get("incident") or {}
    diagnosis = context.get("diagnosis") or {}
    failed_step = context.get("failedStep") or {}
    failed_step_meta = failed_step.get("step") or {}
    analysis = context.get("analysis") or {}
    failed_output = _trim_text(failed_step.get("output") or "")
    summary = str(incident.get("summary") or "").strip()
    guide_excerpt = _trim_text(_read_text(SYSTEM_GUIDE_PATH), max_lines=80, max_chars=7000, tail=False)

    prompt = f"""
You are the automatic repair worker running inside Git Pusher's Test & Debugging loop.
Current local AI runtime: {runtime_label}

Act like a senior reliability engineer, CI/CD debugger, and careful software repair agent.

Primary objective:
- inspect the repository and the repair context
- fix the smallest set of issues needed to unblock the failed step
- rerun the minimum useful validation locally
- stop when the repo is greener or when the issue clearly needs human input

Hard rules:
- do not commit
- do not push
- do not create or delete branches or tags
- do not revert unrelated local changes
- prefer minimal, targeted edits
- avoid speculative refactors
- if secrets, remote services, or external infra block progress, explain that clearly

Repository:
- Path: {repo_path}

Incident:
- Project: {incident.get('projectName') or incident.get('projectId') or 'unknown'}
- Deployment: {incident.get('deploymentId') or 'unknown'}
- Commit: {incident.get('commitSha') or 'unknown'}
- Summary: {summary or 'No summary'}

Diagnosis:
- Category: {diagnosis.get('category') or 'unknown'}
- Hint: {diagnosis.get('hint') or 'No hint'}

Failed step:
- Name: {failed_step_meta.get('name') or 'unknown'}
- Category: {failed_step_meta.get('category') or 'unknown'}
- Command: {failed_step_meta.get('command') or 'unknown'}
- Exit code: {failed_step.get('returncode')}

Repository analysis:
{_format_analysis(analysis)}

Validation plan:
{_format_plan(context.get('plan') or [])}

Recent failed output:
```text
{failed_output or 'No failed output captured.'}
```

Repair approach:
1. Inspect only the relevant files for this failure.
2. Apply a minimal safe fix.
3. Run the most relevant local verification commands.
4. If green enough, stop and summarize the fix and validation.
5. If blocked, explain the blocker precisely.

Output expectations:
- keep the final summary short
- include files changed
- include commands rerun
- include whether the failed step seems fixed
"""

    if guide_excerpt:
        prompt += f"""

Additional product guidance:
```text
{guide_excerpt}
```
"""

    prompt += "\nFull repair context JSON follows.\n```json\n"
    prompt += json.dumps(context, indent=2)
    prompt += "\n```\n"
    return prompt


def _run_codex(repo_path: Path, prompt: str, model: str, last_message_file: Path) -> int:
    codex_bin = shutil.which("codex")
    if not codex_bin:
        print("codex CLI was not found in PATH.", file=sys.stderr)
        return 127

    command = [
        codex_bin,
        "exec",
        "--full-auto",
        "--ephemeral",
        "--color",
        "never",
        "-C",
        str(repo_path),
        "--output-last-message",
        str(last_message_file),
        "-",
    ]
    if model:
        command[2:2] = ["-m", model]

    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    assert process.stdin is not None
    assert process.stdout is not None
    process.stdin.write(prompt)
    process.stdin.close()

    for line in process.stdout:
        print(line, end="")

    code = process.wait()
    if last_message_file.exists():
        return code
    return code


def _run_claude(repo_path: Path, prompt: str, model: str, last_message_file: Path, max_turns: int) -> int:
    claude_bin = shutil.which("claude")
    if not claude_bin:
        print("claude CLI was not found in PATH.", file=sys.stderr)
        return 127

    command = [
        claude_bin,
        "-p",
        "--output-format",
        "text",
        "--max-turns",
        str(max(1, int(max_turns or 8))),
        "--dangerously-skip-permissions",
        prompt,
    ]
    if model:
        command[1:1] = ["--model", model]

    process = subprocess.Popen(
        command,
        cwd=str(repo_path),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    assert process.stdout is not None
    lines = []
    for line in process.stdout:
        lines.append(line)
        print(line, end="")
    code = process.wait()
    output = "".join(lines).strip()
    if output:
        last_message_file.write_text(output + "\n", encoding="utf-8")
    return code


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a local AI repair worker for a failed deployment incident.")
    parser.add_argument("--repo", required=True, help="Absolute path to the affected local repository.")
    parser.add_argument("--context", required=True, help="Path to the generated repair context JSON.")
    parser.add_argument("--runtime", default="codex", help="Local AI runtime to use: codex or claude.")
    parser.add_argument("--model", default="", help="Optional model override for the selected local AI runtime.")
    parser.add_argument("--max-turns", type=int, default=8, help="Maximum agentic turns for Claude print mode.")
    parser.add_argument("--dry-run", action="store_true", help="Print the generated prompt and exit.")
    args = parser.parse_args()

    repo_path = Path(args.repo).expanduser().resolve()
    context_path = Path(args.context).expanduser().resolve()
    if not repo_path.exists():
        print(f"Repository path does not exist: {repo_path}", file=sys.stderr)
        return 2
    if not context_path.exists():
        print(f"Context file does not exist: {context_path}", file=sys.stderr)
        return 2

    context = _load_json(context_path)
    runtime = str(args.runtime or "codex").strip().lower() or "codex"
    if runtime not in SUPPORTED_RUNTIMES:
        print(f"Unsupported runtime: {runtime}", file=sys.stderr)
        return 2

    runtime_label = "ChatGPT / Codex" if runtime == "codex" else "Claude"
    prompt = _build_prompt(context, repo_path, runtime_label)

    artifact_stem = _artifact_stem(context_path)
    prompt_file = context_path.with_name(f"{artifact_stem}-ai-prompt.md")
    prompt_file.write_text(prompt, encoding="utf-8")

    if args.dry_run:
        print(prompt)
        return 0

    last_message_file = context_path.with_name(f"{artifact_stem}-ai-last-message.md")
    if runtime == "claude":
        return _run_claude(
            repo_path,
            prompt,
            args.model.strip(),
            last_message_file,
            args.max_turns,
        )
    return _run_codex(repo_path, prompt, args.model.strip(), last_message_file)


if __name__ == "__main__":
    raise SystemExit(main())
