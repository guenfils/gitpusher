"""GitHub API client."""
import requests


class GitHubAPI:
    BASE_URL = "https://api.github.com"

    def __init__(self, token=None):
        self.token = token
        self.session = requests.Session()
        if token:
            self.session.headers.update({
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json",
            })

    def set_token(self, token):
        self.token = token
        self.session.headers.update({
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
        })

    def get_user(self):
        try:
            r = self.session.get(f"{self.BASE_URL}/user", timeout=10)
            if r.status_code == 200:
                return True, r.json()
            return False, r.json().get("message", "Authentication failed")
        except Exception as e:
            return False, str(e)

    def list_repos(self):
        try:
            repos = []
            page = 1
            while True:
                r = self.session.get(
                    f"{self.BASE_URL}/user/repos",
                    params={"per_page": 100, "page": page, "sort": "updated"},
                    timeout=15
                )
                if r.status_code != 200:
                    break
                data = r.json()
                if not data:
                    break
                repos.extend(data)
                page += 1
                if len(data) < 100:
                    break
            return True, repos
        except Exception as e:
            return False, str(e)

    def create_repo(self, name, description="", private=False, auto_init=False):
        try:
            payload = {
                "name": name,
                "description": description,
                "private": private,
                "auto_init": auto_init,
            }
            r = self.session.post(
                f"{self.BASE_URL}/user/repos",
                json=payload,
                timeout=15
            )
            if r.status_code == 201:
                return True, r.json()
            return False, r.json().get("message", "Failed to create repository")
        except Exception as e:
            return False, str(e)

    def repo_exists(self, owner, repo_name):
        try:
            r = self.session.get(
                f"{self.BASE_URL}/repos/{owner}/{repo_name}",
                timeout=10
            )
            return r.status_code == 200, r.json() if r.status_code == 200 else None
        except Exception as e:
            return False, None

    def add_ssh_key(self, title, key):
        try:
            r = self.session.post(
                f"{self.BASE_URL}/user/keys",
                json={"title": title, "key": key},
                timeout=10
            )
            if r.status_code == 201:
                return True, "SSH key added successfully"
            msg = r.json().get("message", "Failed to add key")
            errors = r.json().get("errors", [])
            if errors:
                msg += ": " + ", ".join(e.get("message", "") for e in errors)
            return False, msg
        except Exception as e:
            return False, str(e)

    def create_pull_request(self, owner, repo, title, body, head, base="main"):
        try:
            r = self.session.post(
                f"{self.BASE_URL}/repos/{owner}/{repo}/pulls",
                json={"title": title, "body": body, "head": head, "base": base},
                timeout=15
            )
            if r.status_code == 201:
                return True, r.json()
            return False, r.json().get("message", "Failed to create PR")
        except Exception as e:
            return False, str(e)

    def list_branches(self, owner, repo):
        try:
            r = self.session.get(
                f"{self.BASE_URL}/repos/{owner}/{repo}/branches",
                params={"per_page": 100},
                timeout=10
            )
            if r.status_code == 200:
                return True, [b["name"] for b in r.json()]
            return False, []
        except Exception as e:
            return False, []

    def create_release(self, owner, repo, tag_name, name, body="", draft=False, prerelease=False):
        try:
            r = self.session.post(
                f"{self.BASE_URL}/repos/{owner}/{repo}/releases",
                json={"tag_name": tag_name, "name": name, "body": body,
                      "draft": draft, "prerelease": prerelease},
                timeout=15
            )
            if r.status_code == 201:
                return True, r.json()
            return False, r.json().get("message", "Failed")
        except Exception as e:
            return False, str(e)

    def list_releases(self, owner, repo):
        try:
            r = self.session.get(
                f"{self.BASE_URL}/repos/{owner}/{repo}/releases",
                params={"per_page": 30},
                timeout=10
            )
            if r.status_code == 200:
                return True, r.json()
            return False, []
        except Exception as e:
            return False, []

    def list_webhooks(self, owner, repo):
        try:
            r = self.session.get(
                f"{self.BASE_URL}/repos/{owner}/{repo}/hooks",
                timeout=10
            )
            if r.status_code == 200:
                return True, r.json()
            return False, r.json().get("message", "Failed")
        except Exception as e:
            return False, str(e)

    def create_webhook(self, owner, repo, url, events=None, secret="", active=True):
        if events is None:
            events = ["push"]
        try:
            config = {"url": url, "content_type": "json"}
            if secret:
                config["secret"] = secret
            r = self.session.post(
                f"{self.BASE_URL}/repos/{owner}/{repo}/hooks",
                json={"name": "web", "active": active, "events": events, "config": config},
                timeout=15
            )
            if r.status_code == 201:
                return True, r.json()
            return False, r.json().get("message", "Failed")
        except Exception as e:
            return False, str(e)

    def delete_webhook(self, owner, repo, hook_id):
        try:
            r = self.session.delete(
                f"{self.BASE_URL}/repos/{owner}/{repo}/hooks/{hook_id}",
                timeout=10
            )
            return r.status_code == 204, ""
        except Exception as e:
            return False, str(e)

    def get_https_url(self, owner, repo_name):
        return f"https://github.com/{owner}/{repo_name}.git"

    def get_ssh_url(self, owner, repo_name):
        return f"git@github.com:{owner}/{repo_name}.git"

    def list_collaborators(self, owner, repo):
        try:
            r = self.session.get(
                f"{self.BASE_URL}/repos/{owner}/{repo}/collaborators",
                params={"per_page": 100}, timeout=10)
            if r.status_code == 200:
                return True, r.json()
            return False, r.json().get("message", "Failed")
        except Exception as e:
            return False, str(e)

    def add_collaborator(self, owner, repo, username, permission="push"):
        try:
            r = self.session.put(
                f"{self.BASE_URL}/repos/{owner}/{repo}/collaborators/{username}",
                json={"permission": permission}, timeout=10)
            return r.status_code in (201, 204), r.json() if r.content else {}
        except Exception as e:
            return False, str(e)

    def remove_collaborator(self, owner, repo, username):
        try:
            r = self.session.delete(
                f"{self.BASE_URL}/repos/{owner}/{repo}/collaborators/{username}",
                timeout=10)
            return r.status_code == 204, ""
        except Exception as e:
            return False, str(e)

    def list_invitations(self, owner, repo):
        try:
            r = self.session.get(
                f"{self.BASE_URL}/repos/{owner}/{repo}/invitations",
                timeout=10)
            if r.status_code == 200:
                return True, r.json()
            return False, []
        except Exception as e:
            return False, []

    def cancel_invitation(self, owner, repo, invitation_id):
        try:
            r = self.session.delete(
                f"{self.BASE_URL}/repos/{owner}/{repo}/invitations/{invitation_id}",
                timeout=10)
            return r.status_code == 204, ""
        except Exception as e:
            return False, str(e)

    def list_issues(self, owner, repo, state="open", page=1):
        try:
            r = self.session.get(
                f"{self.BASE_URL}/repos/{owner}/{repo}/issues",
                params={"state": state, "per_page": 50, "page": page}, timeout=10)
            if r.status_code == 200:
                return True, r.json()
            return False, r.json().get("message", "Failed")
        except Exception as e:
            return False, str(e)

    def create_issue(self, owner, repo, title, body="", labels=None, assignees=None):
        try:
            payload = {"title": title, "body": body}
            if labels:
                payload["labels"] = labels
            if assignees:
                payload["assignees"] = assignees
            r = self.session.post(
                f"{self.BASE_URL}/repos/{owner}/{repo}/issues",
                json=payload, timeout=15)
            if r.status_code == 201:
                return True, r.json()
            return False, r.json().get("message", "Failed")
        except Exception as e:
            return False, str(e)

    def update_issue(self, owner, repo, number, state=None, title=None, body=None):
        try:
            payload = {}
            if state:
                payload["state"] = state
            if title:
                payload["title"] = title
            if body is not None:
                payload["body"] = body
            r = self.session.patch(
                f"{self.BASE_URL}/repos/{owner}/{repo}/issues/{number}",
                json=payload, timeout=10)
            if r.status_code == 200:
                return True, r.json()
            return False, r.json().get("message", "Failed")
        except Exception as e:
            return False, str(e)

    def list_comments(self, owner, repo, number):
        try:
            r = self.session.get(
                f"{self.BASE_URL}/repos/{owner}/{repo}/issues/{number}/comments",
                params={"per_page": 50}, timeout=10)
            if r.status_code == 200:
                return True, r.json()
            return False, []
        except Exception as e:
            return False, []

    def add_comment(self, owner, repo, number, body):
        try:
            r = self.session.post(
                f"{self.BASE_URL}/repos/{owner}/{repo}/issues/{number}/comments",
                json={"body": body}, timeout=10)
            if r.status_code == 201:
                return True, r.json()
            return False, r.json().get("message", "Failed")
        except Exception as e:
            return False, str(e)
