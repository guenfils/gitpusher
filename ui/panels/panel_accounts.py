"""Panel – Multi-account Manager."""
import threading
import customtkinter as ctk
from ui.theme import *
from ui.widgets.common import Card, PrimaryButton, SecondaryButton, Label, StatusBadge, SectionHeader, Divider
from core.github_api import GitHubAPI
from core.gitlab_api import GitLabAPI


class PanelAccounts(ctk.CTkFrame):
    def __init__(self, master, app_state, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app_state = app_state

        # Migrate existing single-account state
        if "github_accounts" not in app_state and app_state.get("github_token"):
            app_state["github_accounts"] = [{
                "token": app_state["github_token"],
                "username": app_state.get("github_user", ""),
                "api": app_state.get("github_api"),
                "active": True,
            }]
        if "github_accounts" not in app_state:
            app_state["github_accounts"] = []

        if "gitlab_accounts" not in app_state and app_state.get("gitlab_token"):
            app_state["gitlab_accounts"] = [{
                "token": app_state["gitlab_token"],
                "username": app_state.get("gitlab_user", ""),
                "api": app_state.get("gitlab_api"),
                "base_url": "https://gitlab.com",
                "active": True,
            }]
        if "gitlab_accounts" not in app_state:
            app_state["gitlab_accounts"] = []

        self._build_ui()

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build_ui(self):
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True)
        self._scroll = scroll

        # Title
        Label(scroll, text="Accounts", size=22, bold=True).pack(
            anchor="w", padx=PAD, pady=(PAD, 2))
        Label(scroll, text="Manage multiple GitHub and GitLab accounts",
              size=12, color=TEXT_DIM).pack(anchor="w", padx=PAD, pady=(0, PAD_SM))

        # Two columns
        cols = ctk.CTkFrame(scroll, fg_color="transparent")
        cols.pack(fill="x", padx=PAD, pady=(0, PAD_SM))
        cols.columnconfigure(0, weight=1)
        cols.columnconfigure(1, weight=1)

        # GitHub column
        gh_outer = Card(cols)
        gh_outer.grid(row=0, column=0, sticky="nsew", padx=(0, PAD_SM))

        SectionHeader(gh_outer, number="G", title="GitHub Accounts").pack(
            padx=PAD, pady=(PAD, PAD_SM), fill="x")

        self._gh_list_frame = ctk.CTkFrame(gh_outer, fg_color="transparent")
        self._gh_list_frame.pack(padx=PAD_SM, pady=(0, PAD_SM), fill="x")

        Divider(gh_outer).pack(fill="x", padx=PAD, pady=(0, PAD_SM))

        Label(gh_outer, text="Add GitHub Account", size=12, bold=True).pack(
            anchor="w", padx=PAD, pady=(0, PAD_SM))

        self._gh_token_entry = ctk.CTkEntry(
            gh_outer, placeholder_text="GitHub Personal Access Token",
            show="*",
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            placeholder_text_color=TEXT_MUTED, corner_radius=8, height=36,
            font=ctk.CTkFont(family="Inter", size=12),
        )
        self._gh_token_entry.pack(fill="x", padx=PAD, pady=(0, PAD_SM))

        PrimaryButton(gh_outer, text="Verify & Add", height=40,
                      command=self._add_github).pack(fill="x", padx=PAD, pady=(0, PAD_SM))

        self._gh_add_badge = StatusBadge(gh_outer, status="pending", text="")
        self._gh_add_badge.pack(anchor="w", padx=PAD, pady=(0, PAD))
        self._gh_add_badge.pack_forget()

        # GitLab column
        gl_outer = Card(cols)
        gl_outer.grid(row=0, column=1, sticky="nsew", padx=(PAD_SM, 0))

        SectionHeader(gl_outer, number="GL", title="GitLab Accounts").pack(
            padx=PAD, pady=(PAD, PAD_SM), fill="x")

        self._gl_list_frame = ctk.CTkFrame(gl_outer, fg_color="transparent")
        self._gl_list_frame.pack(padx=PAD_SM, pady=(0, PAD_SM), fill="x")

        Divider(gl_outer).pack(fill="x", padx=PAD, pady=(0, PAD_SM))

        Label(gl_outer, text="Add GitLab Account", size=12, bold=True).pack(
            anchor="w", padx=PAD, pady=(0, PAD_SM))

        self._gl_url_entry = ctk.CTkEntry(
            gl_outer, placeholder_text="https://gitlab.com",
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            placeholder_text_color=TEXT_MUTED, corner_radius=8, height=36,
            font=ctk.CTkFont(family="Inter", size=12),
        )
        self._gl_url_entry.pack(fill="x", padx=PAD, pady=(0, PAD_SM))
        self._gl_url_entry.insert(0, "https://gitlab.com")

        self._gl_token_entry = ctk.CTkEntry(
            gl_outer, placeholder_text="GitLab Personal Access Token",
            show="*",
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            placeholder_text_color=TEXT_MUTED, corner_radius=8, height=36,
            font=ctk.CTkFont(family="Inter", size=12),
        )
        self._gl_token_entry.pack(fill="x", padx=PAD, pady=(0, PAD_SM))

        PrimaryButton(gl_outer, text="Verify & Add", height=40,
                      command=self._add_gitlab).pack(fill="x", padx=PAD, pady=(0, PAD_SM))

        self._gl_add_badge = StatusBadge(gl_outer, status="pending", text="")
        self._gl_add_badge.pack(anchor="w", padx=PAD, pady=(0, PAD))
        self._gl_add_badge.pack_forget()

        # Info card
        info_card = Card(scroll)
        info_card.pack(fill="x", padx=PAD, pady=(PAD_SM, PAD))
        Label(
            info_card,
            text=(
                "When you switch the active account, all subsequent push operations "
                "will use the new account's credentials."
            ),
            size=12, color=TEXT_DIM,
        ).pack(padx=PAD, pady=PAD)

        # Render initial account lists
        self._render_gh_list()
        self._render_gl_list()

    # ── Render account lists ───────────────────────────────────────────────────

    def _render_gh_list(self):
        for w in self._gh_list_frame.winfo_children():
            w.destroy()
        accounts = self.app_state.get("github_accounts", [])
        if not accounts:
            Label(self._gh_list_frame, text="No GitHub accounts added.",
                  size=11, color=TEXT_MUTED).pack(anchor="w", pady=4)
            return
        for acct in accounts:
            self._render_account_row(self._gh_list_frame, acct, "github")

    def _render_gl_list(self):
        for w in self._gl_list_frame.winfo_children():
            w.destroy()
        accounts = self.app_state.get("gitlab_accounts", [])
        if not accounts:
            Label(self._gl_list_frame, text="No GitLab accounts added.",
                  size=11, color=TEXT_MUTED).pack(anchor="w", pady=4)
            return
        for acct in accounts:
            self._render_account_row(self._gl_list_frame, acct, "gitlab")

    def _render_account_row(self, parent, acct, platform):
        is_active = acct.get("active", False)
        username = acct.get("username") or "Unknown"

        row = ctk.CTkFrame(
            parent,
            fg_color=BG3 if is_active else BG,
            corner_radius=8,
        )
        row.pack(fill="x", pady=4, padx=0)

        left = ctk.CTkFrame(row, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True, padx=PAD_SM, pady=PAD_SM)

        # Avatar + username
        avatar_row = ctk.CTkFrame(left, fg_color="transparent")
        avatar_row.pack(anchor="w")
        ctk.CTkLabel(
            avatar_row,
            text=username[0].upper() if username else "?",
            width=32, height=32, corner_radius=16,
            fg_color=PRIMARY if is_active else BG3,
            text_color=WHITE,
            font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
        ).pack(side="left", padx=(0, PAD_SM))
        Label(avatar_row, text=username, size=13, bold=True).pack(side="left")

        # Active badge or Set Active button
        badge_row = ctk.CTkFrame(left, fg_color="transparent")
        badge_row.pack(anchor="w", pady=(4, 0))
        if is_active:
            StatusBadge(badge_row, status="ok", text="Active").pack(side="left")
        else:
            StatusBadge(badge_row, status="pending", text="Inactive").pack(side="left", padx=(0, PAD_SM))
            if platform == "github":
                PrimaryButton(badge_row, text="Set Active", width=90, height=28,
                              command=lambda a=acct: self._set_active_github(a)).pack(side="left")
            else:
                PrimaryButton(badge_row, text="Set Active", width=90, height=28,
                              command=lambda a=acct: self._set_active_gitlab(a)).pack(side="left")

        # Remove button (right side)
        right_col = ctk.CTkFrame(row, fg_color="transparent")
        right_col.pack(side="right", padx=PAD_SM, pady=PAD_SM)

        if is_active:
            # Show disabled-looking remove button with tooltip hint
            SecondaryButton(
                right_col, text="Remove", width=80, height=28,
                state="disabled",
                fg_color=BG3, text_color=TEXT_MUTED,
            ).pack()
        else:
            if platform == "github":
                SecondaryButton(
                    right_col, text="Remove", width=80, height=28,
                    fg_color="#7F1D1D", text_color=WHITE, hover_color=ERROR,
                    command=lambda a=acct: self._remove_github(a),
                ).pack()
            else:
                SecondaryButton(
                    right_col, text="Remove", width=80, height=28,
                    fg_color="#7F1D1D", text_color=WHITE, hover_color=ERROR,
                    command=lambda a=acct: self._remove_gitlab(a),
                ).pack()

    # ── GitHub account management ──────────────────────────────────────────────

    def _set_active_github(self, account):
        for a in self.app_state.get("github_accounts", []):
            a["active"] = False
        account["active"] = True
        self.app_state["github_api"] = account["api"]
        self.app_state["github_token"] = account["token"]
        self.app_state["github_user"] = account["username"]
        self._render_gh_list()

    def _remove_github(self, account):
        if account.get("active"):
            self._gh_add_badge.update_status("error", "Deactivate account first")
            self._gh_add_badge.pack(anchor="w", padx=PAD, pady=(0, PAD))
            return
        accounts = self.app_state.get("github_accounts", [])
        if account in accounts:
            accounts.remove(account)
        self._render_gh_list()

    def _add_github(self):
        token = self._gh_token_entry.get().strip()
        if not token:
            self._gh_add_badge.update_status("error", "Enter a token")
            self._gh_add_badge.pack(anchor="w", padx=PAD, pady=(0, PAD))
            return
        self._gh_add_badge.update_status("pending", "Verifying…")
        self._gh_add_badge.pack(anchor="w", padx=PAD, pady=(0, PAD))
        threading.Thread(target=self._do_add_github, args=(token,), daemon=True).start()

    def _do_add_github(self, token):
        api = GitHubAPI(token)
        ok, data = api.get_user()
        if ok:
            username = data.get("login", "unknown")
            new_acct = {
                "token": token,
                "username": username,
                "api": api,
                "active": False,
            }
            self.app_state["github_accounts"].append(new_acct)
            self.after(0, lambda: self._gh_token_entry.delete(0, "end"))
            self.after(0, lambda: self._gh_add_badge.update_status("ok", f"Added {username}"))
            self.after(0, self._render_gh_list)
        else:
            msg = str(data) if data else "Verification failed"
            self.after(0, lambda: self._gh_add_badge.update_status("error", msg))

    # ── GitLab account management ──────────────────────────────────────────────

    def _set_active_gitlab(self, account):
        for a in self.app_state.get("gitlab_accounts", []):
            a["active"] = False
        account["active"] = True
        self.app_state["gitlab_api"] = account["api"]
        self.app_state["gitlab_token"] = account["token"]
        self.app_state["gitlab_user"] = account["username"]
        self._render_gl_list()

    def _remove_gitlab(self, account):
        if account.get("active"):
            self._gl_add_badge.update_status("error", "Deactivate account first")
            self._gl_add_badge.pack(anchor="w", padx=PAD, pady=(0, PAD))
            return
        accounts = self.app_state.get("gitlab_accounts", [])
        if account in accounts:
            accounts.remove(account)
        self._render_gl_list()

    def _add_gitlab(self):
        token = self._gl_token_entry.get().strip()
        base_url = self._gl_url_entry.get().strip() or "https://gitlab.com"
        if not token:
            self._gl_add_badge.update_status("error", "Enter a token")
            self._gl_add_badge.pack(anchor="w", padx=PAD, pady=(0, PAD))
            return
        self._gl_add_badge.update_status("pending", "Verifying…")
        self._gl_add_badge.pack(anchor="w", padx=PAD, pady=(0, PAD))
        threading.Thread(target=self._do_add_gitlab, args=(token, base_url), daemon=True).start()

    def _do_add_gitlab(self, token, base_url):
        api = GitLabAPI(token, base_url)
        ok, data = api.get_user()
        if ok:
            username = data.get("username") or data.get("name", "unknown")
            new_acct = {
                "token": token,
                "username": username,
                "api": api,
                "base_url": base_url,
                "active": False,
            }
            self.app_state["gitlab_accounts"].append(new_acct)
            self.after(0, lambda: self._gl_token_entry.delete(0, "end"))
            self.after(0, lambda: self._gl_add_badge.update_status("ok", f"Added {username}"))
            self.after(0, self._render_gl_list)
        else:
            msg = str(data) if data else "Verification failed"
            self.after(0, lambda: self._gl_add_badge.update_status("error", msg))
