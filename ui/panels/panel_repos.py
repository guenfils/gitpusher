"""Panel – Existing Repositories."""
import threading
import webbrowser
import customtkinter as ctk
from ui.theme import *
from ui.widgets.common import Card, PrimaryButton, SecondaryButton, Label, StatusBadge


class PanelRepos(ctk.CTkFrame):
    def __init__(self, master, app_state, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app_state = app_state
        self._all_repos = []
        self._platform = None

        # Determine initial platform
        has_github = bool(app_state.get("github_api"))
        has_gitlab = bool(app_state.get("gitlab_api"))
        if has_github:
            self._platform = "github"
        elif has_gitlab:
            self._platform = "gitlab"

        self._build_ui(has_github, has_gitlab)

        if self._platform:
            self._load_repos()
        else:
            self._status_var.set("Connect a platform first in Push Mode")

    def _build_ui(self, has_github, has_gitlab):
        # Title row
        title_row = ctk.CTkFrame(self, fg_color="transparent")
        title_row.pack(fill="x", pady=(0, PAD_SM))

        Label(title_row, text="Your Repositories", size=18, bold=True).pack(side="left")

        SecondaryButton(
            title_row, text="Refresh", width=90, height=34,
            command=self._on_refresh,
        ).pack(side="right")

        # Platform toggles
        has_github = bool(self.app_state.get("github_api"))
        has_gitlab = bool(self.app_state.get("gitlab_api"))

        if has_github or has_gitlab:
            toggle_row = ctk.CTkFrame(self, fg_color="transparent")
            toggle_row.pack(fill="x", pady=(0, PAD_SM))

            self._platform_btns = {}
            if has_github:
                btn = ctk.CTkButton(
                    toggle_row, text="GitHub", width=100, height=32,
                    corner_radius=16,
                    fg_color=PRIMARY if self._platform == "github" else BG3,
                    hover_color=PRIMARY_H if self._platform == "github" else BORDER,
                    text_color=WHITE,
                    font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
                    command=lambda: self._set_platform("github"),
                )
                btn.pack(side="left", padx=(0, 8))
                self._platform_btns["github"] = btn

            if has_gitlab:
                btn = ctk.CTkButton(
                    toggle_row, text="GitLab", width=100, height=32,
                    corner_radius=16,
                    fg_color=PRIMARY if self._platform == "gitlab" else BG3,
                    hover_color=PRIMARY_H if self._platform == "gitlab" else BORDER,
                    text_color=WHITE,
                    font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
                    command=lambda: self._set_platform("gitlab"),
                )
                btn.pack(side="left")
                self._platform_btns["gitlab"] = btn

        # Search bar
        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._render_list(self._search_var.get()))

        search_entry = ctk.CTkEntry(
            self,
            textvariable=self._search_var,
            placeholder_text="Search repositories...",
            fg_color=BG3,
            border_color=BORDER,
            text_color=TEXT,
            placeholder_text_color=TEXT_MUTED,
            corner_radius=8,
            height=38,
            font=ctk.CTkFont(family="Inter", size=12),
        )
        search_entry.pack(fill="x", pady=(0, PAD_SM))

        # Scrollable repo list
        self._list_frame = ctk.CTkScrollableFrame(
            self, fg_color=BG2, corner_radius=RADIUS,
            height=420,
            scrollbar_button_color=BG3,
            scrollbar_button_hover_color=BORDER,
        )
        self._list_frame.pack(fill="both", expand=True, pady=(0, PAD_SM))

        # Loading label inside list
        self._loading_label = Label(
            self._list_frame, text="Loading...", size=12, color=TEXT_DIM,
        )
        self._loading_label.pack(pady=PAD)

        # Status label
        self._status_var = ctk.StringVar(value="")
        Label(self, textvariable=self._status_var, size=11, color=TEXT_MUTED).pack(anchor="w")

    def _on_refresh(self):
        if self._platform:
            self._load_repos()

    def _load_repos(self):
        # Show loading state
        for w in self._list_frame.winfo_children():
            w.destroy()
        self._loading_label = Label(
            self._list_frame, text="Loading...", size=12, color=TEXT_DIM,
        )
        self._loading_label.pack(pady=PAD)
        self._status_var.set("Fetching repositories...")

        def _fetch():
            api = self.app_state.get(f"{self._platform}_api")
            if not api:
                self.after(0, lambda: self._status_var.set("Platform not connected"))
                return
            ok, repos = api.list_repos()
            if ok:
                self._all_repos = repos if isinstance(repos, list) else []
            else:
                self._all_repos = []
            self.after(0, lambda: self._render_list(self._search_var.get()))

        threading.Thread(target=_fetch, daemon=True).start()

    def _render_list(self, filter_text=""):
        for w in self._list_frame.winfo_children():
            w.destroy()

        ft = filter_text.strip().lower()
        repos = self._all_repos

        if ft:
            repos = [
                r for r in repos
                if ft in (r.get("name") or "").lower()
                or ft in (r.get("description") or "").lower()
                or ft in (r.get("path_with_namespace") or "").lower()
            ]

        if not repos:
            msg = "No repositories found." if self._all_repos else "No repositories found or not connected."
            Label(self._list_frame, text=msg, size=12, color=TEXT_DIM).pack(pady=PAD)
            self._status_var.set(f"0 repositories")
            return

        for repo in repos:
            self._build_repo_row(repo)

        count = len(repos)
        total = len(self._all_repos)
        if ft:
            self._status_var.set(f"{count} of {total} repositories")
        else:
            self._status_var.set(f"{total} repositories")

    def _build_repo_row(self, repo):
        row = ctk.CTkFrame(self._list_frame, fg_color=BG3, corner_radius=8)
        row.pack(fill="x", padx=8, pady=4)
        row.columnconfigure(1, weight=1)

        # Left: name + full name
        left = ctk.CTkFrame(row, fg_color="transparent")
        left.grid(row=0, column=0, padx=(PAD_SM, 8), pady=PAD_SM, sticky="w")

        if self._platform == "github":
            name = repo.get("name", "")
            full_name = repo.get("full_name", "")
            is_private = repo.get("private", False)
            url = repo.get("html_url", "")
            description = repo.get("description") or ""
            language = repo.get("language") or ""
            visibility = "Private" if is_private else "Public"
            vis_status = "warning" if is_private else "ok"
        else:
            name = repo.get("name", "")
            full_name = repo.get("path_with_namespace", "")
            visibility_raw = repo.get("visibility", "private")
            is_private = visibility_raw != "public"
            url = repo.get("web_url", "")
            description = repo.get("description") or ""
            language = ""
            visibility = visibility_raw.capitalize()
            vis_status = "warning" if is_private else "ok"

        Label(left, text=name, size=13, bold=True).pack(anchor="w")
        Label(left, text=full_name, size=11, color=TEXT_DIM).pack(anchor="w")
        if description:
            desc_short = description[:60] + "..." if len(description) > 60 else description
            Label(left, text=desc_short, size=10, color=TEXT_MUTED).pack(anchor="w")

        # Middle: badges
        mid = ctk.CTkFrame(row, fg_color="transparent")
        mid.grid(row=0, column=1, padx=8, pady=PAD_SM, sticky="w")

        StatusBadge(mid, status=vis_status, text=visibility).pack(side="left", padx=(0, 6))

        if language:
            ctk.CTkLabel(
                mid, text=language,
                fg_color=BG2, text_color=TEXT_DIM,
                corner_radius=6, padx=8, pady=4,
                font=ctk.CTkFont(family="Inter", size=10),
            ).pack(side="left", padx=(0, 6))

        # Right: action buttons
        right = ctk.CTkFrame(row, fg_color="transparent")
        right.grid(row=0, column=2, padx=(8, PAD_SM), pady=PAD_SM, sticky="e")

        _url = url
        SecondaryButton(
            right, text="Open", width=70, height=32,
            command=lambda u=_url: webbrowser.open(u),
        ).pack(side="left", padx=(0, 6))

        _clone_url = _url
        SecondaryButton(
            right, text="Clone", width=70, height=32,
            command=lambda u=_clone_url: self._copy_clone_url(u),
        ).pack(side="left")

    def _copy_clone_url(self, url):
        try:
            self.clipboard_clear()
            self.clipboard_append(url)
            self._status_var.set(f"Clone URL copied: {url}")
        except Exception:
            pass

    def _set_platform(self, platform):
        if platform == self._platform:
            return
        self._platform = platform
        # Update button styles
        for p, btn in getattr(self, "_platform_btns", {}).items():
            if p == platform:
                btn.configure(fg_color=PRIMARY, hover_color=PRIMARY_H)
            else:
                btn.configure(fg_color=BG3, hover_color=BORDER)
        self._all_repos = []
        self._load_repos()
