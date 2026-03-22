"""GitignoreManager — detects languages and generates .gitignore content."""
import os
from pathlib import Path

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "env"}

EXT_MAP = {
    ".py":    "Python",
    ".js":    "Node",
    ".jsx":   "Node",
    ".mjs":   "Node",
    ".ts":    "TypeScript",
    ".tsx":   "TypeScript",
    ".java":  "Java",
    ".kt":    "Kotlin",
    ".go":    "Go",
    ".rs":    "Rust",
    ".rb":    "Ruby",
    ".php":   "PHP",
    ".cs":    "CSharp",
    ".cpp":   "C++",
    ".cc":    "C++",
    ".cxx":   "C++",
    ".h":     "C++",
    ".swift": "Swift",
    ".dart":  "Dart",
}

FILE_MAP = {
    "package.json":       "Node",
    "requirements.txt":   "Python",
    "pyproject.toml":     "Python",
    "pom.xml":            "Java",
    "build.gradle":       "Java",
    "Cargo.toml":         "Rust",
    "go.mod":             "Go",
    "composer.json":      "PHP",
}

TEMPLATES = {
    "Python": """\
# Python
__pycache__/
*.py[cod]
.venv/
venv/
env/
.env
dist/
build/
*.egg-info/
.pytest_cache/
.mypy_cache/
""",
    "Node": """\
# Node
node_modules/
dist/
.env
.env.local
.env.*.local
npm-debug.log*
yarn-debug.log*
.next/
.nuxt/
.cache/
""",
    "TypeScript": """\
# TypeScript
node_modules/
dist/
.env
.env.local
*.js.map
.next/
.cache/
""",
    "Java": """\
# Java
target/
*.class
*.jar
*.war
.idea/
*.iml
.gradle/
build/
""",
    "Kotlin": """\
# Kotlin
target/
*.class
*.jar
.idea/
*.iml
.gradle/
build/
""",
    "Go": """\
# Go
*.exe
*.exe~
*.dll
*.so
*.dylib
vendor/
""",
    "Rust": """\
# Rust
target/
""",
    "Ruby": """\
# Ruby
.bundle/
vendor/bundle
.env
log/
tmp/
""",
    "PHP": """\
# PHP
vendor/
.env
""",
    "CSharp": """\
# CSharp
bin/
obj/
.vs/
*.user
*.suo
""",
    "C++": """\
# C++
*.o
*.obj
*.exe
*.out
build/
.cache/
""",
    "Swift": """\
# Swift
.build/
*.xcuserstate
xcuserdata/
""",
    "Dart": """\
# Dart
.dart_tool/
.packages
build/
""",
    "_generic": """\
# Generic
.DS_Store
Thumbs.db
*.log
.env
.env.*
*.swp
*~
""",
}


class GitignoreManager:
    def detect_languages(self, path):
        detected = set()
        try:
            for root, dirs, files in os.walk(path):
                dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
                for fname in files:
                    # Check known filenames first
                    if fname in FILE_MAP:
                        detected.add(FILE_MAP[fname])
                    # Check extensions
                    ext = Path(fname).suffix.lower()
                    if ext in EXT_MAP:
                        detected.add(EXT_MAP[ext])
        except OSError:
            pass
        return sorted(detected)

    def get_template(self, languages):
        parts = [TEMPLATES["_generic"]]
        for lang in languages:
            if lang in TEMPLATES:
                parts.append(TEMPLATES[lang])
        return "\n".join(parts)

    def write_gitignore(self, path, content, merge=True):
        gi_path = os.path.join(path, ".gitignore")
        if merge and os.path.exists(gi_path):
            existing = self.read_existing(path)
            existing_lines = set(existing.splitlines())
            new_lines = [
                line for line in content.splitlines()
                if line.strip() and line not in existing_lines
            ]
            if not new_lines:
                return  # Nothing new to add
            with open(gi_path, "a", encoding="utf-8") as f:
                f.write("\n# Added by Git Pusher\n")
                f.write("\n".join(new_lines) + "\n")
        else:
            with open(gi_path, "w", encoding="utf-8") as f:
                f.write(content)

    def read_existing(self, path):
        gi_path = os.path.join(path, ".gitignore")
        if os.path.exists(gi_path):
            try:
                with open(gi_path, "r", encoding="utf-8", errors="replace") as f:
                    return f.read()
            except OSError:
                return ""
        return ""
