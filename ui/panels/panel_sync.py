"""Panel – Sync Repository."""
import threading
from tkinter import filedialog
import customtkinter as ctk
from ui.theme import *
from ui.widgets.common import Card, PrimaryButton, SecondaryButton, Label, StatusBadge, LogBox
from core.git_manager import GitManager


class PanelSync(ctk.CTkFrame):
    def __init__(self, master, app_state, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app_state = app_state
        self._git = GitManager()
        self._repo_path = None
        self._current_branch = None

        self._build_ui()

    def _build_ui(self):
        # Title
        Label(self, text="Sync Repository", size=18, bold=True).pack(anchor="w", pady=(0, 4))
        Label(self, text="Pull remote changes then push your local commits", size=12, color=TEXT_DIM).pack(anchor="w", pady=(0, PAD))

        # Card: Local repository
        repo_card = Card(self)
        repo_card.pack(fill="x", pady=(0, PAD_SM))

        Label(repo_card, text="Local Repository", size=13, bold=True).pack(anchor="w", padx=PAD, pady=(PAD_SM, 8))

        picker_row = ctk.CTkFrame(repo_card, fg_color="transparent")
        picker_row.pack(fill="x", padx=PAD, pady=(0, 8))

        self._path_var = ctk.StringVar()
        ctk.CTkEntry(
            picker_row, textvariable=self._path_var,
            placeholder_text="/path/to/your/repo",
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            placeholder_text_color=TEXT_MUTED, corner_radius=8, height=38,
            font=ctk.CTkFont(family="Inter", size=12),
        ).pack(side="left", fill="x", expand=True, padx=(0, 8))

        SecondaryButton(picker_row, text="Browse", width=90, height=38, command=self._browse_repo).pack(side="left", padx=(0, 8))
        SecondaryButton(picker_row, text="Load", width=80, height=38, command=self._load_repo).pack(side="left")

        # Repo info area
        self._info_frame = ctk.CTkFrame(repo_card, fg_color="transparent")
        self._info_frame.pack(fill="x", padx=PAD, pady=(0, PAD_SM))

        self._branch_badge_var = ctk.StringVar(value="")
        self._remote_var = ctk.StringVar(value="")
        self._commit_var = ctk.StringVar(value="")

        info_row = ctk.CTkFrame(self._info_frame, fg_color="transparent")
        info_row.pack(fill="x")

        Label(info_row, text="Branch:", size=11, color=TEXT_DIM).pack(side="left")
        self._branch_lbl = Label(info_row, textvariable=self._branch_badge_var, size=11, color=SUCCESS)
        self._branch_lbl.pack(side="left", padx=(4, PAD_SM))

        self._remote_lbl_var = ctk.StringVar(value="")
        Label(info_row, text="Remote:", size=11, color=TEXT_DIM).pack(side="left")
        Label(info_row, textvariable=self._remote_lbl_var, size=11, color=TEXT_DIM).pack(side="left", padx=4)

        self._commit_lbl_var = ctk.StringVar(value="")
        Label(self._info_frame, textvariable=self._commit_lbl_var, size=11, color=TEXT_DIM).pack(anchor="w", pady=(4, 0))

        # Card: Pull options
        pull_card = Card(self)
        pull_card.pack(fill="x", pady=(0, PAD_SM))

        Label(pull_card, text="Pull Options", size=13, bold=True).pack(anchor="w", padx=PAD, pady=(PAD_SM, 8))

        pull_fields = ctk.CTkFrame(pull_card, fg_color="transparent")
        pull_fields.pack(fill="x", padx=PAD, pady=(0, 8))
        pull_fields.columnconfigure(0, weight=1)
        pull_fields.columnconfigure(1, weight=1)

        Label(pull_fields, text="Remote", size=11, color=TEXT_DIM).grid(row=0, column=0, sticky="w", pady=(0, 4))
        Label(pull_fields, text="Branch (optional)", size=11, color=TEXT_DIM).grid(row=0, column=1, sticky="w", pady=(0, 4), padx=(PAD_SM, 0))

        self._pull_remote_var = ctk.StringVar(value="origin")
        ctk.CTkEntry(
            pull_fields, textvariable=self._pull_remote_var,
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            corner_radius=8, height=36,
            font=ctk.CTkFont(family="Inter", size=12),
        ).grid(row=1, column=0, sticky="ew", padx=(0, PAD_SM))

        self._pull_branch_var = ctk.StringVar()
        ctk.CTkEntry(
            pull_fields, textvariable=self._pull_branch_var,
            placeholder_text="Default branch",
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            placeholder_text_color=TEXT_MUTED,
            corner_radius=8, height=36,
            font=ctk.CTkFont(family="Inter", size=12),
        ).grid(row=1, column=1, sticky="ew")

        ctk.CTkLabel(
            pull_card,
            text="  Stash or commit local changes before pulling",
            text_color=WARNING,
            font=ctk.CTkFont(family="Inter", size=11),
            anchor="w",
        ).pack(fill="x", padx=PAD, pady=(0, PAD_SM))

        # Card: Push options
        push_card = Card(self)
        push_card.pack(fill="x", pady=(0, PAD_SM))

        Label(push_card, text="Push Options", size=13, bold=True).pack(anchor="w", padx=PAD, pady=(PAD_SM, 8))

        Label(push_card, text="Commit message (if uncommitted changes)", size=11, color=TEXT_DIM).pack(anchor="w", padx=PAD)
        self._commit_msg_var = ctk.StringVar(value="Update")
        ctk.CTkEntry(
            push_card, textvariable=self._commit_msg_var,
            placeholder_text="Your commit message",
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            placeholder_text_color=TEXT_MUTED, corner_radius=8, height=38,
            font=ctk.CTkFont(family="Inter", size=12),
        ).pack(fill="x", padx=PAD, pady=(4, 8))

        plat_row = ctk.CTkFrame(push_card, fg_color="transparent")
        plat_row.pack(fill="x", padx=PAD, pady=(0, PAD_SM))
        Label(plat_row, text="Push to:", size=11, color=TEXT_DIM).pack(side="left", padx=(0, PAD_SM))

        self._push_github = ctk.BooleanVar(value=bool(self.app_state.get("github_api")))
        self._push_gitlab = ctk.BooleanVar(value=bool(self.app_state.get("gitlab_api")))

        if self.app_state.get("github_api"):
            ctk.CTkCheckBox(
                plat_row, text="GitHub", variable=self._push_github,
                fg_color=PRIMARY, hover_color=PRIMARY_H,
                text_color=TEXT, font=ctk.CTkFont(family="Inter", size=12),
            ).pack(side="left", padx=(0, PAD_SM))

        if self.app_state.get("gitlab_api"):
            ctk.CTkCheckBox(
                plat_row, text="GitLab", variable=self._push_gitlab,
                fg_color=PRIMARY, hover_color=PRIMARY_H,
                text_color=TEXT, font=ctk.CTkFont(family="Inter", size=12),
            ).pack(side="left")

        # Card: Actions
        actions_card = Card(self)
        actions_card.pack(fill="x", pady=(0, PAD_SM))

        Label(actions_card, text="Actions", size=13, bold=True).pack(anchor="w", padx=PAD, pady=(PAD_SM, 8))

        btn_row = ctk.CTkFrame(actions_card, fg_color="transparent")
        btn_row.pack(fill="x", padx=PAD, pady=(0, PAD_SM))
        btn_row.columnconfigure(0, weight=1)
        btn_row.columnconfigure(1, weight=1)
        btn_row.columnconfigure(2, weight=1)

        SecondaryButton(btn_row, text="Pull Only", command=self._do_pull).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        SecondaryButton(btn_row, text="Push Only", command=self._do_push).grid(row=0, column=1, sticky="ew", padx=3)
        PrimaryButton(btn_row, text="Sync (Pull + Push)", command=self._do_sync).grid(row=0, column=2, sticky="ew", padx=(6, 0))

        # LogBox
        self._log = LogBox(self, height=150)
        self._log.pack(fill="x", pady=(0, PAD_SM))

        # Status badge
        self._badge = StatusBadge(self, status="pending", text="")
        self._badge.pack(anchor="w")

    def _browse_repo(self):
        folder = filedialog.askdirectory(title="Select local repository")
        if folder:
            self._path_var.set(folder)

    def _load_repo(self):
        path = self._path_var.get().strip()
        if not path:
            self._badge.update_status("error", "Please select a repository folder")
            return

        if not self._git.is_git_repo(path):
            self._badge.update_status("error", "Not a git repository")
            return

        self._repo_path = path
        branch = self._git.get_current_branch(path)
        self._current_branch = branch
        self._branch_badge_var.set(branch or "unknown")
        if branch:
            self._pull_branch_var.set(branch)

        remote_url = self._git.get_remote_url(path)
        self._remote_lbl_var.set(remote_url[:60] + "..." if len(remote_url) > 60 else remote_url)

        commit = self._git.get_last_commit(path)
        if commit:
            self._commit_lbl_var.set(
                f"Last commit: [{commit['hash']}] {commit['message']} — {commit['author']} {commit['when']}"
            )
        else:
            self._commit_lbl_var.set("No commits yet")

        self._badge.update_status("ok", f"Loaded: {path}")

    def _check_repo(self):
        if not self._repo_path:
            self._badge.update_status("error", "Load a repository first")
            return False
        return True

    def _do_pull(self):
        if not self._check_repo():
            return
        remote = self._pull_remote_var.get().strip() or "origin"
        branch = self._pull_branch_var.get().strip() or None

        self._log.clear()
        self._log.append(f"Pulling from {remote}...")
        self._badge.update_status("pending", "Pulling...")

        def _run():
            ok, output = self._git.pull(self._repo_path, remote=remote, branch=branch)
            def _update():
                self._log.append(output if output.strip() else "(no output)")
                if ok:
                    self._badge.update_status("ok", "Pull successful")
                else:
                    self._badge.update_status("error", "Pull failed")
            self.after(0, _update)

        threading.Thread(target=_run, daemon=True).start()

    def _do_push(self):
        if not self._check_repo():
            return

        self._log.clear()
        self._log.append("Preparing push...")
        self._badge.update_status("pending", "Pushing...")

        def _run():
            path = self._repo_path
            branch = self._current_branch or "main"

            # Commit uncommitted changes if any
            status = self._git.get_status(path)
            if status:
                msg = self._commit_msg_var.get().strip() or "Update"
                self.after(0, lambda: self._log.append(f"Staging and committing: {msg}"))
                self._git.add_all(path)
                ok_c, out_c = self._git.commit(path, msg)
                self.after(0, lambda: self._log.append(out_c if out_c.strip() else "(committed)"))

            any_ok = False
            errors = []

            if self._push_github.get() and self.app_state.get("github_api"):
                token = self.app_state.get("github_token", "")
                env = {"GIT_ASKPASS": "echo", "GIT_USERNAME": "x-token", "GIT_PASSWORD": token} if token else None
                ok, out = self._git.push(path, "origin", branch, env=env)
                self.after(0, lambda o=out: self._log.append(f"GitHub: {o}"))
                if ok:
                    any_ok = True
                else:
                    errors.append("GitHub push failed")

            if self._push_gitlab.get() and self.app_state.get("gitlab_api"):
                token = self.app_state.get("gitlab_token", "")
                env = {"GIT_ASKPASS": "echo", "GIT_USERNAME": "oauth2", "GIT_PASSWORD": token} if token else None
                ok, out = self._git.push(path, "gitlab", branch, env=env)
                self.after(0, lambda o=out: self._log.append(f"GitLab: {o}"))
                if ok:
                    any_ok = True
                else:
                    errors.append("GitLab push failed")

            def _update():
                if any_ok and not errors:
                    self._badge.update_status("ok", "Push successful")
                elif any_ok:
                    self._badge.update_status("warning", "Partial push: " + ", ".join(errors))
                else:
                    self._badge.update_status("error", "Push failed")
            self.after(0, _update)

        threading.Thread(target=_run, daemon=True).start()

    def _do_sync(self):
        if not self._check_repo():
            return

        self._log.clear()
        self._log.append("Starting sync (pull then push)...")
        self._badge.update_status("pending", "Syncing...")

        def _run():
            remote = self._pull_remote_var.get().strip() or "origin"
            branch = self._pull_branch_var.get().strip() or None

            # Pull
            self.after(0, lambda: self._log.append(f"Pulling from {remote}..."))
            ok_pull, out_pull = self._git.pull(self._repo_path, remote=remote, branch=branch)
            self.after(0, lambda: self._log.append(out_pull if out_pull.strip() else "(no output)"))

            if not ok_pull:
                self.after(0, lambda: self._badge.update_status("error", "Pull failed — sync aborted"))
                return

            self.after(0, lambda: self._log.append("Pull successful. Pushing..."))

            # Push
            path = self._repo_path
            cur_branch = self._current_branch or "main"
            status = self._git.get_status(path)
            if status:
                msg = self._commit_msg_var.get().strip() or "Update"
                self.after(0, lambda: self._log.append(f"Committing: {msg}"))
                self._git.add_all(path)
                self._git.commit(path, msg)

            any_ok = False
            errors = []

            if self._push_github.get() and self.app_state.get("github_api"):
                token = self.app_state.get("github_token", "")
                env = {"GIT_ASKPASS": "echo", "GIT_USERNAME": "x-token", "GIT_PASSWORD": token} if token else None
                ok, out = self._git.push(path, "origin", cur_branch, env=env)
                self.after(0, lambda o=out: self._log.append(f"GitHub: {o}"))
                if ok:
                    any_ok = True
                else:
                    errors.append("GitHub")

            if self._push_gitlab.get() and self.app_state.get("gitlab_api"):
                token = self.app_state.get("gitlab_token", "")
                env = {"GIT_ASKPASS": "echo", "GIT_USERNAME": "oauth2", "GIT_PASSWORD": token} if token else None
                ok, out = self._git.push(path, "gitlab", cur_branch, env=env)
                self.after(0, lambda o=out: self._log.append(f"GitLab: {o}"))
                if ok:
                    any_ok = True
                else:
                    errors.append("GitLab")

            def _update():
                if any_ok and not errors:
                    self._badge.update_status("ok", "Sync complete")
                elif any_ok:
                    self._badge.update_status("warning", "Partial: " + ", ".join(errors) + " push failed")
                else:
                    self._badge.update_status("error", "Push failed after pull")
            self.after(0, _update)

        threading.Thread(target=_run, daemon=True).start()
