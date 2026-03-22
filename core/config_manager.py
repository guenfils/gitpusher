"""Persistent configuration manager."""
import json
import os
from pathlib import Path


CONFIG_PATH = Path.home() / ".config" / "git-pusher" / "config.json"


class ConfigManager:
    def __init__(self):
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        self._data = self._load()

    def _load(self):
        if CONFIG_PATH.exists():
            try:
                return json.loads(CONFIG_PATH.read_text())
            except Exception:
                pass
        return {}

    def save(self):
        CONFIG_PATH.write_text(json.dumps(self._data, indent=2))

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value
        self.save()

    def delete(self, key):
        self._data.pop(key, None)
        self.save()

    # Convenience helpers
    def get_github_token(self):
        return self.get("github_token", "")

    def set_github_token(self, token):
        self.set("github_token", token)

    def get_gitlab_token(self):
        return self.get("gitlab_token", "")

    def set_gitlab_token(self, token):
        self.set("gitlab_token", token)

    def get_gitlab_url(self):
        return self.get("gitlab_url", "https://gitlab.com")

    def set_gitlab_url(self, url):
        self.set("gitlab_url", url)

    def get_auth_method(self):
        return self.get("auth_method", "token")

    def set_auth_method(self, method):
        self.set("auth_method", method)

    def get_ssh_key_name(self):
        return self.get("ssh_key_name", "id_ed25519")

    def set_ssh_key_name(self, name):
        self.set("ssh_key_name", name)

    def get_last_project_path(self):
        return self.get("last_project_path", "")

    def set_last_project_path(self, path):
        self.set("last_project_path", path)

    # ── Preferences ────────────────────────────────────────────
    def get_default_branch(self):
        return self.get("default_branch", "main")

    def set_default_branch(self, v):
        self.set("default_branch", v)

    def get_default_commit_msg(self):
        return self.get("default_commit_msg", "Initial commit")

    def set_default_commit_msg(self, v):
        self.set("default_commit_msg", v)

    def get_default_visibility(self):
        return self.get("default_visibility", "private")

    def set_default_visibility(self, v):
        self.set("default_visibility", v)

    def get_watch_interval(self):
        return self.get("watch_interval", "10 min")

    def set_watch_interval(self, v):
        self.set("watch_interval", v)

    def get_watch_msg_template(self):
        return self.get("watch_msg_template", "Auto-commit {datetime}")

    def set_watch_msg_template(self, v):
        self.set("watch_msg_template", v)

    def get_export_exclude(self):
        return self.get("export_exclude", ".git,node_modules,__pycache__,.venv,dist,build,*.pyc")

    def set_export_exclude(self, v):
        self.set("export_exclude", v)

    def get_export_format(self):
        return self.get("export_format", "ZIP")

    def set_export_format(self, v):
        self.set("export_format", v)

    def get_skip_readme_step(self):
        return self.get("skip_readme_step", False)

    def set_skip_readme_step(self, v):
        self.set("skip_readme_step", v)

    def get_skip_gitignore_step(self):
        return self.get("skip_gitignore_step", False)

    def set_skip_gitignore_step(self, v):
        self.set("skip_gitignore_step", v)

    def get_gitflow_main(self):
        return self.get("gitflow_main", "main")

    def set_gitflow_main(self, v):
        self.set("gitflow_main", v)

    def get_gitflow_develop(self):
        return self.get("gitflow_develop", "develop")

    def set_gitflow_develop(self, v):
        self.set("gitflow_develop", v)

    def get_all(self):
        return dict(self._data)
