"""Panel – Project Templates."""
import os
import threading
import shutil
import subprocess
from pathlib import Path
from tkinter import filedialog
import customtkinter as ctk
from ui.theme import *
from ui.widgets.common import Card, PrimaryButton, SecondaryButton, Label, StatusBadge, LogBox
from core.git_manager import GitManager


TEMPLATES = [
    {
        "name": "Python FastAPI",
        "desc": "REST API with FastAPI, async, OpenAPI docs",
        "tags": ["Python", "API", "Async"],
        "color": "#3B82F6",
        "icon": "Py",
        "method": "generate",
        "files": {
            "main.py": 'from fastapi import FastAPI\n\napp = FastAPI()\n\n@app.get("/")\ndef root():\n    return {"message": "Hello World"}\n',
            "requirements.txt": "fastapi>=0.104.0\nuvicorn[standard]>=0.24.0\n",
            ".gitignore": "__pycache__/\n*.py[cod]\n.venv/\nvenv/\n.env\ndist/\nbuild/\n",
            "README.md": "# FastAPI Project\n\n## Run\n\n```bash\nuvicorn main:app --reload\n```\n",
        }
    },
    {
        "name": "Python Flask",
        "desc": "Lightweight web app with Flask",
        "tags": ["Python", "Web"],
        "color": "#10B981",
        "icon": "Fl",
        "method": "generate",
        "files": {
            "app.py": "from flask import Flask\n\napp = Flask(__name__)\n\n@app.route('/')\ndef index():\n    return 'Hello, World!'\n\nif __name__ == '__main__':\n    app.run(debug=True)\n",
            "requirements.txt": "flask>=3.0.0\n",
            ".gitignore": "__pycache__/\n*.py[cod]\n.venv/\nvenv/\n.env\n",
            "README.md": "# Flask App\n\n## Run\n\n```bash\npython app.py\n```\n",
        }
    },
    {
        "name": "Node.js Express",
        "desc": "REST API with Express.js",
        "tags": ["Node", "API", "JavaScript"],
        "color": "#F59E0B",
        "icon": "JS",
        "method": "generate",
        "files": {
            "index.js": "const express = require('express');\nconst app = express();\nconst PORT = process.env.PORT || 3000;\n\napp.use(express.json());\n\napp.get('/', (req, res) => {\n  res.json({ message: 'Hello World' });\n});\n\napp.listen(PORT, () => console.log(`Server running on port ${PORT}`));\n",
            "package.json": '{\n  "name": "my-express-app",\n  "version": "1.0.0",\n  "main": "index.js",\n  "scripts": {\n    "start": "node index.js",\n    "dev": "nodemon index.js"\n  },\n  "dependencies": {\n    "express": "^4.18.2"\n  }\n}\n',
            ".gitignore": "node_modules/\n.env\n.env.local\nnpm-debug.log*\n",
            "README.md": "# Express API\n\n## Run\n\n```bash\nnpm install\nnpm start\n```\n",
        }
    },
    {
        "name": "Static HTML",
        "desc": "Simple static website with HTML, CSS, JS",
        "tags": ["HTML", "CSS", "JavaScript"],
        "color": "#EF4444",
        "icon": "HT",
        "method": "generate",
        "files": {
            "index.html": '<!DOCTYPE html>\n<html lang="en">\n<head>\n  <meta charset="UTF-8">\n  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n  <title>My Website</title>\n  <link rel="stylesheet" href="style.css">\n</head>\n<body>\n  <h1>Hello, World!</h1>\n  <script src="script.js"></script>\n</body>\n</html>\n',
            "style.css": "* {\n  margin: 0;\n  padding: 0;\n  box-sizing: border-box;\n}\n\nbody {\n  font-family: system-ui, sans-serif;\n  padding: 2rem;\n}\n",
            "script.js": "console.log('Hello from script.js');\n",
            ".gitignore": ".DS_Store\nThumbs.db\n",
            "README.md": "# Static Website\n\nOpen `index.html` in your browser.\n",
        }
    },
    {
        "name": "Go REST API",
        "desc": "Simple REST API in Go",
        "tags": ["Go", "API"],
        "color": "#06B6D4",
        "icon": "Go",
        "method": "generate",
        "files": {
            "main.go": 'package main\n\nimport (\n\t"encoding/json"\n\t"fmt"\n\t"net/http"\n)\n\nfunc main() {\n\thttp.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {\n\t\tw.Header().Set("Content-Type", "application/json")\n\t\tjson.NewEncoder(w).Encode(map[string]string{"message": "Hello World"})\n\t})\n\tfmt.Println("Server running on :8080")\n\thttp.ListenAndServe(":8080", nil)\n}\n',
            "go.mod": "module myapp\n\ngo 1.21\n",
            ".gitignore": "*.exe\n*.exe~\n*.dll\n*.so\n*.dylib\nvendor/\n",
            "README.md": "# Go REST API\n\n## Run\n\n```bash\ngo run main.go\n```\n",
        }
    },
    {
        "name": "Docker App",
        "desc": "Containerized app with Docker + Compose",
        "tags": ["Docker", "DevOps"],
        "color": "#8B5CF6",
        "icon": "Dk",
        "method": "generate",
        "files": {
            "Dockerfile": "FROM python:3.11-slim\nWORKDIR /app\nCOPY requirements.txt .\nRUN pip install -r requirements.txt\nCOPY . .\nCMD [\"python\", \"main.py\"]\n",
            "docker-compose.yml": "version: '3.8'\nservices:\n  app:\n    build: .\n    ports:\n      - '8000:8000'\n    environment:\n      - DEBUG=false\n",
            "main.py": "print('Hello from Docker!')\n",
            "requirements.txt": "",
            ".gitignore": "__pycache__/\n.env\n*.py[cod]\n",
            ".dockerignore": "__pycache__/\n.git/\n.env\n*.pyc\n",
            "README.md": "# Docker App\n\n## Run\n\n```bash\ndocker-compose up --build\n```\n",
        }
    },
    {
        "name": "CLI Python Tool",
        "desc": "Command-line tool with Click",
        "tags": ["Python", "CLI"],
        "color": "#F97316",
        "icon": "Py",
        "method": "generate",
        "files": {
            "cli.py": "import click\n\n@click.group()\ndef cli():\n    \"\"\"My CLI tool.\"\"\"\n    pass\n\n@cli.command()\n@click.argument('name')\ndef hello(name):\n    \"\"\"Say hello.\"\"\"\n    click.echo(f'Hello, {name}!')\n\nif __name__ == '__main__':\n    cli()\n",
            "requirements.txt": "click>=8.1.0\n",
            ".gitignore": "__pycache__/\n*.py[cod]\n.venv/\nvenv/\n.env\n",
            "README.md": "# CLI Tool\n\n## Usage\n\n```bash\npip install -r requirements.txt\npython cli.py hello World\n```\n",
        }
    },
    {
        "name": "Rust CLI",
        "desc": "Command-line tool in Rust",
        "tags": ["Rust", "CLI"],
        "color": "#DC2626",
        "icon": "Rs",
        "method": "cargo",
        "files": {}
    },
]


