"""SecretScanner — checks filenames for potential secrets (no file contents read)."""
import os
import fnmatch

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv"}

HIGH_PATTERNS = [
    ".env", ".env.local", ".env.production", ".env.development",
]
HIGH_WILDCARDS = [".env.*", "*.pem", "*.key", "*.p12", "*.pfx"]

MEDIUM_ROOT = [
    "credentials.json", "secrets.json", "secret.json", "config.json",
]
MEDIUM_WILDCARDS_ROOT = ["*.sqlite", "*.db"]


def _matches_any(name, patterns):
    for pat in patterns:
        if fnmatch.fnmatch(name, pat):
            return True
    return False


class SecretScanner:
    def scan(self, path):
        findings = []
        try:
            # Top 2 levels: root + immediate subdirectories
            for depth, (root, dirs, files) in enumerate(os.walk(path)):
                # Remove skip dirs in place
                dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

                rel_root = os.path.relpath(root, path)
                is_root = rel_root == "."

                for fname in files:
                    rel_file = fname if is_root else os.path.join(rel_root, fname)

                    # High severity — env files (any level up to depth 2)
                    if fname in HIGH_PATTERNS or _matches_any(fname, HIGH_WILDCARDS):
                        findings.append({
                            "file": rel_file,
                            "reason": "Environment file with potential secrets"
                            if (fname.startswith(".env") or fname in HIGH_PATTERNS)
                            else "Private key or certificate",
                            "severity": "high",
                        })
                        continue

                    # Medium severity — only at root level
                    if is_root:
                        if fname in MEDIUM_ROOT:
                            findings.append({
                                "file": rel_file,
                                "reason": "Possible credentials file",
                                "severity": "medium",
                            })
                        elif _matches_any(fname, MEDIUM_WILDCARDS_ROOT):
                            findings.append({
                                "file": rel_file,
                                "reason": "Database file",
                                "severity": "medium",
                            })

                # Stop after 2 levels (depth 0 = root, depth 1 = immediate children)
                if depth >= 1:
                    dirs.clear()
        except OSError:
            pass
        return findings

    def add_to_gitignore(self, path, filenames):
        gi_path = os.path.join(path, ".gitignore")
        existing_lines = set()
        if os.path.exists(gi_path):
            try:
                with open(gi_path, "r", encoding="utf-8", errors="replace") as f:
                    existing_lines = set(f.read().splitlines())
            except OSError:
                pass

        to_add = [fn for fn in filenames if fn not in existing_lines]
        if not to_add:
            return

        with open(gi_path, "a", encoding="utf-8") as f:
            f.write("\n# Sensitive files (added by Git Pusher)\n")
            for fn in to_add:
                f.write(fn + "\n")
