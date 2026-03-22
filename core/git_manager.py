"""Git operations manager."""
import subprocess
import shutil
import os
from pathlib import Path


class GitManager:
    def __init__(self):
        self.git_path = shutil.which("git")

    def is_git_installed(self):
        return self.git_path is not None

    def get_version(self):
        result = self._run(["git", "--version"])
        return result.stdout.strip() if result.returncode == 0 else None

    def get_global_config(self, key):
        result = self._run(["git", "config", "--global", key])
        return result.stdout.strip() if result.returncode == 0 else ""

    def set_global_config(self, key, value):
        result = self._run(["git", "config", "--global", key, value])
        return result.returncode == 0

    def get_user_name(self):
        return self.get_global_config("user.name")

    def get_user_email(self):
        return self.get_global_config("user.email")

    def set_user_name(self, name):
        return self.set_global_config("user.name", name)

    def set_user_email(self, email):
        return self.set_global_config("user.email", email)

    def is_git_repo(self, path):
        result = self._run(["git", "rev-parse", "--is-inside-work-tree"], cwd=path)
        return result.returncode == 0

    def init_repo(self, path):
        result = self._run(["git", "init"], cwd=path)
        return result.returncode == 0, result.stdout + result.stderr

    def add_all(self, path):
        result = self._run(["git", "add", "."], cwd=path)
        return result.returncode == 0, result.stdout + result.stderr

    def commit(self, path, message):
        result = self._run(["git", "commit", "-m", message], cwd=path)
        return result.returncode == 0, result.stdout + result.stderr

    def has_commits(self, path):
        result = self._run(["git", "log", "--oneline", "-1"], cwd=path)
        return result.returncode == 0 and bool(result.stdout.strip())

    def get_current_branch(self, path):
        result = self._run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=path)
        if result.returncode == 0:
            return result.stdout.strip()
        return None

    def create_branch(self, path, branch_name):
        result = self._run(["git", "checkout", "-b", branch_name], cwd=path)
        return result.returncode == 0, result.stdout + result.stderr

    def checkout_branch(self, path, branch_name):
        result = self._run(["git", "checkout", branch_name], cwd=path)
        return result.returncode == 0, result.stdout + result.stderr

    def rename_branch(self, path, new_name):
        result = self._run(["git", "branch", "-M", new_name], cwd=path)
        return result.returncode == 0, result.stdout + result.stderr

    def add_remote(self, path, name, url):
        # Remove existing remote first
        self._run(["git", "remote", "remove", name], cwd=path)
        result = self._run(["git", "remote", "add", name, url], cwd=path)
        return result.returncode == 0, result.stdout + result.stderr

    def push(self, path, remote, branch, set_upstream=True, env=None):
        cmd = ["git", "push"]
        if set_upstream:
            cmd += ["-u", remote, branch]
        else:
            cmd += [remote, branch]
        result = self._run(cmd, cwd=path, env=env)
        return result.returncode == 0, result.stdout + result.stderr

    def get_status(self, path):
        result = self._run(["git", "status", "--short"], cwd=path)
        return result.stdout.strip() if result.returncode == 0 else ""

    def set_local_config(self, path, key, value):
        """Set a git config value scoped to the repo (does not touch global config)."""
        result = self._run(["git", "config", "--local", key, value], cwd=path)
        return result.returncode == 0

    def get_local_branches(self, path):
        result = self._run(
            ["git", "branch", "--format=%(refname:short)"], cwd=path
        )
        if result.returncode == 0:
            return [b.strip() for b in result.stdout.splitlines() if b.strip()]
        return []

    def get_remotes(self, path):
        result = self._run(["git", "remote", "-v"], cwd=path)
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            remotes = {}
            for line in lines:
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 2:
                        remotes[parts[0]] = parts[1]
            return remotes
        return {}

    def pull(self, path, remote="origin", branch=None, env=None):
        cmd = ["git", "pull", remote]
        if branch:
            cmd.append(branch)
        result = self._run(cmd, cwd=path, env=env)
        return result.returncode == 0, result.stdout + result.stderr

    def fetch(self, path, remote="origin", env=None):
        result = self._run(["git", "fetch", remote], cwd=path, env=env)
        return result.returncode == 0, result.stdout + result.stderr

    def clone(self, url, dest_path, branch=None, env=None):
        cmd = ["git", "clone", url, dest_path]
        if branch:
            cmd += ["--branch", branch]
        result = self._run(cmd, env=env)
        return result.returncode == 0, result.stdout + result.stderr

    def get_tags(self, path):
        result = self._run(
            ["git", "tag", "-l", "--sort=-version:refname", "--format=%(refname:short)|%(creatordate:short)|%(subject)"],
            cwd=path
        )
        tags = []
        if result.returncode == 0:
            for line in result.stdout.strip().splitlines():
                parts = line.split("|")
                tags.append({
                    "name": parts[0] if len(parts) > 0 else "",
                    "date": parts[1] if len(parts) > 1 else "",
                    "message": parts[2] if len(parts) > 2 else "",
                })
        return tags

    def create_tag(self, path, tag_name, message=None):
        if message:
            cmd = ["git", "tag", "-a", tag_name, "-m", message]
        else:
            cmd = ["git", "tag", tag_name]
        result = self._run(cmd, cwd=path)
        return result.returncode == 0, result.stdout + result.stderr

    def push_tags(self, path, remote, env=None):
        result = self._run(["git", "push", remote, "--tags"], cwd=path, env=env)
        return result.returncode == 0, result.stdout + result.stderr

    def get_last_commit(self, path):
        result = self._run(
            ["git", "log", "-1", "--pretty=format:%H|%s|%an|%ar"],
            cwd=path
        )
        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split("|")
            return {
                "hash": parts[0][:8] if len(parts) > 0 else "",
                "message": parts[1] if len(parts) > 1 else "",
                "author": parts[2] if len(parts) > 2 else "",
                "when": parts[3] if len(parts) > 3 else "",
            }
        return None

    def get_remote_url(self, path, remote="origin"):
        result = self._run(["git", "remote", "get-url", remote], cwd=path)
        return result.stdout.strip() if result.returncode == 0 else ""

    def get_log(self, path, branch=None, max_count=100):
        """Return list of commits as dicts."""
        cmd = [
            "git", "log",
            f"--max-count={max_count}",
            "--pretty=format:%H|%h|%s|%an|%ae|%ar|%D",
        ]
        if branch:
            cmd.append(branch)
        result = self._run(cmd, cwd=path)
        commits = []
        if result.returncode == 0:
            for line in result.stdout.strip().splitlines():
                if not line.strip():
                    continue
                parts = line.split("|")
                refs = parts[6].strip() if len(parts) > 6 else ""
                tags = [r.strip().replace("tag: ", "") for r in refs.split(",") if "tag:" in r]
                branches = [r.strip() for r in refs.split(",") if r.strip() and "tag:" not in r and "->" not in r and r.strip()]
                commits.append({
                    "hash":    parts[0].strip() if len(parts) > 0 else "",
                    "short":   parts[1].strip() if len(parts) > 1 else "",
                    "message": parts[2].strip() if len(parts) > 2 else "",
                    "author":  parts[3].strip() if len(parts) > 3 else "",
                    "email":   parts[4].strip() if len(parts) > 4 else "",
                    "when":    parts[5].strip() if len(parts) > 5 else "",
                    "tags":    tags,
                    "branches": branches,
                })
        return commits

    def get_branches(self, path):
        """Return list of local branch names."""
        result = self._run(["git", "branch", "--format=%(refname:short)"], cwd=path)
        if result.returncode == 0:
            return [b.strip() for b in result.stdout.splitlines() if b.strip()]
        return []

    def get_contributor_stats(self, path):
        """Return list of (commit_count, author_name) sorted by count desc."""
        result = self._run(
            ["git", "shortlog", "-sn", "--no-merges", "HEAD"],
            cwd=path
        )
        contributors = []
        if result.returncode == 0:
            for line in result.stdout.strip().splitlines():
                line = line.strip()
                if not line:
                    continue
                parts = line.split("\t", 1)
                if len(parts) == 2:
                    try:
                        count = int(parts[0].strip())
                        name = parts[1].strip()
                        contributors.append({"name": name, "count": count})
                    except ValueError:
                        pass
        return contributors

    def get_commits_by_month(self, path, months=12):
        """Return dict {YYYY-MM: count} for the last N months."""
        result = self._run(
            ["git", "log", "--pretty=format:%ad", "--date=format:%Y-%m", "HEAD"],
            cwd=path
        )
        from collections import Counter
        from datetime import datetime, timedelta
        counts = Counter()
        if result.returncode == 0:
            for line in result.stdout.strip().splitlines():
                if line.strip():
                    counts[line.strip()] += 1
        # Build ordered dict for last N months
        ordered = {}
        now = datetime.now()
        for i in range(months - 1, -1, -1):
            d = now.replace(day=1) - timedelta(days=i * 28)
            key = d.strftime("%Y-%m")
            ordered[key] = counts.get(key, 0)
        return ordered

    def get_total_commits(self, path):
        result = self._run(["git", "rev-list", "--count", "HEAD"], cwd=path)
        try:
            return int(result.stdout.strip()) if result.returncode == 0 else 0
        except ValueError:
            return 0

    def get_most_changed_files(self, path, limit=10):
        """Return list of (change_count, filepath) sorted desc."""
        result = self._run(
            ["git", "log", "--pretty=format:", "--name-only", "--no-merges", "HEAD"],
            cwd=path
        )
        from collections import Counter
        counts = Counter()
        if result.returncode == 0:
            for line in result.stdout.strip().splitlines():
                line = line.strip()
                if line:
                    counts[line] += 1
        return [{"file": f, "count": c} for f, c in counts.most_common(limit)]

    def get_first_commit_date(self, path):
        result = self._run(
            ["git", "log", "--reverse", "--pretty=format:%ad", "--date=short", "HEAD"],
            cwd=path
        )
        if result.returncode == 0:
            lines = [l.strip() for l in result.stdout.strip().splitlines() if l.strip()]
            return lines[0] if lines else ""
        return ""

    # ── Stash methods ────────────────────────────────────────────
    def stash_list(self, path):
        result = self._run(
            ["git", "stash", "list", "--format=%gd|%s|%cr"],
            cwd=path
        )
        stashes = []
        if result.returncode == 0:
            for line in result.stdout.strip().splitlines():
                if not line.strip():
                    continue
                parts = line.split("|", 2)
                stashes.append({
                    "ref":     parts[0].strip() if len(parts) > 0 else "",
                    "message": parts[1].strip() if len(parts) > 1 else "",
                    "when":    parts[2].strip() if len(parts) > 2 else "",
                })
        return stashes

    def stash_push(self, path, message=None, include_untracked=False):
        cmd = ["git", "stash", "push"]
        if include_untracked:
            cmd.append("-u")
        if message:
            cmd += ["-m", message]
        result = self._run(cmd, cwd=path)
        return result.returncode == 0, result.stdout + result.stderr

    def stash_pop(self, path, stash_ref="stash@{0}"):
        result = self._run(["git", "stash", "pop", stash_ref], cwd=path)
        return result.returncode == 0, result.stdout + result.stderr

    def stash_apply(self, path, stash_ref="stash@{0}"):
        result = self._run(["git", "stash", "apply", stash_ref], cwd=path)
        return result.returncode == 0, result.stdout + result.stderr

    def stash_drop(self, path, stash_ref="stash@{0}"):
        result = self._run(["git", "stash", "drop", stash_ref], cwd=path)
        return result.returncode == 0, result.stdout + result.stderr

    def stash_show(self, path, stash_ref="stash@{0}"):
        result = self._run(["git", "stash", "show", "-p", stash_ref], cwd=path)
        return result.stdout if result.returncode == 0 else result.stderr

    # ── Branch management methods ─────────────────────────────────
    def get_all_branches(self, path):
        """Return list of dicts for local and remote branches."""
        result = self._run(
            ["git", "branch", "-a", "--format=%(refname:short)|%(objectname:short)|%(upstream:short)|%(HEAD)"],
            cwd=path
        )
        branches = []
        if result.returncode == 0:
            for line in result.stdout.strip().splitlines():
                if not line.strip():
                    continue
                parts = line.split("|")
                name = parts[0].strip() if len(parts) > 0 else ""
                if not name or name.startswith("HEAD"):
                    continue
                is_remote = name.startswith("remotes/")
                display = name.replace("remotes/", "")
                branches.append({
                    "name":     name,
                    "display":  display,
                    "short":    parts[1].strip() if len(parts) > 1 else "",
                    "upstream": parts[2].strip() if len(parts) > 2 else "",
                    "current":  parts[3].strip() == "*" if len(parts) > 3 else False,
                    "remote":   is_remote,
                })
        return branches

    def delete_branch(self, path, branch_name, force=False):
        flag = "-D" if force else "-d"
        result = self._run(["git", "branch", flag, branch_name], cwd=path)
        return result.returncode == 0, result.stdout + result.stderr

    def merge_branch(self, path, branch_name, no_ff=True):
        cmd = ["git", "merge"]
        if no_ff:
            cmd.append("--no-ff")
        cmd.append(branch_name)
        result = self._run(cmd, cwd=path)
        return result.returncode == 0, result.stdout + result.stderr

    def compare_branches(self, path, base, compare):
        """Return commits in compare not in base."""
        result = self._run(
            ["git", "log", f"{base}..{compare}", "--pretty=format:%h|%s|%an|%ar"],
            cwd=path
        )
        commits = []
        if result.returncode == 0:
            for line in result.stdout.strip().splitlines():
                if not line.strip():
                    continue
                parts = line.split("|")
                commits.append({
                    "short":   parts[0].strip() if len(parts) > 0 else "",
                    "message": parts[1].strip() if len(parts) > 1 else "",
                    "author":  parts[2].strip() if len(parts) > 2 else "",
                    "when":    parts[3].strip() if len(parts) > 3 else "",
                })
        return commits

    def get_branch_diff_stat(self, path, base, compare):
        result = self._run(["git", "diff", "--stat", f"{base}...{compare}"], cwd=path)
        return result.stdout if result.returncode == 0 else result.stderr

    # ── Diff methods ──────────────────────────────────────────────
    def get_diff(self, path, staged=False, filepath=None):
        cmd = ["git", "diff"]
        if staged:
            cmd.append("--cached")
        if filepath:
            cmd += ["--", filepath]
        result = self._run(cmd, cwd=path)
        return result.stdout if result.returncode == 0 else result.stderr

    def get_changed_files(self, path, staged=False):
        """Return list of changed files with +/- counts."""
        cmd = ["git", "diff", "--numstat"]
        if staged:
            cmd.append("--cached")
        result = self._run(cmd, cwd=path)
        files = []
        if result.returncode == 0:
            for line in result.stdout.strip().splitlines():
                parts = line.split("\t")
                if len(parts) == 3:
                    try:
                        added   = int(parts[0]) if parts[0] != "-" else 0
                        removed = int(parts[1]) if parts[1] != "-" else 0
                    except ValueError:
                        added = removed = 0
                    files.append({"added": added, "removed": removed, "file": parts[2].strip()})
        return files

    def stage_file(self, path, filepath):
        result = self._run(["git", "add", filepath], cwd=path)
        return result.returncode == 0, result.stdout + result.stderr

    def unstage_file(self, path, filepath):
        result = self._run(["git", "restore", "--staged", filepath], cwd=path)
        return result.returncode == 0, result.stdout + result.stderr

    def discard_file(self, path, filepath):
        result = self._run(["git", "restore", filepath], cwd=path)
        return result.returncode == 0, result.stdout + result.stderr

    # ── Gitflow methods ───────────────────────────────────────────
    def gitflow_has_develop(self, path):
        branches = self.get_branches(path)
        return "develop" in branches

    def gitflow_init(self, path, main_branch="main", develop_branch="develop"):
        self._run(["git", "checkout", main_branch], cwd=path)
        if develop_branch not in self.get_branches(path):
            result = self._run(["git", "checkout", "-b", develop_branch], cwd=path)
            return result.returncode == 0, result.stdout + result.stderr
        return True, "develop branch already exists"

    def gitflow_start(self, path, prefix, name, base="develop"):
        branch = f"{prefix}/{name}"
        self._run(["git", "checkout", base], cwd=path)
        result = self._run(["git", "checkout", "-b", branch], cwd=path)
        return result.returncode == 0, branch, result.stdout + result.stderr

    def gitflow_finish(self, path, prefix, name, main_branch="main", tag_version=None):
        branch = f"{prefix}/{name}"
        logs = []
        errors = []

        ok, out = self._do_merge(path, "develop", branch, logs)
        if not ok:
            errors.append(f"Merge to develop failed: {out}")

        if prefix in ("release", "hotfix"):
            ok2, out2 = self._do_merge(path, main_branch, branch, logs)
            if not ok2:
                errors.append(f"Merge to {main_branch} failed: {out2}")
            if tag_version:
                self._run(["git", "tag", "-a", tag_version, "-m", f"{prefix} {name}"], cwd=path)
                logs.append(f"Tag {tag_version} created")

        self._run(["git", "branch", "-d", branch], cwd=path)
        logs.append(f"Branch {branch} deleted")

        self._run(["git", "checkout", "develop"], cwd=path)

        return len(errors) == 0, "\n".join(logs + errors)

    def _do_merge(self, path, target, source, logs):
        self._run(["git", "checkout", target], cwd=path)
        result = self._run(["git", "merge", "--no-ff", source, "-m", f"Merge {source} into {target}"], cwd=path)
        ok = result.returncode == 0
        logs.append(f"{'OK' if ok else 'FAIL'} Merged {source} -> {target}")
        return ok, result.stdout + result.stderr

    def gitflow_list(self, path, prefix):
        """List branches with given prefix."""
        branches = self.get_branches(path)
        return [b for b in branches if b.startswith(f"{prefix}/")]

    def _run(self, cmd, cwd=None, env=None):
        run_env = os.environ.copy()
        if env:
            run_env.update(env)
        try:
            return subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=cwd,
                env=run_env,
                timeout=60,
            )
        except subprocess.TimeoutExpired:
            class Fake:
                returncode = 1
                stdout = ""
                stderr = "Timeout: operation took too long"
            return Fake()
        except Exception as e:
            class Fake:
                returncode = 1
                stdout = ""
                stderr = str(e)
            return Fake()
