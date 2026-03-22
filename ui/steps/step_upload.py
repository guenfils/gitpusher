"""Step 6 – Upload / Push."""
import threading
import customtkinter as ctk
from ui.theme import *
from ui.widgets.common import (
    Card, PrimaryButton, SecondaryButton, Label, StatusBadge,
    SectionHeader, LogBox, ProgressCard
)
from core.git_manager import GitManager


class Task:
    def __init__(self, label):
        self.label  = label
        self.status = "pending"   # pending | running | ok | error | skip
        self.detail = ""


class StepUpload(ctk.CTkFrame):
    def __init__(self, master, app_state, on_restart, on_back, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app_state  = app_state
        self.on_restart = on_restart
        self.on_back    = on_back
        self.git        = GitManager()
        self._tasks     = []
        self._task_rows = {}
        self._done      = False
        self._build()

    # ── Layout ────────────────────────────────────────────────────────────────
    def _build(self):
        Label(self, text="Uploading…", size=22, bold=True).pack(anchor="w", pady=(0, 4))
        Label(self, text="Sit back — we'll handle everything",
              size=13, color=TEXT_DIM).pack(anchor="w", pady=(0, PAD))

        # Summary card
        summary = Card(self)
        summary.pack(fill="x", pady=(0, PAD_SM))
        summary.columnconfigure((1, 3), weight=1)

        projects = self.app_state.get("projects", [])
        if len(projects) > 1:
            # Multi-project: show project count instead of single path
            ctk.CTkLabel(
                summary, text="Projects",
                font=ctk.CTkFont(family="Inter", size=11),
                text_color=TEXT_DIM,
            ).grid(row=0, column=0, padx=(PAD, 4), pady=(PAD_SM, 2), sticky="w")
            ctk.CTkLabel(
                summary,
                text=f"{len(projects)} projects",
                font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
                text_color=TEXT,
            ).grid(row=1, column=0, padx=(PAD, 4), pady=(0, PAD_SM), sticky="w")
        else:
            for col, (title, key) in enumerate([
                ("Project",  "project_path"),
                ("Repo",     "repo_name"),
                ("Branch",   "branch"),
            ]):
                ctk.CTkLabel(
                    summary, text=title,
                    font=ctk.CTkFont(family="Inter", size=11),
                    text_color=TEXT_DIM,
                ).grid(row=0, column=col * 2,
                       padx=(PAD if col == 0 else PAD_SM, 4),
                       pady=(PAD_SM, 2), sticky="w")
                val = self.app_state.get(key, "—")
                if key == "project_path":
                    from pathlib import Path
                    val = Path(val).name if val != "—" else "—"
                ctk.CTkLabel(
                    summary, text=val,
                    font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
                    text_color=TEXT,
                ).grid(row=1, column=col * 2,
                       padx=(PAD if col == 0 else PAD_SM, 4),
                       pady=(0, PAD_SM), sticky="w")
                if col < 2:
                    ctk.CTkFrame(summary, width=1, fg_color=BORDER).grid(
                        row=0, column=col * 2 + 1, rowspan=2,
                        sticky="ns", pady=PAD_SM)

        targets = []
        if self.app_state.get("push_github"):
            targets.append("GitHub")
        if self.app_state.get("push_gitlab"):
            targets.append("GitLab")
        ctk.CTkLabel(
            summary, text="Targets",
            font=ctk.CTkFont(family="Inter", size=11), text_color=TEXT_DIM,
        ).grid(row=0, column=6, padx=(PAD_SM, PAD), pady=(PAD_SM, 2), sticky="w")
        ctk.CTkLabel(
            summary, text=", ".join(targets) or "—",
            font=ctk.CTkFont(family="Inter", size=12, weight="bold"), text_color=TEXT,
        ).grid(row=1, column=6, padx=(PAD_SM, PAD), pady=(0, PAD_SM), sticky="w")

        # Progress
        self._progress = ProgressCard(self, label="Preparing…")
        self._progress.pack(fill="x", pady=(0, PAD_SM))

        # Task list
        self._task_card = Card(self)
        self._task_card.pack(fill="x", pady=(0, PAD_SM))
        Label(self._task_card, text="Steps", size=13, bold=True).pack(
            anchor="w", padx=PAD, pady=(PAD, PAD_SM))
        self._task_list = ctk.CTkFrame(self._task_card, fg_color="transparent")
        self._task_list.pack(fill="x", padx=PAD, pady=(0, PAD))

        # Log
        log_card = Card(self)
        log_card.pack(fill="x", pady=(0, PAD_SM))
        log_header = ctk.CTkFrame(log_card, fg_color="transparent")
        log_header.pack(fill="x", padx=PAD, pady=(PAD, PAD_SM))
        Label(log_header, text="Log", size=13, bold=True).pack(side="left")
        SecondaryButton(log_header, text="Clear", command=lambda: self._log.clear(),
                        width=70, height=28).pack(side="right")
        self._log = LogBox(log_card, height=160)
        self._log.pack(fill="x", padx=PAD, pady=(0, PAD))

        # Navigation
        nav = ctk.CTkFrame(self, fg_color="transparent")
        nav.pack(fill="x", pady=(PAD, 0))
        self._back_btn = SecondaryButton(nav, text="← Back", command=self.on_back, width=120)
        self._back_btn.pack(side="left")
        self._start_btn = PrimaryButton(nav, text="🚀  Upload Now",
                                        command=self._start_upload, width=200)
        self._start_btn.pack(side="right")
        self._restart_btn = PrimaryButton(nav, text="Upload Another",
                                          command=self.on_restart, width=180)
        self._restart_btn.pack_forget()

    # ── Task tracking ─────────────────────────────────────────────────────────
    def _add_task(self, label):
        task = Task(label)
        self._tasks.append(task)
        row = ctk.CTkFrame(self._task_list, fg_color="transparent")
        row.pack(fill="x", pady=2)
        badge = StatusBadge(row, status="pending", text="•  Waiting")
        badge.pack(side="left", padx=(0, 8))
        ctk.CTkLabel(
            row, text=label,
            font=ctk.CTkFont(family="Inter", size=12),
            text_color=TEXT, anchor="w",
        ).pack(side="left")
        self._task_rows[label] = (task, badge)
        return task

    def _update_task(self, label, status, detail=""):
        if label not in self._task_rows:
            return
        task, badge = self._task_rows[label]
        task.status = status
        task.detail = detail
        icons = {"running": "⟳  Running", "ok": "✓  Done",
                 "error": "✗  Failed", "skip": "—  Skipped"}
        status_map = {"running": "info", "ok": "ok", "error": "error", "skip": "pending"}
        self.after(0, lambda: badge.update_status(
            status_map.get(status, "pending"),
            icons.get(status, status)
        ))
        if detail:
            self._log_msg(f"  [{label}] {detail}")

    def _log_msg(self, msg):
        self.after(0, lambda: self._log.append(msg))

    # ── Upload logic ──────────────────────────────────────────────────────────
    def _build_task_list(self):
        self._tasks.clear()
        self._task_rows.clear()
        for w in self._task_list.winfo_children():
            w.destroy()

        projects = self.app_state.get("projects", [])
        if len(projects) > 1:
            # Multi-project: add per-project tasks
            for proj in projects:
                pname = proj.get("repo_name", "project")
                self._add_task(f"[{pname}] Stage & commit")
                if self.app_state.get("push_github"):
                    self._add_task(f"[{pname}] Push to GitHub")
                if self.app_state.get("push_gitlab"):
                    self._add_task(f"[{pname}] Push to GitLab")
            return

        # Single project task list (original logic)
        push_mode = self.app_state.get("push_mode", "init")
        is_repo   = self.app_state.get("is_git_repo", False)

        if push_mode == "init" and not is_repo:
            self._add_task("Initialize git repository")

        if push_mode == "new_branch":
            self._add_task("Create new branch")

        self._add_task("Stage all files")
        self._add_task("Create commit")

        if self.app_state.get("push_github"):
            self._add_task("Create GitHub repository")
            self._add_task("Push to GitHub")
        if self.app_state.get("push_gitlab"):
            self._add_task("Create GitLab project")
            self._add_task("Push to GitLab")

    def _start_upload(self):
        self._start_btn.configure(state="disabled", text="Uploading…")
        self._back_btn.configure(state="disabled")
        self._build_task_list()
        self._progress.start_indeterminate()
        threading.Thread(target=self._do_upload, daemon=True).start()

    def _do_upload(self):
        projects = self.app_state.get("projects", [])
        if len(projects) > 1:
            self._do_multi_upload(projects)
            return
        self._do_single_upload()

    # ── Multi-project upload ──────────────────────────────────────────────────
    def _do_multi_upload(self, projects):
        all_errors = []

        branch    = self.app_state.get("branch", "main")
        msg       = self.app_state.get("commit_msg", "Initial commit")
        private   = self.app_state.get("visibility", "private") == "private"
        push_mode = self.app_state.get("push_mode", "init")

        for proj in projects:
            path      = proj["path"]
            repo_nm   = proj["repo_name"]
            desc      = proj.get("description", "")
            pname     = repo_nm
            errors    = []

            self._log_msg(f"\n── {pname} ({path}) ──")

            is_repo = self.git.is_git_repo(path)

            # Init if needed
            if push_mode == "init" and not is_repo:
                self._update_task(f"[{pname}] Stage & commit", "running")
                ok, out = self.git.init_repo(path)
                if not ok:
                    self._update_task(f"[{pname}] Stage & commit", "error", out)
                    all_errors.append(f"{pname}: git init failed")
                    continue

            # Stage
            ok, out = self.git.add_all(path)
            if not ok:
                self._update_task(f"[{pname}] Stage & commit", "error", out)
                all_errors.append(f"{pname}: staging failed")
                continue

            # Commit
            ok, out = self.git.commit(path, msg)
            if ok:
                self._update_task(f"[{pname}] Stage & commit", "ok",
                                  out.strip().split("\n")[0])
            elif "nothing to commit" in out.lower():
                self._update_task(f"[{pname}] Stage & commit", "skip",
                                  "Nothing new to commit")
            else:
                self._update_task(f"[{pname}] Stage & commit", "error", out)
                all_errors.append(f"{pname}: commit failed")
                continue

            # Rename branch for init mode
            if push_mode == "init":
                self.git.rename_branch(path, branch)

            # GitHub
            if self.app_state.get("push_github"):
                self._update_task(f"[{pname}] Push to GitHub", "running")
                api   = self.app_state["github_api"]
                owner = self.app_state["github_user"]
                ok_ex, _ = api.repo_exists(owner, repo_nm)
                if ok_ex:
                    url = api.get_https_url(owner, repo_nm)
                else:
                    ok_c, result = api.create_repo(repo_nm, desc, private)
                    if ok_c:
                        url = result.get("clone_url", api.get_https_url(owner, repo_nm))
                    else:
                        self._update_task(f"[{pname}] Push to GitHub", "error", str(result))
                        all_errors.append(f"{pname}: GitHub repo creation failed")
                        url = None
                if url:
                    token    = self.app_state["github_token"]
                    auth_url = url.replace("https://", f"https://{owner}:{token}@")
                    self.git.add_remote(path, f"origin-github-{pname}", auth_url)
                    ok3, out3 = self.git.push(path, f"origin-github-{pname}", branch)
                    if ok3:
                        self._update_task(f"[{pname}] Push to GitHub", "ok", f"✓ {url}")
                    else:
                        self._update_task(f"[{pname}] Push to GitHub", "error", out3)
                        all_errors.append(f"{pname}: push to GitHub failed")

            # GitLab
            if self.app_state.get("push_gitlab"):
                self._update_task(f"[{pname}] Push to GitLab", "running")
                api   = self.app_state["gitlab_api"]
                owner = self.app_state["gitlab_user"]
                vis   = self.app_state.get("visibility", "private")
                ok_c, result = api.create_repo(repo_nm, desc, vis)
                if ok_c:
                    gl_url = result.get("http_url_to_repo", api.get_https_url(owner, repo_nm))
                else:
                    msg_err = str(result)
                    if "already" in msg_err.lower() or "taken" in msg_err.lower():
                        gl_url = api.get_https_url(owner, repo_nm)
                    else:
                        self._update_task(f"[{pname}] Push to GitLab", "error", msg_err)
                        all_errors.append(f"{pname}: GitLab project creation failed")
                        gl_url = None
                if gl_url:
                    token    = self.app_state["gitlab_token"]
                    auth_url = gl_url.replace("https://", f"https://{owner}:{token}@")
                    self.git.add_remote(path, f"origin-gitlab-{pname}", auth_url)
                    ok3, out3 = self.git.push(path, f"origin-gitlab-{pname}", branch)
                    if ok3:
                        self._update_task(f"[{pname}] Push to GitLab", "ok", f"✓ {gl_url}")
                    else:
                        self._update_task(f"[{pname}] Push to GitLab", "error", out3)
                        all_errors.append(f"{pname}: push to GitLab failed")

        self._finish(success=len(all_errors) == 0, errors=all_errors)

    # ── Single-project upload (original) ──────────────────────────────────────
    def _do_single_upload(self):
        path      = self.app_state["project_path"]
        branch    = self.app_state["branch"]
        msg       = self.app_state["commit_msg"]
        repo_nm   = self.app_state["repo_name"]
        desc      = self.app_state.get("description", "")
        private   = self.app_state.get("visibility", "private") == "private"
        is_repo   = self.app_state.get("is_git_repo", False)
        push_mode = self.app_state.get("push_mode", "init")

        errors = []

        # 1. Init
        if push_mode == "init" and not is_repo:
            self._update_task("Initialize git repository", "running")
            ok, out = self.git.init_repo(path)
            if ok:
                self.app_state["is_git_repo"] = True
                self._update_task("Initialize git repository", "ok", out.strip())
            else:
                self._update_task("Initialize git repository", "error", out)
                errors.append("Git init failed")
                self._finish(success=False, errors=errors)
                return

        # 1b. New branch
        if push_mode == "new_branch":
            self._update_task("Create new branch", "running")
            ok, out = self.git.create_branch(path, branch)
            if ok:
                self._update_task("Create new branch", "ok",
                                  f"Switched to new branch '{branch}'")
            else:
                self._update_task("Create new branch", "error", out)
                errors.append(f"Create branch failed: {out[:200]}")
                self._finish(success=False, errors=errors)
                return

        # 2. Apply git identity
        push_github = self.app_state.get("push_github", False)
        push_gitlab = self.app_state.get("push_gitlab", False)

        if push_github or not push_gitlab:
            git_name  = (self.app_state.get("github_git_name") or
                         self.app_state.get("git_name", ""))
            git_email = (self.app_state.get("github_git_email") or
                         self.app_state.get("git_email", ""))
        else:
            git_name  = (self.app_state.get("gitlab_git_name") or
                         self.app_state.get("git_name", ""))
            git_email = (self.app_state.get("gitlab_git_email") or
                         self.app_state.get("git_email", ""))

        if git_name:
            self.git.set_local_config(path, "user.name", git_name)
        if git_email:
            self.git.set_local_config(path, "user.email", git_email)

        # 3. Stage
        self._update_task("Stage all files", "running")
        ok, out = self.git.add_all(path)
        if ok:
            self._update_task("Stage all files", "ok")
        else:
            self._update_task("Stage all files", "error", out)
            errors.append("Staging failed")
            self._finish(success=False, errors=errors)
            return

        # 4. Commit
        self._update_task("Create commit", "running")
        ok, out = self.git.commit(path, msg)
        if ok:
            self._update_task("Create commit", "ok", out.strip().split("\n")[0])
        else:
            if "nothing to commit" in out.lower():
                self._update_task("Create commit", "skip", "Nothing new to commit")
            else:
                self._update_task("Create commit", "error", out)
                errors.append("Commit failed")
                self._finish(success=False, errors=errors)
                return

        # Rename branch for init mode
        if push_mode == "init":
            self.git.rename_branch(path, branch)

        # 5. GitHub
        if self.app_state.get("push_github"):
            self._update_task("Create GitHub repository", "running")
            api    = self.app_state["github_api"]
            owner  = self.app_state["github_user"]
            ok_ex, repo_data = api.repo_exists(owner, repo_nm)
            if ok_ex:
                self._update_task("Create GitHub repository", "skip",
                                  "Repo already exists")
                url = api.get_https_url(owner, repo_nm)
            else:
                ok, result = api.create_repo(repo_nm, desc, private)
                if ok:
                    self._update_task("Create GitHub repository", "ok",
                                      result.get("full_name", ""))
                    url = result.get("clone_url", api.get_https_url(owner, repo_nm))
                else:
                    self._update_task("Create GitHub repository", "error", str(result))
                    errors.append(f"GitHub repo creation: {result}")
                    url = None

            if url and (not errors or "GitHub" not in str(errors[-1])):
                self._update_task("Push to GitHub", "running")
                token    = self.app_state["github_token"]
                auth_url = url.replace("https://", f"https://{owner}:{token}@")
                ok2, out2 = self.git.add_remote(path, "origin-github", auth_url)
                ok3, out3 = self.git.push(path, "origin-github", branch)
                if ok3:
                    self._update_task("Push to GitHub", "ok", f"✓ {url}")
                else:
                    self._update_task("Push to GitHub", "error", out3)
                    errors.append(f"Push to GitHub failed: {out3[:200]}")

        # 6. GitLab
        if self.app_state.get("push_gitlab"):
            self._update_task("Create GitLab project", "running")
            api    = self.app_state["gitlab_api"]
            owner  = self.app_state["gitlab_user"]
            vis    = self.app_state.get("visibility", "private")
            ok, result = api.create_repo(repo_nm, desc, vis)
            if ok:
                self._update_task("Create GitLab project", "ok",
                                  result.get("path_with_namespace", ""))
                gl_url = result.get("http_url_to_repo",
                                    api.get_https_url(owner, repo_nm))
            else:
                msg_err = str(result)
                if "already" in msg_err.lower() or "taken" in msg_err.lower():
                    self._update_task("Create GitLab project", "skip",
                                      "Project already exists")
                    gl_url = api.get_https_url(owner, repo_nm)
                else:
                    self._update_task("Create GitLab project", "error", msg_err)
                    errors.append(f"GitLab project creation: {msg_err}")
                    gl_url = None

            if gl_url:
                self._update_task("Push to GitLab", "running")
                token    = self.app_state["gitlab_token"]
                auth_url = gl_url.replace("https://", f"https://{owner}:{token}@")
                ok2, out2 = self.git.add_remote(path, "origin-gitlab", auth_url)
                ok3, out3 = self.git.push(path, "origin-gitlab", branch)
                if ok3:
                    self._update_task("Push to GitLab", "ok", f"✓ {gl_url}")
                else:
                    self._update_task("Push to GitLab", "error", out3)
                    errors.append(f"Push to GitLab failed: {out3[:200]}")

        self._finish(success=len(errors) == 0, errors=errors)

    def _finish(self, success, errors):
        self.after(0, lambda: self._progress.stop_indeterminate())

        if success:
            self.after(0, lambda: self._show_success())
        else:
            self.after(0, lambda: self._show_errors(errors))

        self.after(0, lambda: self._start_btn.configure(state="disabled"))
        self.after(0, lambda: self._back_btn.configure(state="normal"))
        self.after(0, lambda: self._restart_btn.pack(side="right", padx=(PAD_SM, 0)))

    def _show_success(self):
        push_mode   = self.app_state.get("push_mode", "init")
        push_github = self.app_state.get("push_github", False)
        push_gitlab = self.app_state.get("push_gitlab", False)
        branch      = self.app_state.get("branch", "main")
        repo_nm     = self.app_state.get("repo_name", "")

        is_new_branch = push_mode == "new_branch"
        win_height = 520 if is_new_branch else 280
        win = ctk.CTkToplevel(self)
        win.title("Upload Complete")
        win.geometry(f"460x{win_height}")
        win.configure(fg_color=BG)
        win.grab_set()

        ctk.CTkLabel(win, text="🎉", font=ctk.CTkFont(size=48)).pack(pady=(20, 6))
        ctk.CTkLabel(
            win, text="Upload Successful!",
            font=ctk.CTkFont(family="Inter", size=20, weight="bold"),
            text_color=SUCCESS,
        ).pack()
        ctk.CTkLabel(
            win, text="Your project has been pushed successfully.",
            font=ctk.CTkFont(family="Inter", size=12),
            text_color=TEXT_DIM,
        ).pack(pady=(4, 8))

        if is_new_branch:
            # ── PR/MR panel ───────────────────────────────────────────────
            ctk.CTkLabel(
                win,
                text="Create a Pull Request / Merge Request",
                font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
                text_color=TEXT,
            ).pack(pady=(0, 4))

            pr_card = ctk.CTkFrame(win, fg_color=BG2, corner_radius=10)
            pr_card.pack(fill="x", padx=PAD, pady=(0, PAD_SM))

            # Title
            title_row = ctk.CTkFrame(pr_card, fg_color="transparent")
            title_row.pack(fill="x", padx=PAD_SM, pady=(PAD_SM, 4))
            ctk.CTkLabel(title_row, text="Title:",
                         font=ctk.CTkFont(family="Inter", size=11),
                         text_color=TEXT_DIM).pack(side="left", padx=(0, 6))
            pr_title_var = ctk.StringVar(value=f"Merge {branch} into main")
            ctk.CTkEntry(
                title_row, textvariable=pr_title_var,
                fg_color=BG3, border_color=BORDER, text_color=TEXT,
                font=ctk.CTkFont(family="Inter", size=12), height=34, corner_radius=6,
            ).pack(side="left", fill="x", expand=True)

            # Description
            desc_lbl_row = ctk.CTkFrame(pr_card, fg_color="transparent")
            desc_lbl_row.pack(fill="x", padx=PAD_SM, pady=(4, 2))
            ctk.CTkLabel(desc_lbl_row, text="Description:",
                         font=ctk.CTkFont(family="Inter", size=11),
                         text_color=TEXT_DIM).pack(anchor="w")
            pr_body_box = ctk.CTkTextbox(
                pr_card, height=70,
                fg_color=BG3, border_color=BORDER, text_color=TEXT,
                font=ctk.CTkFont(family="Inter", size=12), corner_radius=6,
                border_width=1,
            )
            pr_body_box.pack(fill="x", padx=PAD_SM, pady=(0, 4))

            # Base branch
            base_row = ctk.CTkFrame(pr_card, fg_color="transparent")
            base_row.pack(fill="x", padx=PAD_SM, pady=(0, PAD_SM))
            ctk.CTkLabel(base_row, text="Base branch:",
                         font=ctk.CTkFont(family="Inter", size=11),
                         text_color=TEXT_DIM).pack(side="left", padx=(0, 6))
            base_var = ctk.StringVar(value="main")
            ctk.CTkEntry(
                base_row, textvariable=base_var,
                fg_color=BG3, border_color=BORDER, text_color=TEXT,
                font=ctk.CTkFont(family="Inter", size=12), height=30, corner_radius=6,
                width=120,
            ).pack(side="left")

            # Status labels
            gh_status = ctk.CTkLabel(
                win, text="", font=ctk.CTkFont(family="Inter", size=11),
                text_color=TEXT_DIM, wraplength=420)
            gh_status.pack(pady=(2, 0))
            gl_status = ctk.CTkLabel(
                win, text="", font=ctk.CTkFont(family="Inter", size=11),
                text_color=TEXT_DIM, wraplength=420)
            gl_status.pack()

            # Buttons row
            btn_row = ctk.CTkFrame(win, fg_color="transparent")
            btn_row.pack(pady=(4, 0))

            def _create_pr_github():
                title   = pr_title_var.get().strip()
                body    = pr_body_box.get("1.0", "end").strip()
                base    = base_var.get().strip() or "main"
                api     = self.app_state.get("github_api")
                owner   = self.app_state.get("github_user", "")
                gh_btn.configure(state="disabled")
                gh_status.configure(text="Creating GitHub PR…", text_color=TEXT_DIM)
                def _run():
                    ok, res = api.create_pull_request(owner, repo_nm, title, body,
                                                      branch, base)
                    if ok:
                        url = res.get("html_url", "")
                        win.after(0, lambda: gh_status.configure(
                            text=f"✓ PR created: {url}", text_color=SUCCESS))
                    else:
                        win.after(0, lambda: gh_status.configure(
                            text=f"✗ {res}", text_color=ERROR))
                threading.Thread(target=_run, daemon=True).start()

            def _create_mr_gitlab():
                title   = pr_title_var.get().strip()
                body    = pr_body_box.get("1.0", "end").strip()
                base    = base_var.get().strip() or "main"
                api     = self.app_state.get("gitlab_api")
                owner   = self.app_state.get("gitlab_user", "")
                gl_btn.configure(state="disabled")
                gl_status.configure(text="Creating GitLab MR…", text_color=TEXT_DIM)
                def _run():
                    ok, res = api.create_merge_request(owner, repo_nm, title, body,
                                                       branch, base)
                    if ok:
                        url = res.get("web_url", "")
                        win.after(0, lambda: gl_status.configure(
                            text=f"✓ MR created: {url}", text_color=SUCCESS))
                    else:
                        win.after(0, lambda: gl_status.configure(
                            text=f"✗ {res}", text_color=ERROR))
                threading.Thread(target=_run, daemon=True).start()

            if push_github and self.app_state.get("github_api"):
                gh_btn = PrimaryButton(
                    btn_row, text="Create GitHub PR",
                    command=_create_pr_github, width=170, height=36)
                gh_btn.pack(side="left", padx=(0, PAD_SM))

            if push_gitlab and self.app_state.get("gitlab_api"):
                gl_btn = PrimaryButton(
                    btn_row, text="Create GitLab MR",
                    command=_create_mr_gitlab, width=170, height=36)
                gl_btn.pack(side="left")

        else:
            ctk.CTkFrame(win, fg_color="transparent", height=8).pack()

        PrimaryButton(win, text="Close", command=win.destroy, width=140).pack(pady=(8, 16))

    def _show_errors(self, errors):
        self._log_msg("\n⚠ Errors encountered:")
        for e in errors:
            self._log_msg(f"  • {e}")
