"""Reusable preflight and bootstrap helpers for Git Pusher dev mode."""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

REQUIRED_IMPORTS = [
    ("customtkinter", "customtkinter"),
    ("Pillow", "PIL"),
    ("requests", "requests"),
    ("paramiko", "paramiko"),
    ("cryptography", "cryptography"),
    ("darkdetect", "darkdetect"),
]

OPTIONAL_IMPORTS = [
    ("tkinter", "tkinter"),
    ("venv", "venv"),
]

AI_BINARIES = [
    ("ChatGPT / Codex CLI", "codex"),
    ("Claude CLI", "claude"),
]


def _run(cmd, *, cwd=None, env=None):
    try:
        result = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            env=env,
            capture_output=True,
            text=True,
        )
    except Exception as exc:
        return {
            "ok": False,
            "returncode": -1,
            "stdout": "",
            "stderr": str(exc),
        }
    return {
        "ok": result.returncode == 0,
        "returncode": result.returncode,
        "stdout": result.stdout or "",
        "stderr": result.stderr or "",
    }


def _detect_node_runtime():
    node = shutil.which("node")
    npm = shutil.which("npm")
    if node and npm:
        node_version = _run([node, "-v"]).get("stdout", "").strip()
        npm_version = _run([npm, "-v"]).get("stdout", "").strip()
        return {
            "ok": True,
            "source": "system-path",
            "node": node,
            "npm": npm,
            "summary": f"{node_version} / npm {npm_version} (system-path)".strip(),
        }

    nvm_root = Path(os.environ.get("NVM_DIR") or (Path.home() / ".nvm"))
    versions_root = nvm_root / "versions" / "node"
    if versions_root.exists():
        version_dirs = [path for path in versions_root.iterdir() if path.is_dir() and path.name.startswith("v")]
        version_dirs.sort(reverse=True)
        preferred = [path for path in version_dirs if path.name.startswith("v20.")]
        fallback = [path for path in version_dirs if path not in preferred]
        candidates = preferred + fallback
        for path in candidates:
            node_path = path / "bin" / "node"
            npm_path = path / "bin" / "npm"
            if not node_path.exists() or not npm_path.exists():
                continue
            env = os.environ.copy()
            env["PATH"] = f"{path / 'bin'}:{env.get('PATH', '')}"
            node_version = _run([str(node_path), "-v"], env=env).get("stdout", "").strip()
            npm_version = _run([str(npm_path), "-v"], env=env).get("stdout", "").strip()
            return {
                "ok": True,
                "source": "nvm",
                "node": str(node_path),
                "npm": str(npm_path),
                "summary": f"{node_version} / npm {npm_version} (nvm)".strip(),
            }
    return {
        "ok": False,
        "source": "missing",
        "node": "",
        "npm": "",
        "summary": "missing",
    }


def _detect_ai_runtimes():
    results = []
    for label, binary_name in AI_BINARIES:
        binary = shutil.which(binary_name)
        version = ""
        if binary:
            version = _run([binary, "--version"]).get("stdout", "").strip()
        results.append(
            {
                "name": label,
                "binary": binary_name,
                "ok": bool(binary),
                "path": binary or "",
                "version": version,
            }
        )
    return results


def _check_imports(modules):
    results = []
    for label, module_name in modules:
        found = importlib.util.find_spec(module_name) is not None
        results.append(
            {
                "name": label,
                "module": module_name,
                "ok": found,
            }
        )
    return results


def _check_imports_with_python(python_path, modules):
    checks = []
    for label, module_name in modules:
        result = _run(
            [
                str(python_path),
                "-c",
                f"import importlib.util, sys; sys.exit(0 if importlib.util.find_spec({module_name!r}) else 1)",
            ]
        )
        checks.append(
            {
                "name": label,
                "module": module_name,
                "ok": result["ok"],
            }
        )
    return checks


def _site_config_paths():
    root_override = str(os.environ.get("GIT_PUSHER_CONFIG_ROOT") or "").strip()
    root = Path(root_override).expanduser() if root_override else (Path.home() / ".config" / "git-pusher")
    return {
        "root": root,
        "failures": root / "novadeploy-failures",
        "runtime": root / "runtime",
    }


