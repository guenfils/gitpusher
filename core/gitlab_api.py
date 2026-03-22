"""GitLab API client."""
import requests


class GitLabAPI:
    def __init__(self, token=None, base_url="https://gitlab.com"):
        self.token = token
        self.base_url = base_url.rstrip("/")
        self.api_url = f"{self.base_url}/api/v4"
        self.session = requests.Session()
        if token:
            self.session.headers.update({"PRIVATE-TOKEN": token})

    def set_token(self, token, base_url=None):
        self.token = token
        if base_url:
            self.base_url = base_url.rstrip("/")
            self.api_url = f"{self.base_url}/api/v4"
        self.session.headers.update({"PRIVATE-TOKEN": token})

    def get_user(self):
        try:
            r = self.session.get(f"{self.api_url}/user", timeout=10)
            if r.status_code == 200:
                return True, r.json()
            return False, r.json().get("message", "Authentication failed")
        except Exception as e:
            return False, str(e)

    def list_repos(self):
        try:
            projects = []
            page = 1
            while True:
                r = self.session.get(
                    f"{self.api_url}/projects",
                    params={
                        "membership": True,
                        "per_page": 100,
                        "page": page,
                        "order_by": "last_activity_at",
                    },
                    timeout=15
                )
                if r.status_code != 200:
                    break
                data = r.json()
                if not data:
                    break
                projects.extend(data)
                page += 1
                if len(data) < 100:
                    break
            return True, projects
        except Exception as e:
            return False, str(e)

    def create_repo(self, name, description="", visibility="private"):
        try:
            payload = {
                "name": name,
                "description": description,
                "visibility": visibility,
                "initialize_with_readme": False,
            }
            r = self.session.post(
                f"{self.api_url}/projects",
                json=payload,
                timeout=15
            )
            if r.status_code == 201:
                return True, r.json()
            return False, r.json().get("message", "Failed to create project")
        except Exception as e:
            return False, str(e)

    def add_ssh_key(self, title, key):
        try:
            r = self.session.post(
                f"{self.api_url}/user/keys",
                json={"title": title, "key": key},
                timeout=10
            )
            if r.status_code == 201:
                return True, "SSH key added successfully"
            return False, r.json().get("message", "Failed to add key")
        except Exception as e:
            return False, str(e)

    def create_merge_request(self, owner, repo, title, description,
                              source_branch, target_branch="main"):
        try:
            r = self.session.get(
                f"{self.api_url}/projects/{owner}%2F{repo}",
                timeout=10
            )
            if r.status_code != 200:
                return False, "Project not found"
            project_id = r.json()["id"]

            r2 = self.session.post(
                f"{self.api_url}/projects/{project_id}/merge_requests",
                json={
                    "title": title,
                    "description": description,
                    "source_branch": source_branch,
                    "target_branch": target_branch,
                },
                timeout=15
            )
            if r2.status_code == 201:
                return True, r2.json()
            return False, r2.json().get("message", "Failed to create MR")
        except Exception as e:
            return False, str(e)

    def get_project_id(self, owner, repo):
        try:
            import urllib.parse
            encoded = urllib.parse.quote(f"{owner}/{repo}", safe="")
            r = self.session.get(f"{self.api_url}/projects/{encoded}", timeout=10)
            if r.status_code == 200:
                return r.json().get("id")
            return None
        except Exception:
            return None

    def list_branches(self, owner, repo):
        try:
            pid = self.get_project_id(owner, repo)
            if not pid:
                return False, []
            r = self.session.get(
                f"{self.api_url}/projects/{pid}/repository/branches",
                params={"per_page": 100},
                timeout=10
            )
            if r.status_code == 200:
                return True, [b["name"] for b in r.json()]
            return False, []
        except Exception as e:
            return False, []

    def create_tag(self, owner, repo, tag_name, ref, message=""):
        try:
            pid = self.get_project_id(owner, repo)
            if not pid:
                return False, "Project not found"
            r = self.session.post(
                f"{self.api_url}/projects/{pid}/repository/tags",
                json={"tag_name": tag_name, "ref": ref, "message": message},
                timeout=15
            )
            if r.status_code == 201:
                return True, r.json()
            return False, r.json().get("message", "Failed")
        except Exception as e:
            return False, str(e)

    def create_release(self, owner, repo, tag_name, name, description=""):
        try:
            pid = self.get_project_id(owner, repo)
            if not pid:
                return False, "Project not found"
            r = self.session.post(
                f"{self.api_url}/projects/{pid}/releases",
                json={"tag_name": tag_name, "name": name, "description": description},
                timeout=15
            )
            if r.status_code == 201:
                return True, r.json()
            return False, r.json().get("message", "Failed")
        except Exception as e:
            return False, str(e)

    def list_releases(self, owner, repo):
        try:
            pid = self.get_project_id(owner, repo)
            if not pid:
                return False, []
            r = self.session.get(
                f"{self.api_url}/projects/{pid}/releases",
                params={"per_page": 20},
                timeout=10
            )
            if r.status_code == 200:
                return True, r.json()
            return False, []
        except Exception as e:
            return False, []

    def list_webhooks(self, owner, repo):
        try:
            pid = self.get_project_id(owner, repo)
            if not pid:
                return False, "Project not found"
            r = self.session.get(f"{self.api_url}/projects/{pid}/hooks", timeout=10)
            if r.status_code == 200:
                return True, r.json()
            return False, r.json().get("message", "Failed")
        except Exception as e:
            return False, str(e)

    def create_webhook(self, owner, repo, url, push_events=True,
                       merge_requests_events=False, issues_events=False,
                       tag_push_events=False, token=""):
        try:
            pid = self.get_project_id(owner, repo)
            if not pid:
                return False, "Project not found"
            payload = {
                "url": url,
                "push_events": push_events,
                "merge_requests_events": merge_requests_events,
                "issues_events": issues_events,
                "tag_push_events": tag_push_events,
            }
            if token:
                payload["token"] = token
            r = self.session.post(
                f"{self.api_url}/projects/{pid}/hooks",
                json=payload, timeout=15
            )
            if r.status_code == 201:
                return True, r.json()
            return False, r.json().get("message", "Failed")
        except Exception as e:
            return False, str(e)

    def delete_webhook(self, owner, repo, hook_id):
        try:
            pid = self.get_project_id(owner, repo)
            if not pid:
                return False, "Project not found"
            r = self.session.delete(
                f"{self.api_url}/projects/{pid}/hooks/{hook_id}",
                timeout=10
            )
            return r.status_code == 204, ""
        except Exception as e:
            return False, str(e)

    def get_https_url(self, username, repo_name):
        return f"{self.base_url}/{username}/{repo_name}.git"

    def get_ssh_url(self, username, repo_name):
        host = self.base_url.replace("https://", "").replace("http://", "")
        return f"git@{host}:{username}/{repo_name}.git"

    def search_user(self, username):
        try:
            r = self.session.get(
                f"{self.api_url}/users",
                params={"username": username}, timeout=10)
            if r.status_code == 200:
                return True, r.json()
            return False, []
        except Exception as e:
            return False, []

    def list_members(self, owner, repo):
        try:
            pid = self.get_project_id(owner, repo)
            if not pid:
                return False, "Project not found"
            r = self.session.get(
                f"{self.api_url}/projects/{pid}/members",
                params={"per_page": 100}, timeout=10)
            if r.status_code == 200:
                return True, r.json()
            return False, r.json().get("message", "Failed")
        except Exception as e:
            return False, str(e)

    def add_member(self, owner, repo, user_id, access_level=30):
        # access_level: 10=Guest,20=Reporter,30=Developer,40=Maintainer,50=Owner
        try:
            pid = self.get_project_id(owner, repo)
            if not pid:
                return False, "Project not found"
            r = self.session.post(
                f"{self.api_url}/projects/{pid}/members",
                json={"user_id": user_id, "access_level": access_level}, timeout=10)
            if r.status_code == 201:
                return True, r.json()
            return False, r.json().get("message", "Failed")
        except Exception as e:
            return False, str(e)

    def remove_member(self, owner, repo, user_id):
        try:
            pid = self.get_project_id(owner, repo)
            if not pid:
                return False, "Project not found"
            r = self.session.delete(
                f"{self.api_url}/projects/{pid}/members/{user_id}",
                timeout=10)
            return r.status_code == 204, ""
        except Exception as e:
            return False, str(e)

    def list_issues(self, owner, repo, state="opened"):
        try:
            pid = self.get_project_id(owner, repo)
            if not pid:
                return False, "Project not found"
            r = self.session.get(
                f"{self.api_url}/projects/{pid}/issues",
                params={"state": state, "per_page": 50}, timeout=10)
            if r.status_code == 200:
                return True, r.json()
            return False, r.json().get("message", "Failed")
        except Exception as e:
            return False, str(e)

    def create_issue(self, owner, repo, title, description="", labels=""):
        try:
            pid = self.get_project_id(owner, repo)
            if not pid:
                return False, "Project not found"
            payload = {"title": title, "description": description}
            if labels:
                payload["labels"] = labels
            r = self.session.post(
                f"{self.api_url}/projects/{pid}/issues",
                json=payload, timeout=15)
            if r.status_code == 201:
                return True, r.json()
            return False, r.json().get("message", "Failed")
        except Exception as e:
            return False, str(e)

    def update_issue(self, owner, repo, iid, state_event=None, title=None, description=None):
        try:
            pid = self.get_project_id(owner, repo)
            if not pid:
                return False, "Project not found"
            payload = {}
            if state_event:
                payload["state_event"] = state_event  # "close" or "reopen"
            if title:
                payload["title"] = title
            if description is not None:
                payload["description"] = description
            r = self.session.put(
                f"{self.api_url}/projects/{pid}/issues/{iid}",
                json=payload, timeout=10)
            if r.status_code == 200:
                return True, r.json()
            return False, r.json().get("message", "Failed")
        except Exception as e:
            return False, str(e)

    def list_comments(self, owner, repo, iid):
        try:
            pid = self.get_project_id(owner, repo)
            if not pid:
                return False, []
            r = self.session.get(
                f"{self.api_url}/projects/{pid}/issues/{iid}/notes",
                params={"per_page": 50}, timeout=10)
            if r.status_code == 200:
                return True, r.json()
            return False, []
        except Exception as e:
            return False, []

    def add_comment(self, owner, repo, iid, body):
        try:
            pid = self.get_project_id(owner, repo)
            if not pid:
                return False, "Project not found"
            r = self.session.post(
                f"{self.api_url}/projects/{pid}/issues/{iid}/notes",
                json={"body": body}, timeout=10)
            if r.status_code == 201:
                return True, r.json()
            return False, r.json().get("message", "Failed")
        except Exception as e:
            return False, str(e)
