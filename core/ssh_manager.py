"""SSH key management for GitHub and GitLab."""
import os
import subprocess
from pathlib import Path


class SSHManager:
    def __init__(self):
        self.ssh_dir = Path.home() / ".ssh"
        self.ssh_dir.mkdir(mode=0o700, exist_ok=True)

    def get_existing_keys(self):
        """Return list of existing SSH key pairs."""
        keys = []
        for f in self.ssh_dir.glob("*.pub"):
            private = f.with_suffix("")
            if private.exists():
                keys.append({
                    "name": f.stem,
                    "public": str(f),
                    "private": str(private),
                })
        return keys

    def get_public_key(self, key_name="id_ed25519"):
        pub_path = self.ssh_dir / f"{key_name}.pub"
        if pub_path.exists():
            return pub_path.read_text().strip()
        return None

    def generate_key(self, email, key_name="id_ed25519", passphrase=""):
        """Generate a new SSH key pair."""
        key_path = self.ssh_dir / key_name
        if key_path.exists():
            return True, f"Key already exists at {key_path}", str(key_path)

        cmd = [
            "ssh-keygen",
            "-t", "ed25519",
            "-C", email,
            "-f", str(key_path),
            "-N", passphrase,
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                pub_key = self.get_public_key(key_name)
                return True, pub_key, str(key_path)
            return False, result.stderr, None
        except Exception as e:
            return False, str(e), None

    def start_ssh_agent(self):
        """Start ssh-agent and return environment variables."""
        try:
            result = subprocess.run(
                ["ssh-agent", "-s"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                env = {}
                for line in result.stdout.split(";"):
                    if "=" in line and "SSH_AUTH_SOCK" in line:
                        parts = line.strip().split("=")
                        if len(parts) == 2:
                            env["SSH_AUTH_SOCK"] = parts[1]
                    elif "=" in line and "SSH_AGENT_PID" in line:
                        parts = line.strip().split("=")
                        if len(parts) == 2:
                            env["SSH_AGENT_PID"] = parts[1]
                return env
            return {}
        except Exception:
            return {}

    def add_key_to_agent(self, key_path):
        """Add SSH key to agent."""
        try:
            result = subprocess.run(
                ["ssh-add", key_path],
                capture_output=True, text=True, timeout=15
            )
            return result.returncode == 0, result.stdout + result.stderr
        except Exception as e:
            return False, str(e)

    def test_connection(self, host="github.com"):
        """Test SSH connection to a host."""
        try:
            result = subprocess.run(
                ["ssh", "-T", "-o", "StrictHostKeyChecking=no",
                 "-o", "ConnectTimeout=10", f"git@{host}"],
                capture_output=True, text=True, timeout=15
            )
            output = result.stdout + result.stderr
            # GitHub/GitLab return exit code 1 but with success message
            if "successfully authenticated" in output.lower():
                return True, output
            if result.returncode == 0:
                return True, output
            return False, output
        except Exception as e:
            return False, str(e)

    def update_ssh_config(self, host, hostname, key_path, user="git"):
        """Add/update SSH config entry."""
        config_path = self.ssh_dir / "config"
        entry = (
            f"\nHost {host}\n"
            f"    HostName {hostname}\n"
            f"    User {user}\n"
            f"    IdentityFile {key_path}\n"
            f"    StrictHostKeyChecking no\n"
        )
        existing = config_path.read_text() if config_path.exists() else ""
        if f"Host {host}" not in existing:
            with open(config_path, "a") as f:
                f.write(entry)
            config_path.chmod(0o600)
        return True