def _path_writable(path):
    path = Path(path)
    target = path if path.exists() else path.parent
    try:
        return os.access(str(target), os.W_OK)
    except Exception:
        return False


def collect_preflight(repo_root, *, interpreter=None, target_python=None):
    repo_root = Path(repo_root).resolve()
    interpreter = str(interpreter or sys.executable)
    target_python = str(target_python or interpreter)
    python_info = _run([interpreter, "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"])
    target_info = _run([target_python, "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"])
    git_path = shutil.which("git")
    pip_path = shutil.which("pip3") or shutil.which("pip")
    config_paths = _site_config_paths()
    report = {
        "repo_root": str(repo_root),
        "python": {
            "ok": python_info["ok"],
            "path": interpreter,
            "version": python_info["stdout"].strip(),
        },
        "target_python": {
            "ok": target_info["ok"],
            "path": target_python,
            "version": target_info["stdout"].strip(),
        },
        "git": {
            "ok": bool(git_path),
            "path": git_path or "",
            "version": _run([git_path, "--version"]).get("stdout", "").strip() if git_path else "",
        },
        "pip": {
            "ok": bool(pip_path),
            "path": pip_path or "",
            "version": _run([pip_path, "--version"]).get("stdout", "").strip() if pip_path else "",
        },
        "imports": _check_imports(REQUIRED_IMPORTS),
        "optional_imports": _check_imports(OPTIONAL_IMPORTS),
        "target_imports": _check_imports_with_python(target_python, REQUIRED_IMPORTS) if Path(target_python).exists() else [],
        "node": _detect_node_runtime(),
        "ai_runtimes": _detect_ai_runtimes(),
        "requirements_file": str(repo_root / "requirements.txt"),
        "config_paths": {key: str(value) for key, value in config_paths.items()},
        "config_writable": {key: _path_writable(value) for key, value in config_paths.items()},
        "venv_path": str(repo_root / ".venv"),
        "venv_exists": (repo_root / ".venv" / "bin" / "python").exists(),
    }
    report["ok"] = bool(
        report["python"]["ok"]
        and report["git"]["ok"]
        and all(item["ok"] for item in report["imports"])
    )
    return report


def ensure_config_dirs():
    created = []
    failed = []
    for path in _site_config_paths().values():
        try:
            path.mkdir(parents=True, exist_ok=True)
            created.append(str(path))
        except Exception as exc:
            failed.append({"path": str(path), "error": str(exc)})
    return {
        "ok": not failed,
        "created": created,
        "failed": failed,
    }


def ensure_venv(repo_root, *, base_python="python3"):
    repo_root = Path(repo_root).resolve()
    venv_python = repo_root / ".venv" / "bin" / "python"
    if venv_python.exists():
        return {"ok": True, "created": False, "python": str(venv_python)}
    result = _run([base_python, "-m", "venv", str(repo_root / ".venv")], cwd=repo_root)
    return {
        "ok": result["ok"] and venv_python.exists(),
        "created": True,
        "python": str(venv_python),
        "stderr": result["stderr"].strip(),
    }


def install_requirements(repo_root, *, python_path):
    repo_root = Path(repo_root).resolve()
    requirements = repo_root / "requirements.txt"
    if not requirements.exists():
        return {"ok": False, "reason": "requirements.txt not found"}
    result = _run([str(python_path), "-m", "pip", "install", "-r", str(requirements)], cwd=repo_root)
    return {
        "ok": result["ok"],
        "stdout": result["stdout"].strip(),
        "stderr": result["stderr"].strip(),
    }


