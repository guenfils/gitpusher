"""Step 2 – Platform and authentication setup."""
import threading
import webbrowser
import customtkinter as ctk
from ui.theme import *
from ui.widgets.common import (
    Card, PrimaryButton, SecondaryButton, Label, StatusBadge,
    SectionHeader, Divider, Entry
)
from core.github_api import GitHubAPI
from core.gitlab_api import GitLabAPI
from core.config_manager import ConfigManager
from core.ssh_manager import SSHManager


class StepPlatform(ctk.CTkFrame):
    def __init__(self, master, app_state, on_next, on_back, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app_state = app_state
        self.on_next   = on_next
        self.on_back   = on_back
        self.config    = ConfigManager()
        self.ssh       = SSHManager()
        self._build()

    # ── Layout ────────────────────────────────────────────────────────────────
    def _build(self):
        Label(self, text="Platform & Auth", size=22, bold=True).pack(anchor="w", pady=(0, 4))
        Label(self, text="Connect to GitHub and/or GitLab using a Personal Access Token",
              size=13, color=TEXT_DIM).pack(anchor="w", pady=(0, PAD))

        # Auth method selector
        method_card = Card(self)
        method_card.pack(fill="x", pady=(0, PAD_SM))
        Label(method_card, text="Authentication Method", size=13, bold=True).pack(
            anchor="w", padx=PAD, pady=(PAD, PAD_SM))

        method_row = ctk.CTkFrame(method_card, fg_color="transparent")
        method_row.pack(fill="x", padx=PAD, pady=(0, PAD))

        self._auth_var = ctk.StringVar(value=self.config.get_auth_method())
        ctk.CTkRadioButton(
            method_row, text="Personal Access Token  (recommended)",
            variable=self._auth_var, value="token",
            font=ctk.CTkFont(family="Inter", size=12),
            text_color=TEXT, fg_color=PRIMARY,
            command=self._on_method_change,
        ).pack(side="left", padx=(0, PAD))
        ctk.CTkRadioButton(
            method_row, text="SSH Key",
            variable=self._auth_var, value="ssh",
            font=ctk.CTkFont(family="Inter", size=12),
            text_color=TEXT, fg_color=PRIMARY,
            command=self._on_method_change,
        ).pack(side="left")

        # ── Token section ──────────────────────────────────────────────────────
        self._token_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._token_frame.pack(fill="x")

        # GitHub token
        gh_card = Card(self._token_frame)
        gh_card.pack(fill="x", pady=(0, PAD_SM))
        SectionHeader(gh_card, "G", "GitHub", "github.com").pack(
            fill="x", padx=PAD, pady=(PAD, PAD_SM))

        gh_row = ctk.CTkFrame(gh_card, fg_color="transparent")
        gh_row.pack(fill="x", padx=PAD, pady=(0, PAD_SM))
        gh_row.columnconfigure(0, weight=1)

        self._gh_token_var = ctk.StringVar(value=self.config.get_github_token())
        self._gh_entry = ctk.CTkEntry(
            gh_row, textvariable=self._gh_token_var,
            placeholder_text="ghp_xxxxxxxxxxxxxxxxxxxx",
            show="•",
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            font=ctk.CTkFont(family="Inter", size=12), height=42, corner_radius=8,
        )
        self._gh_entry.grid(row=0, column=0, sticky="ew", padx=(0, PAD_SM))

        self._gh_status = StatusBadge(gh_row, status="pending", text="Not connected")
        self._gh_status.grid(row=0, column=1)

        gh_btns = ctk.CTkFrame(gh_card, fg_color="transparent")
        gh_btns.pack(fill="x", padx=PAD, pady=(0, PAD))
        PrimaryButton(gh_btns, text="Connect GitHub", command=self._connect_github,
                      width=160).pack(side="left", padx=(0, PAD_SM))
        SecondaryButton(gh_btns, text="Get Token →",
                        command=lambda: webbrowser.open(
                            "https://github.com/settings/tokens/new?scopes=repo,admin:public_key"),
                        width=120).pack(side="left")

        # GitLab token
        gl_card = Card(self._token_frame)
        gl_card.pack(fill="x", pady=(0, PAD_SM))
        SectionHeader(gl_card, "GL", "GitLab", "gitlab.com or self-hosted").pack(
            fill="x", padx=PAD, pady=(PAD, PAD_SM))

        gl_url_row = ctk.CTkFrame(gl_card, fg_color="transparent")
        gl_url_row.pack(fill="x", padx=PAD, pady=(0, PAD_SM))
        Label(gl_url_row, text="GitLab URL:", size=12, color=TEXT_DIM).pack(side="left", padx=(0, 8))
        self._gl_url_var = ctk.StringVar(value=self.config.get_gitlab_url())
        ctk.CTkEntry(
            gl_url_row, textvariable=self._gl_url_var,
            placeholder_text="https://gitlab.com",
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            font=ctk.CTkFont(family="Inter", size=12), height=36, corner_radius=8, width=280,
        ).pack(side="left")

        gl_row = ctk.CTkFrame(gl_card, fg_color="transparent")
        gl_row.pack(fill="x", padx=PAD, pady=(0, PAD_SM))
        gl_row.columnconfigure(0, weight=1)

        self._gl_token_var = ctk.StringVar(value=self.config.get_gitlab_token())
        ctk.CTkEntry(
            gl_row, textvariable=self._gl_token_var,
            placeholder_text="glpat-xxxxxxxxxxxxxxxxxxxx",
            show="•",
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            font=ctk.CTkFont(family="Inter", size=12), height=42, corner_radius=8,
        ).grid(row=0, column=0, sticky="ew", padx=(0, PAD_SM))

        self._gl_status = StatusBadge(gl_row, status="pending", text="Not connected")
        self._gl_status.grid(row=0, column=1)

        gl_btns = ctk.CTkFrame(gl_card, fg_color="transparent")
        gl_btns.pack(fill="x", padx=PAD, pady=(0, PAD))
        PrimaryButton(gl_btns, text="Connect GitLab", command=self._connect_gitlab,
                      width=160).pack(side="left", padx=(0, PAD_SM))
        SecondaryButton(gl_btns, text="Get Token →",
                        command=lambda: webbrowser.open(
                            self._gl_url_var.get() + "/-/user_settings/personal_access_tokens"),
                        width=120).pack(side="left")

        # ── SSH section ────────────────────────────────────────────────────────
        self._ssh_frame = ctk.CTkFrame(self, fg_color="transparent")

        ssh_card = Card(self._ssh_frame)
        ssh_card.pack(fill="x", pady=(0, PAD_SM))
        SectionHeader(ssh_card, "🔑", "SSH Key Management",
                      "Generate or use an existing SSH key").pack(
            fill="x", padx=PAD, pady=(PAD, PAD_SM))

        self._ssh_status_lbl = Label(ssh_card, text="", size=12, color=TEXT_DIM)
        self._ssh_status_lbl.pack(anchor="w", padx=PAD, pady=(0, PAD_SM))

        ssh_btns = ctk.CTkFrame(ssh_card, fg_color="transparent")
        ssh_btns.pack(fill="x", padx=PAD, pady=(0, PAD))
        PrimaryButton(ssh_btns, text="Generate New Key",
                      command=self._generate_ssh_key, width=180).pack(side="left", padx=(0, PAD_SM))
        SecondaryButton(ssh_btns, text="Show Public Key",
                        command=self._show_pub_key, width=160).pack(side="left")

        self._pub_key_box = ctk.CTkTextbox(
            ssh_card, height=80, fg_color=BG, text_color=TEXT,
            font=ctk.CTkFont(family="JetBrains Mono", size=10),
            corner_radius=8, border_color=BORDER, border_width=1,
        )

        self._on_method_change()

        # Navigation
        nav = ctk.CTkFrame(self, fg_color="transparent")
        nav.pack(fill="x", pady=(PAD, 0))
        SecondaryButton(nav, text="← Back", command=self.on_back, width=120).pack(side="left")
        self._next_btn = PrimaryButton(nav, text="Continue  →", command=self._next,
                                       state="disabled", width=180)
        self._next_btn.pack(side="right")

        # Auto-connect if tokens saved
        self._auto_connect()

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _on_method_change(self):
        method = self._auth_var.get()
        self.config.set_auth_method(method)
        if method == "token":
            self._token_frame.pack(fill="x")
            self._ssh_frame.pack_forget()
        else:
            self._token_frame.pack_forget()
            self._ssh_frame.pack(fill="x")
            self._refresh_ssh_status()

    def _auto_connect(self):
        gh_token = self._gh_token_var.get()
        gl_token = self._gl_token_var.get()
        if gh_token:
            threading.Thread(target=self._do_connect_github, daemon=True).start()
        if gl_token:
            threading.Thread(target=self._do_connect_gitlab, daemon=True).start()

    # GitHub
    def _connect_github(self):
        self._gh_status.update_status("pending", "Connecting…")
        threading.Thread(target=self._do_connect_github, daemon=True).start()

    def _do_connect_github(self):
        token = self._gh_token_var.get().strip()
        if not token:
            self.after(0, lambda: self._gh_status.update_status("error", "No token"))
            return
        api = GitHubAPI(token)
        ok, data = api.get_user()
        if ok:
            login = data.get("login", "?")
            self.app_state["github_token"]  = token
            self.app_state["github_user"]   = login
            self.app_state["github_api"]    = api
            self.config.set_github_token(token)
            self.after(0, lambda l=login: self._gh_status.update_status("ok", f"✓ {l}"))
        else:
            self.after(0, lambda: self._gh_status.update_status("error", "✗ Invalid token"))
        self.after(0, self._check_can_continue)

    # GitLab
    def _connect_gitlab(self):
        self._gl_status.update_status("pending", "Connecting…")
        threading.Thread(target=self._do_connect_gitlab, daemon=True).start()

    def _do_connect_gitlab(self):
        token   = self._gl_token_var.get().strip()
        gl_url  = self._gl_url_var.get().strip() or "https://gitlab.com"
        if not token:
            self.after(0, lambda: self._gl_status.update_status("error", "No token"))
            return
        api = GitLabAPI(token, gl_url)
        ok, data = api.get_user()
        if ok:
            login = data.get("username", "?")
            self.app_state["gitlab_token"]  = token
            self.app_state["gitlab_user"]   = login
            self.app_state["gitlab_api"]    = api
            self.config.set_gitlab_token(token)
            self.config.set_gitlab_url(gl_url)
            self.after(0, lambda l=login: self._gl_status.update_status("ok", f"✓ {l}"))
        else:
            self.after(0, lambda: self._gl_status.update_status("error", "✗ Invalid token"))
        self.after(0, self._check_can_continue)

    def _check_can_continue(self):
        gh_ok = "github_api" in self.app_state
        gl_ok = "gitlab_api" in self.app_state
        if gh_ok or gl_ok:
            self._next_btn.configure(state="normal")

    # SSH
    def _refresh_ssh_status(self):
        keys = self.ssh.get_existing_keys()
        if keys:
            names = ", ".join(k["name"] for k in keys)
            self._ssh_status_lbl.configure(
                text=f"Found {len(keys)} key(s): {names}", text_color=SUCCESS)
            self.app_state["ssh_key"] = keys[0]["private"]
            self._next_btn.configure(state="normal")
        else:
            self._ssh_status_lbl.configure(text="No SSH keys found", text_color=WARNING)

    def _generate_ssh_key(self):
        email = self.app_state.get("git_email", "user@example.com")
        ok, result, path = self.ssh.generate_key(email)
        if ok:
            self.app_state["ssh_key"] = path
            self._ssh_status_lbl.configure(
                text=f"✓ Key generated: {path}", text_color=SUCCESS)
            self._show_pub_key()
            self._next_btn.configure(state="normal")
        else:
            self._ssh_status_lbl.configure(text=f"Error: {result}", text_color=ERROR)

    def _show_pub_key(self):
        key = self.ssh.get_public_key(self.config.get_ssh_key_name())
        if key:
            self._pub_key_box.pack(fill="x", padx=PAD, pady=(0, PAD))
            self._pub_key_box.configure(state="normal")
            self._pub_key_box.delete("1.0", "end")
            self._pub_key_box.insert("1.0", key)
            self._pub_key_box.configure(state="disabled")

    def _next(self):
        self.on_next()