class PanelTemplates(ctk.CTkFrame):
    def __init__(self, master, app_state, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app_state = app_state
        self.git = GitManager()
        self._selected = None
        self._selected_cards = []
        self._dest_var = ctk.StringVar()
        self._name_var = ctk.StringVar(value="my-project")
        self._create_status = None
        self._log_box = None
        self._build_ui()

    def _build_ui(self):
        outer = ctk.CTkScrollableFrame(self, fg_color="transparent")
        outer.pack(fill="both", expand=True, padx=PAD, pady=PAD)

        # Title
        Label(outer, text="Project Templates", size=22, bold=True).pack(anchor="w")
        Label(outer, text="Start a new project from a curated template",
              size=13, color=TEXT_DIM).pack(anchor="w", pady=(2, PAD_SM))

        # Templates grid
        grid_card = Card(outer)
        grid_card.pack(fill="x", pady=(0, PAD_SM))
        Label(grid_card, text="Choose a Template", size=13, bold=True).pack(
            anchor="w", padx=PAD_SM, pady=(PAD_SM, PAD_SM))

        grid_scroll = ctk.CTkScrollableFrame(grid_card, fg_color="transparent", height=320)
        grid_scroll.pack(fill="x", padx=PAD_SM, pady=(0, PAD_SM))
        grid_scroll.columnconfigure(0, weight=1)
        grid_scroll.columnconfigure(1, weight=1)

        self._selected_cards = []

        for i, tmpl in enumerate(TEMPLATES):
            row = i // 2
            col = i % 2
            self._make_template_card(grid_scroll, tmpl, row, col)

        # Create form card
        form_card = Card(outer)
        form_card.pack(fill="x", pady=(0, PAD_SM))
        Label(form_card, text="Create Project", size=13, bold=True).pack(
            anchor="w", padx=PAD_SM, pady=(PAD_SM, PAD_SM))

        # Project name
        name_row = ctk.CTkFrame(form_card, fg_color="transparent")
        name_row.pack(fill="x", padx=PAD_SM, pady=(0, 6))
        Label(name_row, text="Project Name:", size=12, color=TEXT_DIM).pack(side="left", padx=(0, 6))
        ctk.CTkEntry(
            name_row, textvariable=self._name_var, width=220,
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            placeholder_text="my-project", placeholder_text_color=TEXT_MUTED,
            corner_radius=8, height=34,
            font=ctk.CTkFont(family="Inter", size=12),
        ).pack(side="left")

        # Destination folder
        dest_row = ctk.CTkFrame(form_card, fg_color="transparent")
        dest_row.pack(fill="x", padx=PAD_SM, pady=(0, 6))
        Label(dest_row, text="Destination:", size=12, color=TEXT_DIM).pack(side="left", padx=(0, 6))
        ctk.CTkEntry(
            dest_row, textvariable=self._dest_var, state="readonly", width=260,
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            placeholder_text_color=TEXT_MUTED, corner_radius=8, height=34,
            font=ctk.CTkFont(family="Inter", size=12),
        ).pack(side="left", padx=(0, 6))
        SecondaryButton(dest_row, text="Browse...", width=90, height=34,
                        command=self._browse_dest).pack(side="left")

        # Create button + status
        btn_row = ctk.CTkFrame(form_card, fg_color="transparent")
        btn_row.pack(fill="x", padx=PAD_SM, pady=(0, PAD_SM))
        PrimaryButton(btn_row, text="Create Project", width=150, height=36,
                      command=self._create_project).pack(side="left")
        self._create_status = StatusBadge(btn_row, status="pending", text="")
        self._create_status.pack(side="left", padx=(PAD_SM, 0))

        # Log box
        self._log_box = LogBox(form_card, height=100)
        self._log_box.pack(fill="x", padx=PAD_SM, pady=(0, PAD_SM))

    def _make_template_card(self, parent, tmpl, row, col):
        frame = ctk.CTkFrame(
            parent,
            fg_color=BG3,
            corner_radius=10,
            border_width=2,
            border_color=BG3,
        )
        frame.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")

        # Accent bar
        ctk.CTkFrame(frame, fg_color=tmpl["color"], height=3, corner_radius=2).pack(
            fill="x", pady=(0, 0))

        # Inner content
        inner = ctk.CTkFrame(frame, fg_color="transparent")
        inner.pack(fill="x", padx=PAD_SM, pady=(8, PAD_SM))

        # Top row: icon + name + tags
        top = ctk.CTkFrame(inner, fg_color="transparent")
        top.pack(fill="x")

        ctk.CTkLabel(
            top,
            text=tmpl["icon"],
            fg_color=tmpl["color"],
            text_color=WHITE,
            width=28, height=22,
            corner_radius=4,
            font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
        ).pack(side="left", padx=(0, 6))

        Label(top, text=tmpl["name"], size=13, bold=True).pack(side="left")

        tags_frame = ctk.CTkFrame(top, fg_color="transparent")
        tags_frame.pack(side="right")
        for tag in tmpl["tags"][:2]:
            ctk.CTkLabel(
                tags_frame,
                text=tag,
                fg_color=BG2,
                text_color=TEXT_DIM,
                corner_radius=4,
                padx=6,
                pady=2,
                font=ctk.CTkFont(family="Inter", size=9),
            ).pack(side="left", padx=2)

        # Description
        Label(inner, text=tmpl["desc"], size=11, color=TEXT_DIM).pack(anchor="w", pady=(4, 0))

        # Click handler — captures frame and tmpl
        def make_select(t, f):
            def _select():
                self._selected = t
                # Reset all card borders
                for other_frame in self._selected_cards:
                    try:
                        other_frame.configure(border_color=BG3)
                    except Exception:
                        pass
                # Highlight selected
                try:
                    f.configure(border_color=PRIMARY)
                except Exception:
                    pass
            return _select

        select_cmd = make_select(tmpl, frame)
        frame.bind("<Button-1>", lambda e, cmd=select_cmd: cmd())
        for child in frame.winfo_children():
            child.bind("<Button-1>", lambda e, cmd=select_cmd: cmd())
            for grandchild in child.winfo_children():
                try:
                    grandchild.bind("<Button-1>", lambda e, cmd=select_cmd: cmd())
                except Exception:
                    pass

        self._selected_cards.append(frame)

    def _browse_dest(self):
        path = filedialog.askdirectory(title="Select Destination Folder")
        if path:
            self._dest_var.set(path)

    def _create_project(self):
        if self._selected is None:
            self._create_status.update_status("error", "Select a template first")
            return
        dest = self._dest_var.get().strip()
        if not dest:
            self._create_status.update_status("error", "Select a destination folder")
            return
        name = self._name_var.get().strip() or "my-project"
        # Sanitize project name
        name = name.replace(" ", "-")

        self._create_status.update_status("pending", "Creating...")
        self._log_box.clear()

        tmpl = self._selected

        def worker():
            project_path = os.path.join(dest, name)
            try:
                os.makedirs(project_path, exist_ok=True)
            except Exception as e:
                self.after(0, lambda: self._create_status.update_status(
                    "error", f"Cannot create folder: {e}"))
                return

            if tmpl["method"] == "generate":
                files = tmpl.get("files", {})
                for filename, content in files.items():
                    file_path = os.path.join(project_path, filename)
                    try:
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write(content)
                        self.after(0, lambda fn=filename: self._log_box.append(f"  Created: {fn}"))
                    except Exception as e:
                        self.after(0, lambda fn=filename, ex=e: self._log_box.append(
                            f"  Error writing {fn}: {ex}"))

            elif tmpl["method"] == "cargo":
                try:
                    result = subprocess.run(
                        ["cargo", "new", project_path],
                        capture_output=True, text=True, timeout=60
                    )
                    out = result.stdout + result.stderr
                    self.after(0, lambda o=out: self._log_box.append(o))
                    if result.returncode != 0:
                        self.after(0, lambda: self._create_status.update_status(
                            "error", "cargo new failed"))
                        return
                except FileNotFoundError:
                    self.after(0, lambda: self._log_box.append("  Error: 'cargo' not found. Install Rust."))
                    self.after(0, lambda: self._create_status.update_status("error", "cargo not found"))
                    return
                except Exception as e:
                    self.after(0, lambda ex=e: self._log_box.append(f"  Error: {ex}"))
                    self.after(0, lambda: self._create_status.update_status("error", "Failed"))
                    return

            # Init git repo
            git = GitManager()
            ok, msg = git.init_repo(project_path)
            if ok:
                self.after(0, lambda: self._log_box.append("  git init OK"))
            else:
                self.after(0, lambda m=msg: self._log_box.append(f"  git init: {m}"))

            self.after(0, lambda p=project_path: self._log_box.append(
                f"\nProject created at: {p}"))
            self.after(0, lambda: self._create_status.update_status("ok", "Created!"))

            # Offer to open in file manager
            def open_in_fm():
                try:
                    subprocess.Popen(["xdg-open", project_path])
                except Exception:
                    pass

            self.after(0, lambda: self._show_open_btn(project_path))

        threading.Thread(target=worker, daemon=True).start()

    def _show_open_btn(self, project_path):
        pass  # The log already shows the path; xdg-open is optional