def bootstrap_dev(repo_root, *, base_python="python3", install_missing=False):
    repo_root = Path(repo_root).resolve()
    config_result = ensure_config_dirs()
    venv_result = ensure_venv(repo_root, base_python=base_python)
    final_python = venv_result.get("python") if venv_result.get("ok") else base_python
    install_result = {
        "ok": True,
        "skipped": True,
        "stdout": "",
        "stderr": "",
    }
    if install_missing and venv_result.get("ok"):
        install_result = install_requirements(repo_root, python_path=final_python)
        install_result["skipped"] = False
    report = collect_preflight(repo_root, interpreter=base_python, target_python=final_python)
    host_imports_ok = all(item["ok"] for item in (report.get("imports") or []))
    target_imports = report.get("target_imports") or []
    target_imports_ok = all(item["ok"] for item in target_imports) if target_imports else host_imports_ok
    report["bootstrap"] = {
        "config_dirs": config_result,
        "venv": venv_result,
        "install": install_result,
    }
    report["host_imports_ok"] = host_imports_ok
    report["target_imports_ok"] = target_imports_ok
    report["ok"] = bool(
        report["python"]["ok"]
        and report["git"]["ok"]
        and config_result.get("ok")
        and venv_result.get("ok")
        and (install_result.get("ok") or install_result.get("skipped"))
        and (target_imports_ok if install_missing else True)
    )
    return report


def format_report(report):
    lines = [
        "Git Pusher Dev Preflight",
        f"Repo: {report.get('repo_root')}",
        "",
        f"Python: {'OK' if report['python']['ok'] else 'FAIL'}  {report['python']['version'] or report['python']['path']}",
        f"Target Python: {'OK' if report['target_python']['ok'] else 'FAIL'}  {report['target_python']['version'] or report['target_python']['path']}",
        f"Git: {'OK' if report['git']['ok'] else 'FAIL'}  {report['git']['version'] or 'missing'}",
        f"Pip: {'OK' if report['pip']['ok'] else 'WARN'}  {report['pip']['version'] or 'missing'}",
        f"Node: {'OK' if report['node']['ok'] else 'WARN'}  {report['node']['summary']}",
        "",
        "Required imports:",
    ]
    for item in report.get("imports") or []:
        lines.append(f"- {item['name']}: {'OK' if item['ok'] else 'MISSING'}")
    if report.get("target_imports"):
        lines.extend(["", "Target env imports:"])
        for item in report["target_imports"]:
            lines.append(f"- {item['name']}: {'OK' if item['ok'] else 'MISSING'}")
    if report.get("ai_runtimes"):
        lines.extend(["", "Local AI runtimes:"])
        for item in report["ai_runtimes"]:
            details = item["version"] or item["path"] or item["binary"]
            lines.append(f"- {item['name']}: {'OK' if item['ok'] else 'MISSING'}  {details}")
    lines.extend(["", "Config paths:"])
    for key, path in (report.get("config_paths") or {}).items():
        lines.append(f"- {key}: {path}")
    bootstrap = report.get("bootstrap") or {}
    if bootstrap:
        lines.extend(["", "Bootstrap:"])
        config_dirs = bootstrap.get("config_dirs") or {}
        lines.append(f"- config dirs: {'OK' if config_dirs.get('ok') else 'FAIL'}")
        for item in config_dirs.get("failed") or []:
            lines.append(f"  {item['path']}: {item['error']}")
        venv = bootstrap.get("venv") or {}
        install = bootstrap.get("install") or {}
        lines.append(f"- venv: {'OK' if venv.get('ok') else 'FAIL'}  {venv.get('python') or 'missing'}")
        if install.get("skipped"):
            lines.append("- install: skipped")
        else:
            lines.append(f"- install: {'OK' if install.get('ok') else 'FAIL'}")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Git Pusher dev preflight and bootstrap")
    parser.add_argument("--repo-root", default=Path(__file__).resolve().parent.parent, help="Repo root")
    parser.add_argument("--bootstrap", action="store_true", help="Create config dirs and local .venv")
    parser.add_argument("--install-missing", action="store_true", help="Install requirements into .venv during bootstrap")
    parser.add_argument("--json", action="store_true", help="Print JSON report")
    parser.add_argument("--base-python", default="python3", help="Base Python executable")
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    if args.bootstrap:
        report = bootstrap_dev(
            repo_root,
            base_python=args.base_python,
            install_missing=bool(args.install_missing),
        )
    else:
        target_python = repo_root / ".venv" / "bin" / "python"
        report = collect_preflight(
            repo_root,
            interpreter=args.base_python,
            target_python=str(target_python) if target_python.exists() else args.base_python,
        )

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(format_report(report))

    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
