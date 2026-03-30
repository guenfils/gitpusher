"""NovaDeploy public API client for failed-build monitoring."""
import requests


class NovaDeployAPI:
    def __init__(self, api_base="", api_key=""):
        self.session = requests.Session()
        self.api_base = ""
        self.api_key = ""
        self.set_credentials(api_base, api_key)

    def set_credentials(self, api_base, api_key):
        self.api_base = self._normalize_base(api_base)
        self.api_key = (api_key or "").strip()
        self.session.headers.clear()
        self.session.headers.update({"Accept": "application/json"})
        if self.api_key:
            self.session.headers["x-api-key"] = self.api_key

    def _normalize_base(self, api_base):
        base = (api_base or "").strip().rstrip("/")
        if not base:
            return ""
        if base.endswith("/public/v1"):
            return base
        if base.endswith("/public"):
            return base + "/v1"
        if base.endswith("/api"):
            return base + "/public/v1"
        return base + "/public/v1"

    def _url(self, path):
        return f"{self.api_base}/{path.lstrip('/')}"

    def list_deployments(self, project_id):
        if not self.api_base:
            return False, "NovaDeploy API base is missing"
        if not self.api_key:
            return False, "NovaDeploy API key is missing"
        if not project_id:
            return False, "NovaDeploy project ID is missing"
        try:
            response = self.session.get(
                self._url(f"projects/{project_id}/deployments"),
                timeout=20,
            )
            if response.status_code == 200:
                return True, response.json()
            return False, self._error_message(response, "Failed to list deployments")
        except Exception as exc:
            return False, str(exc)

    def get_developer_logs(self, deployment_id, limit=500):
        if not self.api_base:
            return False, "NovaDeploy API base is missing"
        if not self.api_key:
            return False, "NovaDeploy API key is missing"
        if not deployment_id:
            return False, "Deployment ID is missing"
        try:
            response = self.session.get(
                self._url(f"deployments/{deployment_id}/developer-logs"),
                params={"limit": max(1, min(500, int(limit or 500)))},
                timeout=20,
            )
            if response.status_code == 200:
                return True, response.json()
            return False, self._error_message(
                response,
                f"Failed to fetch developer logs for deployment {deployment_id}",
            )
        except Exception as exc:
            return False, str(exc)

    def _error_message(self, response, fallback):
        try:
            payload = response.json()
        except Exception:
            payload = None
        if isinstance(payload, dict):
            message = payload.get("message") or payload.get("error")
            if isinstance(message, str) and message.strip():
                return message
        text = (response.text or "").strip()
        if text:
            return text[:300]
        return fallback
