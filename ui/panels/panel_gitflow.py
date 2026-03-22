"""Gitflow panel — structured branching workflow."""
import threading
import customtkinter as ctk
from tkinter import filedialog
from ui.theme import *
from ui.widgets.common import Card, PrimaryButton, SecondaryButton, Label, SectionHeader, StatusBadge, LogBox
from core.git_manager import GitManager
from core.config_manager import ConfigManager


class PanelGitflow(ctk.CTkFrame):
    def __init__(self, master, app_state, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app_state = app_state
        self.git = GitManager()
        self.cfg = ConfigManager()
        self._path_var = ctk.StringVar()
        self._feature_var = ctk.StringVar()
        self._release_var = ctk.StringVar()
        self._release_tag_var = ctk.StringVar()
        self._hotfix_var = ctk.StringVar()
        self._bugfix_var = ctk.StringVar()
        self._initialized = False
        self._build_ui()

    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=PAD, pady=(PAD, PAD_SM))
        Label(header, text="Gitflow", size=22, bold=True).pack(anchor="w")
        Label(header, text="Structured branching workflow for your projects", size=12, color=TEXT_DIM).pack(anchor="w")

        # Repo + status card
        repo_card = Card(self)
        repo_card.pack(fill="x", padx=PAD, pady=(0, PAD_SM))
        repo_row = ctk.CTkFrame(repo_card, fg_color="transparent")
        repo_row.pack(fill="x", padx=PAD_SM, pady=PAD_SM)
        ctk.CTkEntry(
            repo_row, textvariable=self._path_var, width=260,
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            state="readonly", corner_radius=8,
        ).pack(side="left", padx=(0, PAD_SM))
        SecondaryButton(repo_row, text="Browse...", width=80, height=34, command=self._browse).pack(side="left", padx=(0, 6))
        PrimaryButton(repo_row, text="Load", width=80, height=34, command=self._load_gitflow).pack(side="left")

        # Status row
        self._status_row = ctk.CTkFrame(repo_card, fg_color="transparent")
        self._status_row.pack(fill="x", padx=PAD_SM, pady=(0, PAD_SM))
        self._status_badge = StatusBadge(self._status_row, status="pending", text="Select a repository")
        self._status_badge.pack(side="left", padx=(0, 8))
        self._init_btn = PrimaryButton(
            self._status_row, text="Initialize Gitflow", width=160, height=34,
            command=self._init_gitflow,
        )

        # 2x2 grid of workflow cards
        grid = ctk.CTkFrame(self, fg_color="transparent")
        grid.pack(fill="both", expand=True, padx=PAD, pady=(0, PAD_SM))
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

        # Feature card
        feature_card = Card(grid)
        feature_card.configure(border_width=1, border_color="#4F46E5")
        feature_card.grid(row=0, column=0, sticky="nsew", padx=(0, PAD_SM // 2), pady=(0, PAD_SM // 2))
        self._build_workflow_card(
            feature_card, "F", "Feature Branch", "New feature development",
            "#4F46E5", self._feature_var, "feature", "my-feature",
        )

        # Release card
        release_card = Card(grid)
        release_card.configure(border_width=1, border_color=SUCCESS)
        release_card.grid(row=0, column=1, sticky="nsew", padx=(PAD_SM // 2, 0), pady=(0, PAD_SM // 2))
        self._build_release_card(release_card)

        # Hotfix card
        hotfix_card = Card(grid)
        hotfix_card.configure(border_width=1, border_color=ERROR)
        hotfix_card.grid(row=1, column=0, sticky="nsew", padx=(0, PAD_SM // 2), pady=(PAD_SM // 2, 0))
        self._build_workflow_card(
            hotfix_card, "H", "Hotfix Branch", "Emergency fix for production",
            ERROR, self._hotfix_var, "hotfix", "critical-bug-fix",
        )

        # Bugfix card
        bugfix_card = Card(grid)
        bugfix_card.configure(border_width=1, border_color=WARNING)
        bugfix_card.grid(row=1, column=1, sticky="nsew", padx=(PAD_SM // 2, 0), pady=(PAD_SM // 2, 0))
        self._build_workflow_card(
            bugfix_card, "B", "Bugfix Branch", "Fix a bug from develop",
            WARNING, self._bugfix_var, "bugfix", "login-error",
        )

        # LogBox
        self._log = LogBox(self, height=120)
        self._log.pack(fill="x", padx=PAD, pady=(0, PAD))

    def _build_workflow_card(self, card, badge_text, title, subtitle, color, name_var, prefix, placeholder):
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=PAD_SM, pady=(PAD_SM, PAD_SM))
        # Badge
        ctk.CTkLabel(
            header, text=badge_text, width=28, height=28,
            fg_color=color, text_color=WHITE, corner_radius=14,
            font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
        ).pack(side="left", padx=(0, 10))
        txt = ctk.CTkFrame(header, fg_color="transparent")
        txt.pack(side="left")
        Label(txt, text=title, size=14, bold=True).pack(anchor="w")
        Label(txt, text=subtitle, size=11, color=TEXT_DIM).pack(anchor="w")

        # Existing branches list
        list_frame = ctk.CTkFrame(card, fg_color="transparent")
        list_frame.pack(fill="x", padx=PAD_SM, pady=(0, PAD_SM))

        # Store reference for refresh
        attr = f"_list_{prefix}"
        setattr(self, attr, list_frame)

        # Entry + buttons
        entry_row = ctk.CTkFrame(card, fg_color="transparent")
        entry_row.pack(fill="x", padx=PAD_SM, pady=(0, PAD_SM))
        ctk.CTkEntry(
            entry_row, textvariable=name_var, width=180,
            placeholder_text=placeholder,
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            placeholder_text_color=TEXT_MUTED, corner_radius=8,
        ).pack(side="left", padx=(0, 6))

        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.pack(fill="x", padx=PAD_SM, pady=(0, PAD_SM))
        PrimaryButton(
            btn_row, text=f"Start {title.split()[0]}", width=130, height=34,
            command=lambda: self._start(prefix, name_var),
        ).pack(side="left", padx=(0, 6))
        SecondaryButton(
            btn_row, text=f"Finish {title.split()[0]}", width=130, height=34,
            command=lambda: self._finish(prefix, name_var),
        ).pack(side="left")

    def _build_release_card(self, card):
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=PAD_SM, pady=(PAD_SM, PAD_SM))
        ctk.CTkLabel(
            header, text="R", width=28, height=28,
            fg_color=SUCCESS, text_color=WHITE, corner_radius=14,
            font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
        ).pack(side="left", padx=(0, 10))
        txt = ctk.CTkFrame(header, fg_color="transparent")
        txt.pack(side="left")
        Label(txt, text="Release Branch", size=14, bold=True).pack(anchor="w")
        Label(txt, text="Prepare a new release", size=11, color=TEXT_DIM).pack(anchor="w")

        # Existing releases list
        self._list_release = ctk.CTkFrame(card, fg_color="transparent")
        self._list_release.pack(fill="x", padx=PAD_SM, pady=(0, PAD_SM))

        entry_row = ctk.CTkFrame(card, fg_color="transparent")
        entry_row.pack(fill="x", padx=PAD_SM, pady=(0, PAD_SM))
        ctk.CTkEntry(
            entry_row, textvariable=self._release_var, width=180,
            placeholder_text="1.0.0",
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            placeholder_text_color=TEXT_MUTED, corner_radius=8,
        ).pack(side="left", padx=(0, 6))

        tag_row = ctk.CTkFrame(card, fg_color="transparent")
        tag_row.pack(fill="x", padx=PAD_SM, pady=(0, PAD_SM))
        Label(tag_row, text="Tag:", size=12).pack(side="left", padx=(0, 6))
        ctk.CTkEntry(
            tag_row, textvariable=self._release_tag_var, width=140,
            placeholder_text="v1.0.0",
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            placeholder_text_color=TEXT_MUTED, corner_radius=8,
        ).pack(side="left")

        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.pack(fill="x", padx=PAD_SM, pady=(0, PAD_SM))
        PrimaryButton(
            btn_row, text="Start Release", width=130, height=34,
            command=lambda: self._start("release", self._release_var),
        ).pack(side="left", padx=(0, 6))
        SecondaryButton(
            btn_row, text="Finish Release", width=130, height=34,
            command=lambda: self._finish("release", self._release_var, self._release_tag_var),
        ).pack(side="left")

    def _browse(self):
        path = filedialog.askdirectory(title="Select Git Repository")
        if path:
            self._path_var.set(path)
            self._load_gitflow()

    def _load_gitflow(self):
        path = self._path_var.get()
        if not path:
            self._log_msg("[!] No repository path selected.")
            return
        threading.Thread(target=self._bg_load, daemon=True).start()

    def _bg_load(self):
        path = self._path_var.get()
        has_develop = self.git.gitflow_has_develop(path)
        self.after(0, lambda: self._update_status(has_develop))
        self.after(0, self._refresh_lists)

    def _update_status(self, initialized):
        self._initialized = initialized
        if initialized:
            self._status_badge.update_status("ok", "Gitflow initialized")
            self._init_btn.pack_forget()
        else:
            self._status_badge.update_status("warning", "Gitflow not initialized")
            self._init_btn.pack(side="left")

    def _init_gitflow(self):
        path = self._path_var.get()
        if not path:
            self._log_msg("[!] No repository path selected.")
            return
        main = self.cfg.get_gitflow_main()
        develop = self.cfg.get_gitflow_develop()
        threading.Thread(target=self._bg_init, args=(path, main, develop), daemon=True).start()

    def _bg_init(self, path, main, develop):
        ok, out = self.git.gitflow_init(path, main, develop)
        status = "[OK] Gitflow initialized." if ok else f"[!] Init failed: {out.strip()}"
        self.after(0, lambda: self._log_msg(status))
        self.after(0, self._load_gitflow)

    def _start(self, prefix, name_var):
        path = self._path_var.get()
        name = name_var.get().strip()
        if not path:
            self._log_msg("[!] No repository path selected.")
            return
        if not name:
            self._log_msg(f"[!] Enter a name for the {prefix} branch.")
            return
        base = self.cfg.get_gitflow_develop()
        if prefix == "hotfix":
            base = self.cfg.get_gitflow_main()
        threading.Thread(target=self._bg_start, args=(path, prefix, name, base), daemon=True).start()

    def _bg_start(self, path, prefix, name, base):
        ok, branch, out = self.git.gitflow_start(path, prefix, name, base)
        status = f"[OK] Started {branch}." if ok else f"[!] Start failed: {out.strip()}"
        self.after(0, lambda: self._log_msg(status))
        if ok:
            self.after(0, self._refresh_lists)

    def _finish(self, prefix, name_var, tag_var=None):
        path = self._path_var.get()
        name = name_var.get().strip()
        if not path:
            self._log_msg("[!] No repository path selected.")
            return
        if not name:
            self._log_msg(f"[!] Enter the name of the {prefix} branch to finish.")
            return
        main = self.cfg.get_gitflow_main()
        tag = tag_var.get().strip() if tag_var else None
        threading.Thread(target=self._bg_finish, args=(path, prefix, name, main, tag), daemon=True).start()

    def _bg_finish(self, path, prefix, name, main, tag):
        ok, out = self.git.gitflow_finish(path, prefix, name, main, tag)
        status = f"[OK] Finished {prefix}/{name}." if ok else f"[!] Finish had issues:\n{out}"
        self.after(0, lambda: self._log_msg(status))
        self.after(0, self._refresh_lists)

    def _refresh_lists(self):
        path = self._path_var.get()
        if not path:
            return
        threading.Thread(target=self._bg_refresh_lists, daemon=True).start()

    def _bg_refresh_lists(self):
        path = self._path_var.get()
        for prefix in ["feature", "release", "hotfix", "bugfix"]:
            branches = self.git.gitflow_list(path, prefix)
            self.after(0, lambda p=prefix, bl=branches: self._render_list(p, bl))

    def _render_list(self, prefix, branches):
        attr = f"_list_{prefix}"
        frame = getattr(self, attr, None)
        if frame is None:
            return
        for w in frame.winfo_children():
            w.destroy()
        if not branches:
            Label(frame, text=f"No {prefix} branches", size=11, color=TEXT_MUTED).pack(anchor="w")
            return
        for b in branches:
            pill = ctk.CTkLabel(
                frame, text=b,
                fg_color=BG3, text_color=TEXT, corner_radius=6, padx=8,
                font=ctk.CTkFont(family="Inter", size=11),
            )
            pill.pack(side="left", padx=(0, 4), pady=2)

    def _log_msg(self, msg):
        self.after(0, lambda: self._log.append(msg))
