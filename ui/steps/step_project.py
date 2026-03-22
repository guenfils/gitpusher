"""Step 3 – Select local project folder(s)."""
import os
import threading
from pathlib import Path
import customtkinter as ctk
from tkinter import filedialog
from ui.theme import *
from ui.widgets.common import (
    Card, PrimaryButton, SecondaryButton, Label, StatusBadge, SectionHeader
)
from core.git_manager import GitManager
from core.gitignore_manager import GitignoreManager
from core.secret_scanner import SecretScanner


class StepProject(ctk.CTkFrame):
    def __init__(self, master, app_state, on_next, on_back, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app_state = app_state
        self.on_next   = on_next
        self.on_back   = on_back
        self.git       = GitManager()
        # Multi-project list: [{"path": str, "repo_name": str, "description": str}]
        self._projects = []
        self._project_rows = []  # list of dicts with widget refs per project
        self._build()

    # ── Main layout ───────────────────────────────────────────────────────────
    def _build(self):
        Label(self, text="Select Project", size=22, bold=True).pack(anchor="w", pady=(0, 4))
        Label(self, text="Choose the local folder(s) you want to upload",
              size=13, color=TEXT_DIM).pack(anchor="w", pady=(0, PAD))

        # ── Multi-project browse card ─────────────────────────────────────
        browse_card = Card(self)
        browse_card.pack(fill="x", pady=(0, PAD_SM))

        hdr = ctk.CTkFrame(browse_card, fg_color="transparent")
        hdr.pack(fill="x", padx=PAD, pady=(PAD, PAD_SM))
        ctk.CTkLabel(
            hdr, text="📁",
            font=ctk.CTkFont(size=28), text_color=TEXT_DIM,
        ).pack(side="left", padx=(0, 8))
        Label(hdr, text="Project Folders", size=14, bold=True).pack(side="left")
        PrimaryButton(hdr, text="+ Add Project", command=self._add_project,
                      width=130, height=36).pack(side="right")

        Label(browse_card, text="Add one or multiple project folders to push",
              size=12, color=TEXT_DIM).pack(anchor="w", padx=PAD, pady=(0, PAD_SM))

        # Project list container
        self._proj_list_frame = ctk.CTkFrame(browse_card, fg_color="transparent")
        self._proj_list_frame.pack(fill="x", padx=PAD, pady=(0, PAD))

        # Summary label (file count / size)
        self._summary_lbl = Label(browse_card, text="", size=12, color=TEXT_DIM)
        self._summary_lbl.pack(anchor="w", padx=PAD, pady=(0, PAD_SM))

        # ── Single-project compat: path + git status card ─────────────────
        self._path_card = Card(self)
        path_inner = ctk.CTkFrame(self._path_card, fg_color="transparent")
        path_inner.pack(fill="x", padx=PAD, pady=PAD_SM)
        path_inner.columnconfigure(1, weight=1)

        Label(path_inner, text="Path:", size=12, bold=True,
              color=TEXT_DIM).grid(row=0, column=0, sticky="w", padx=(0, 8))
        self._path_var = ctk.StringVar(value="—")
        ctk.CTkLabel(
            path_inner, textvariable=self._path_var,
            font=ctk.CTkFont(family="JetBrains Mono", size=11),
            text_color=TEXT, anchor="w", wraplength=500,
        ).grid(row=0, column=1, sticky="w")

        status_row = ctk.CTkFrame(self._path_card, fg_color="transparent")
        status_row.pack(fill="x", padx=PAD, pady=(0, PAD_SM))
        Label(status_row, text="Git status:", size=12, bold=True,
              color=TEXT_DIM).pack(side="left", padx=(0, 8))
        self._git_badge = StatusBadge(status_row, status="pending", text="—")
        self._git_badge.pack(side="left")

        self._files_lbl = Label(self._path_card, text="", size=12, color=TEXT_DIM)
        self._files_lbl.pack(anchor="w", padx=PAD, pady=(0, PAD))
        self._path_card.pack_forget()

        # ── Repo name card ────────────────────────────────────────────────
        name_card = Card(self)
        name_card.pack(fill="x", pady=(0, PAD_SM))
        SectionHeader(name_card, "R", "Repository Name",
                      "This will be the name on GitHub/GitLab").pack(
            fill="x", padx=PAD, pady=(PAD, PAD_SM))
        self._repo_name_var = ctk.StringVar()
        ctk.CTkEntry(
            name_card, textvariable=self._repo_name_var,
            placeholder_text="my-awesome-project",
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            font=ctk.CTkFont(family="Inter", size=13), height=42, corner_radius=8,
        ).pack(fill="x", padx=PAD, pady=(0, PAD))

        # ── Description card ──────────────────────────────────────────────
        desc_card = Card(self)
        desc_card.pack(fill="x", pady=(0, PAD_SM))
        Label(desc_card, text="Description (optional)", size=13, bold=True).pack(
            anchor="w", padx=PAD, pady=(PAD, PAD_SM))
        self._desc_var = ctk.StringVar()
        ctk.CTkEntry(
            desc_card, textvariable=self._desc_var,
            placeholder_text="A short description of your project",
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            font=ctk.CTkFont(family="Inter", size=12), height=42, corner_radius=8,
        ).pack(fill="x", padx=PAD, pady=(0, PAD))

        # ── Visibility card ───────────────────────────────────────────────
        vis_card = Card(self)
        vis_card.pack(fill="x", pady=(0, PAD_SM))
        Label(vis_card, text="Visibility", size=13, bold=True).pack(
            anchor="w", padx=PAD, pady=(PAD, PAD_SM))
        vis_row = ctk.CTkFrame(vis_card, fg_color="transparent")
        vis_row.pack(fill="x", padx=PAD, pady=(0, PAD))
        self._visibility_var = ctk.StringVar(value="private")
        for val, lbl, desc in [
            ("private", "Private", "Only you can see this"),
            ("public",  "Public",  "Anyone can see this"),
        ]:
            col = ctk.CTkFrame(vis_row, fg_color="transparent")
            col.pack(side="left", padx=(0, PAD))
            ctk.CTkRadioButton(
                col, text=lbl,
                variable=self._visibility_var, value=val,
                font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
                text_color=TEXT, fg_color=PRIMARY,
            ).pack(anchor="w")
            Label(col, text=desc, size=11, color=TEXT_DIM).pack(anchor="w")

        # ── Security Scan card (shown after folder selected) ──────────────
        self._scan_card = Card(self)
        scan_hdr = ctk.CTkFrame(self._scan_card, fg_color="transparent")
        scan_hdr.pack(fill="x", padx=PAD, pady=(PAD, PAD_SM))
        ctk.CTkLabel(scan_hdr, text="🔒",
                     font=ctk.CTkFont(size=16), text_color=TEXT_DIM).pack(side="left", padx=(0, 6))
        Label(scan_hdr, text="Security Scan", size=13, bold=True).pack(side="left")

        self._scan_status = Label(self._scan_card, text="Scanning…",
                                  size=12, color=TEXT_DIM)
        self._scan_status.pack(anchor="w", padx=PAD, pady=(0, PAD_SM))

        self._scan_findings_frame = ctk.CTkFrame(self._scan_card, fg_color="transparent")
        self._scan_findings_frame.pack(fill="x", padx=PAD, pady=(0, PAD_SM))

        self._scan_add_btn_frame = ctk.CTkFrame(self._scan_card, fg_color="transparent")
        self._scan_add_btn_frame.pack(fill="x", padx=PAD, pady=(0, PAD))
        self._scan_card.pack_forget()

        # ── .gitignore card (shown after folder selected) ─────────────────
        self._gi_card = Card(self)
        gi_hdr = ctk.CTkFrame(self._gi_card, fg_color="transparent")
        gi_hdr.pack(fill="x", padx=PAD, pady=(PAD, PAD_SM))
        ctk.CTkLabel(gi_hdr, text="📝",
                     font=ctk.CTkFont(size=16), text_color=TEXT_DIM).pack(side="left", padx=(0, 6))
        Label(gi_hdr, text=".gitignore Generator", size=13, bold=True).pack(side="left")

        self._gi_lang_frame = ctk.CTkFrame(self._gi_card, fg_color="transparent")
        self._gi_lang_frame.pack(fill="x", padx=PAD, pady=(0, PAD_SM))

        self._gi_check_frame = ctk.CTkFrame(self._gi_card, fg_color="transparent")
        self._gi_check_frame.pack(fill="x", padx=PAD, pady=(0, PAD_SM))

        self._gi_btn_frame = ctk.CTkFrame(self._gi_card, fg_color="transparent")
        self._gi_btn_frame.pack(fill="x", padx=PAD, pady=(0, PAD))
        self._gi_card.pack_forget()

        self._gi_lang_vars = {}   # lang -> BooleanVar
        self._gi_detected  = []   # list of detected lang names

        # ── Navigation ────────────────────────────────────────────────────
        nav = ctk.CTkFrame(self, fg_color="transparent")
        nav.pack(fill="x", pady=(PAD, 0))
        SecondaryButton(nav, text="← Back", command=self.on_back, width=120).pack(side="left")
        self._next_btn = PrimaryButton(nav, text="Continue  →", command=self._next,
                                       state="disabled", width=180)
        self._next_btn.pack(side="right")

    # ── Add project ───────────────────────────────────────────────────────────
    def _add_project(self):
        path = filedialog.askdirectory(title="Select Project Folder")
        if not path:
            return
        # Check for duplicate
        for p in self._projects:
            if p["path"] == path:
                return
        folder_name = Path(path).name
        safe_name = folder_name.lower().replace(" ", "-").replace("_", "-")
        proj = {"path": path, "repo_name": safe_name, "description": ""}
        self._projects.append(proj)
        self._add_project_row(proj)
        self._on_projects_changed()

    def _add_project_row(self, proj):
        row_frame = ctk.CTkFrame(
            self._proj_list_frame,
            fg_color=BG3, corner_radius=8,
        )
        row_frame.pack(fill="x", pady=(0, PAD_SM))

        # Folder icon + name
        info_col = ctk.CTkFrame(row_frame, fg_color="transparent")
        info_col.pack(side="left", fill="x", expand=True, padx=PAD_SM, pady=PAD_SM)

        Label(info_col, text=Path(proj["path"]).name, size=13, bold=True).pack(anchor="w")
        Label(info_col, text=proj["path"], size=10, color=TEXT_MUTED).pack(anchor="w")

        # Repo name entry
        repo_var = ctk.StringVar(value=proj["repo_name"])
        def _on_repo_change(var=repo_var, p=proj):
            p["repo_name"] = var.get()
        repo_var.trace_add("write", lambda *a, v=repo_var, p=proj: _on_repo_change(v, p))

        name_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
        name_frame.pack(side="left", padx=(0, PAD_SM), pady=PAD_SM)
        Label(name_frame, text="Repo:", size=11, color=TEXT_DIM).pack(anchor="w")
        ctk.CTkEntry(
            name_frame, textvariable=repo_var,
            fg_color=BG, border_color=BORDER, text_color=TEXT,
            font=ctk.CTkFont(family="Inter", size=11), height=32, corner_radius=6, width=160,
        ).pack()

        # Remove button
        def _remove(p=proj, rf=row_frame):
            self._projects.remove(p)
            self._project_rows = [r for r in self._project_rows if r["proj"] is not p]
            rf.destroy()
            self._on_projects_changed()

        SecondaryButton(row_frame, text="✕", command=_remove, width=36, height=36).pack(
            side="right", padx=PAD_SM, pady=PAD_SM)

        row_info = {"proj": proj, "frame": row_frame, "repo_var": repo_var}
        self._project_rows.append(row_info)

    def _on_projects_changed(self):
        if not self._projects:
            self._path_card.pack_forget()
            self._scan_card.pack_forget()
            self._gi_card.pack_forget()
            self._next_btn.configure(state="disabled")
            self._summary_lbl.configure(text="")
            return

        # Use first project as primary for single-project compat
        first = self._projects[0]
        self._set_path(first["path"], first["repo_name"])

        # Count files across all projects
        paths = [p["path"] for p in self._projects]
        threading.Thread(
            target=self._count_all_files, args=(paths,), daemon=True
        ).start()

        # Show security scan + gitignore for first project
        self._run_security_scan(first["path"])
        self._run_gitignore_detect(first["path"])

    def _set_path(self, path, repo_name=None):
        self.app_state["project_path"] = path
        self._path_var.set(path)
        self._path_card.pack(fill="x", pady=(0, PAD_SM))

        if repo_name:
            self._repo_name_var.set(repo_name)
        else:
            folder_name = Path(path).name
            safe_name = folder_name.lower().replace(" ", "-").replace("_", "-")
            self._repo_name_var.set(safe_name)

        # Git check
        if self.git.is_git_repo(path):
            branch = self.git.get_current_branch(path)
            self._git_badge.update_status(
                "ok", f"✓ Git repo  ({branch or 'unknown branch'})")
            self.app_state["is_git_repo"] = True
            self.app_state["current_branch"] = branch
        else:
            self._git_badge.update_status("warning", "⚠ Not a git repo (will init)")
            self.app_state["is_git_repo"] = False

        self._next_btn.configure(state="normal")

    # ── File counting ─────────────────────────────────────────────────────────
    def _count_all_files(self, paths):
        total_count = 0
        total_size = 0
        for path in paths:
            for root, dirs, files in os.walk(path):
                dirs[:] = [d for d in dirs
                           if d not in (".git", "node_modules", "__pycache__", ".venv")]
                for f in files:
                    try:
                        fp = os.path.join(root, f)
                        total_size += os.path.getsize(fp)
                        total_count += 1
                    except OSError:
                        pass
        size_str = self._human_size(total_size)
        n_proj = len(paths)
        proj_label = f"{n_proj} project{'s' if n_proj > 1 else ''}"
        self.after(0, lambda: self._summary_lbl.configure(
            text=f"{proj_label}  ·  {total_count:,} files  ·  {size_str}"))
        self.after(0, lambda: self._files_lbl.configure(
            text=f"{total_count:,} files  ·  {size_str}"))

    @staticmethod
    def _human_size(n):
        for unit in ("B", "KB", "MB", "GB"):
            if n < 1024:
                return f"{n:.1f} {unit}"
            n /= 1024
        return f"{n:.1f} TB"

    # ── Security Scan ─────────────────────────────────────────────────────────
    def _run_security_scan(self, path):
        # Clear old findings
        for w in self._scan_findings_frame.winfo_children():
            w.destroy()
        for w in self._scan_add_btn_frame.winfo_children():
            w.destroy()
        self._scan_status.configure(text="Scanning for sensitive files…", text_color=TEXT_DIM)
        self._scan_card.pack(fill="x", pady=(0, PAD_SM))
        threading.Thread(
            target=self._do_security_scan, args=(path,), daemon=True
        ).start()

    def _do_security_scan(self, path):
        findings = SecretScanner().scan(path)
        self.after(0, lambda: self._show_scan_results(path, findings))

    def _show_scan_results(self, path, findings):
        # Clear widgets
        for w in self._scan_findings_frame.winfo_children():
            w.destroy()
        for w in self._scan_add_btn_frame.winfo_children():
            w.destroy()

        if not findings:
            self._scan_status.configure(
                text="✓ No sensitive files detected", text_color=SUCCESS)
            return

        self._scan_status.configure(
            text=f"⚠ {len(findings)} sensitive file(s) found:", text_color=WARNING)

        for item in findings:
            sev = item["severity"]
            badge_status = "error" if sev == "high" else "warning"
            row = ctk.CTkFrame(self._scan_findings_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)
            StatusBadge(row, status=badge_status,
                        text=sev.upper()).pack(side="left", padx=(0, 8))
            ctk.CTkLabel(
                row,
                text=item["file"],
                font=ctk.CTkFont(family="JetBrains Mono", size=11),
                text_color=TEXT, anchor="w",
            ).pack(side="left", padx=(0, 8))
            Label(row, text=item["reason"], size=11, color=TEXT_DIM).pack(side="left")

        # "Add to .gitignore" button
        def _add_findings():
            filenames = [f["file"] for f in findings]
            SecretScanner().add_to_gitignore(path, filenames)
            confirm_lbl.configure(text="✓ Added to .gitignore", text_color=SUCCESS)
            add_btn.configure(state="disabled")

        btn_row = ctk.CTkFrame(self._scan_add_btn_frame, fg_color="transparent")
        btn_row.pack(fill="x")
        add_btn = SecondaryButton(
            btn_row, text="Add to .gitignore", command=_add_findings,
            width=160, height=34
        )
        add_btn.pack(side="left")
        confirm_lbl = Label(btn_row, text="", size=12, color=SUCCESS)
        confirm_lbl.pack(side="left", padx=(PAD_SM, 0))

    # ── .gitignore Generator ──────────────────────────────────────────────────
    def _run_gitignore_detect(self, path):
        for w in self._gi_lang_frame.winfo_children():
            w.destroy()
        for w in self._gi_check_frame.winfo_children():
            w.destroy()
        for w in self._gi_btn_frame.winfo_children():
            w.destroy()
        self._gi_lang_vars = {}
        self._gi_detected = []
        Label(self._gi_lang_frame, text="Detecting languages…",
              size=12, color=TEXT_DIM).pack(anchor="w")
        self._gi_card.pack(fill="x", pady=(0, PAD_SM))
        threading.Thread(
            target=self._do_gitignore_detect, args=(path,), daemon=True
        ).start()

    def _do_gitignore_detect(self, path):
        langs = GitignoreManager().detect_languages(path)
        gi_exists = os.path.exists(os.path.join(path, ".gitignore"))
        self.after(0, lambda: self._show_gitignore_ui(path, langs, gi_exists))

    def _show_gitignore_ui(self, path, langs, gi_exists):
        for w in self._gi_lang_frame.winfo_children():
            w.destroy()
        for w in self._gi_check_frame.winfo_children():
            w.destroy()
        for w in self._gi_btn_frame.winfo_children():
            w.destroy()

        self._gi_detected = langs
        self._gi_lang_vars = {}

        # Language pills row
        if langs:
            Label(self._gi_lang_frame, text="Detected:", size=11,
                  color=TEXT_DIM).pack(side="left", padx=(0, 6))
            for lang in langs:
                ctk.CTkLabel(
                    self._gi_lang_frame,
                    text=lang,
                    fg_color=PRIMARY,
                    text_color=WHITE,
                    corner_radius=10,
                    padx=10, pady=3,
                    font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
                ).pack(side="left", padx=(0, 4))
        else:
            Label(self._gi_lang_frame, text="No languages detected — generic template will be used",
                  size=12, color=TEXT_DIM).pack(anchor="w")

        # Checkboxes for each detected language
        if langs:
            Label(self._gi_check_frame, text="Include templates:",
                  size=11, color=TEXT_DIM).pack(anchor="w", pady=(0, 4))
            checks_row = ctk.CTkFrame(self._gi_check_frame, fg_color="transparent")
            checks_row.pack(fill="x")
            for lang in langs:
                var = ctk.BooleanVar(value=True)
                self._gi_lang_vars[lang] = var
                ctk.CTkCheckBox(
                    checks_row,
                    text=lang, variable=var,
                    font=ctk.CTkFont(family="Inter", size=12),
                    text_color=TEXT, fg_color=PRIMARY, hover_color=PRIMARY_H,
                ).pack(side="left", padx=(0, PAD_SM))

        # Generate button
        btn_label = "Update .gitignore" if gi_exists else "Generate .gitignore"

        def _generate():
            selected = [l for l, v in self._gi_lang_vars.items() if v.get()]
            content = GitignoreManager().get_template(selected)
            GitignoreManager().write_gitignore(path, content, merge=True)
            self.app_state["gitignore_generated"] = True
            gi_confirm.configure(text="✓ .gitignore updated", text_color=SUCCESS)
            gi_gen_btn.configure(state="disabled")

        gi_gen_btn = PrimaryButton(
            self._gi_btn_frame, text=btn_label, command=_generate,
            width=180, height=36
        )
        gi_gen_btn.pack(side="left")
        gi_confirm = Label(self._gi_btn_frame, text="", size=12, color=SUCCESS)
        gi_confirm.pack(side="left", padx=(PAD_SM, 0))

    # ── Next ──────────────────────────────────────────────────────────────────
    def _next(self):
        repo_name = self._repo_name_var.get().strip()
        if not repo_name:
            return

        # Build projects list — multi-project support
        if len(self._projects) > 1:
            # Update repo names from row vars
            for row_info in self._project_rows:
                row_info["proj"]["repo_name"] = row_info["repo_var"].get().strip()
            # Set first project as primary for compat
            first = self._projects[0]
            self.app_state["project_path"] = first["path"]
            self.app_state["repo_name"]    = first["repo_name"]
            self.app_state["description"]  = self._desc_var.get().strip()
            self.app_state["visibility"]   = self._visibility_var.get()
            self.app_state["projects"]     = list(self._projects)
        else:
            self.app_state["project_path"] = self.app_state.get("project_path", "")
            self.app_state["repo_name"]    = repo_name
            self.app_state["description"]  = self._desc_var.get().strip()
            self.app_state["visibility"]   = self._visibility_var.get()
            # Clear multi-project list if only 1
            self.app_state.pop("projects", None)

        if "gitignore_generated" not in self.app_state:
            self.app_state["gitignore_generated"] = False

        self.on_next()
