"""Step 1 – System checks: git, identity (per platform)."""
import threading
import customtkinter as ctk
from ui.theme import *
from ui.widgets.common import (
    Card, PrimaryButton, Label, StatusBadge, SectionHeader, Divider
)
from core.git_manager import GitManager


class StepCheck(ctk.CTkFrame):
    def __init__(self, master, app_state, on_next, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app_state = app_state
        self.on_next   = on_next
        self.git       = GitManager()
        self._build()
        self._run_checks()

    # ── Layout ────────────────────────────────────────────────────────────────
    def _build(self):
        Label(self, text="System Check", size=22, bold=True).pack(anchor="w", pady=(0, 4))
        Label(self, text="Verifying your environment before we start",
              size=13, color=TEXT_DIM).pack(anchor="w", pady=(0, PAD))

        # ── Status checks ─────────────────────────────────────────────────────
        checks_card = Card(self)
        checks_card.pack(fill="x", pady=(0, PAD_SM))
        checks_card.columnconfigure(0, weight=1)

        self._git_badge = self._check_row(checks_card, "Git Installation",
                                          "Checking if git is installed…", 0)
        Divider(checks_card).grid(row=1, column=0, columnspan=3, sticky="ew", padx=PAD_SM)
        self._ver_badge = self._check_row(checks_card, "Git Version", "—", 2)

        # ── Per-platform identity card ─────────────────────────────────────────
        id_card = Card(self)
        id_card.pack(fill="x", pady=(0, PAD_SM))
        SectionHeader(id_card, "✎", "Git Identity per Platform",
                      "Name and email that will appear on your commits"
                      ).pack(fill="x", padx=PAD, pady=(PAD, PAD_SM))

        # Two columns: GitHub | GitLab
        cols = ctk.CTkFrame(id_card, fg_color="transparent")
        cols.pack(fill="x", padx=PAD, pady=(0, PAD))
        cols.columnconfigure((0, 1), weight=1)

        # GitHub column
        gh_frame = ctk.CTkFrame(cols, fg_color=BG3, corner_radius=8)
        gh_frame.grid(row=0, column=0, sticky="nsew", padx=(0, PAD_SM // 2))

        Label(gh_frame, text="GitHub", size=13, bold=True).pack(
            anchor="w", padx=PAD_SM, pady=(PAD_SM, PAD_SM // 2))

        Label(gh_frame, text="Name", size=11, color=TEXT_DIM).pack(
            anchor="w", padx=PAD_SM, pady=(0, 2))
        self._gh_name_var = ctk.StringVar()
        ctk.CTkEntry(
            gh_frame, textvariable=self._gh_name_var,
            placeholder_text="Your Name",
            fg_color=BG, border_color=BORDER, text_color=TEXT,
            font=ctk.CTkFont(family="Inter", size=12), height=38, corner_radius=6,
        ).pack(fill="x", padx=PAD_SM, pady=(0, PAD_SM // 2))

        Label(gh_frame, text="Email", size=11, color=TEXT_DIM).pack(
            anchor="w", padx=PAD_SM, pady=(0, 2))
        self._gh_email_var = ctk.StringVar()
        ctk.CTkEntry(
            gh_frame, textvariable=self._gh_email_var,
            placeholder_text="you@example.com",
            fg_color=BG, border_color=BORDER, text_color=TEXT,
            font=ctk.CTkFont(family="Inter", size=12), height=38, corner_radius=6,
        ).pack(fill="x", padx=PAD_SM, pady=(0, PAD_SM))

        # GitLab column
        gl_frame = ctk.CTkFrame(cols, fg_color=BG3, corner_radius=8)
        gl_frame.grid(row=0, column=1, sticky="nsew", padx=(PAD_SM // 2, 0))

        Label(gl_frame, text="GitLab", size=13, bold=True).pack(
            anchor="w", padx=PAD_SM, pady=(PAD_SM, PAD_SM // 2))

        Label(gl_frame, text="Name", size=11, color=TEXT_DIM).pack(
            anchor="w", padx=PAD_SM, pady=(0, 2))
        self._gl_name_var = ctk.StringVar()
        ctk.CTkEntry(
            gl_frame, textvariable=self._gl_name_var,
            placeholder_text="Your Name",
            fg_color=BG, border_color=BORDER, text_color=TEXT,
            font=ctk.CTkFont(family="Inter", size=12), height=38, corner_radius=6,
        ).pack(fill="x", padx=PAD_SM, pady=(0, PAD_SM // 2))

        Label(gl_frame, text="Email", size=11, color=TEXT_DIM).pack(
            anchor="w", padx=PAD_SM, pady=(0, 2))
        self._gl_email_var = ctk.StringVar()
        ctk.CTkEntry(
            gl_frame, textvariable=self._gl_email_var,
            placeholder_text="you@example.com",
            fg_color=BG, border_color=BORDER, text_color=TEXT,
            font=ctk.CTkFont(family="Inter", size=12), height=38, corner_radius=6,
        ).pack(fill="x", padx=PAD_SM, pady=(0, PAD_SM))

        # Hint
        Label(id_card,
              text="You can use different identities for each platform. "
                   "Leave both the same if you prefer.",
              size=11, color=TEXT_MUTED).pack(anchor="w", padx=PAD, pady=(0, PAD))

        # ── Next button ────────────────────────────────────────────────────────
        self._next_btn = PrimaryButton(self, text="Continue  →", command=self._next,
                                       state="disabled", width=180)
        self._next_btn.pack(anchor="e", pady=(PAD, 0))

    def _check_row(self, parent, title, subtitle, row):
        ctk.CTkLabel(
            parent, text=title,
            font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
            text_color=TEXT, anchor="w",
        ).grid(row=row, column=0, sticky="w", padx=PAD, pady=(PAD_SM, 2))
        ctk.CTkLabel(
            parent, text=subtitle,
            font=ctk.CTkFont(family="Inter", size=11),
            text_color=TEXT_DIM, anchor="w",
        ).grid(row=row, column=1, sticky="w", padx=PAD_SM)
        badge = StatusBadge(parent, status="pending", text="Checking…")
        badge.grid(row=row, column=2, sticky="e", padx=PAD, pady=PAD_SM)
        return badge

    # ── Checks ────────────────────────────────────────────────────────────────
    def _run_checks(self):
        threading.Thread(target=self._do_checks, daemon=True).start()

    def _do_checks(self):
        # Git installed?
        if self.git.is_git_installed():
            self.after(0, lambda: self._git_badge.update_status("ok", "✓ Installed"))
        else:
            self.after(0, lambda: self._git_badge.update_status("error", "✗ Not found"))
            self.after(0, self._show_install_hint)
            return

        # Version
        ver = self.git.get_version() or "unknown"
        self.after(0, lambda v=ver: self._ver_badge.update_status("ok", v))

        # Pre-fill identity fields from global git config
        name  = self.git.get_user_name()
        email = self.git.get_user_email()

        self.after(0, lambda n=name, e=email: self._prefill(n, e))
        self.after(0, lambda: self._next_btn.configure(state="normal"))

    def _prefill(self, name, email):
        if name:
            if not self._gh_name_var.get():
                self._gh_name_var.set(name)
            if not self._gl_name_var.get():
                self._gl_name_var.set(name)
        if email:
            if not self._gh_email_var.get():
                self._gh_email_var.set(email)
            if not self._gl_email_var.get():
                self._gl_email_var.set(email)

    def _show_install_hint(self):
        hint = Card(self)
        hint.pack(fill="x", pady=(0, PAD_SM))
        Label(hint, text="Git is not installed", size=14, bold=True, color=ERROR).pack(
            anchor="w", padx=PAD, pady=(PAD, 4))
        Label(hint,
              text="Run the following command in your terminal to install git:\n\n"
                   "    sudo apt install git      (Ubuntu/Debian)\n"
                   "    sudo dnf install git      (Fedora)\n"
                   "    brew install git          (macOS)",
              size=12, color=TEXT_DIM, justify="left",
              ).pack(anchor="w", padx=PAD, pady=(0, PAD))

    # ── Next ──────────────────────────────────────────────────────────────────
    def _next(self):
        gh_name  = self._gh_name_var.get().strip()
        gh_email = self._gh_email_var.get().strip()
        gl_name  = self._gl_name_var.get().strip()
        gl_email = self._gl_email_var.get().strip()

        # Fall back: if one platform's fields are empty, copy from the other
        if not gh_name:
            gh_name = gl_name
        if not gh_email:
            gh_email = gl_email
        if not gl_name:
            gl_name = gh_name
        if not gl_email:
            gl_email = gh_email

        self.app_state["github_git_name"]  = gh_name
        self.app_state["github_git_email"] = gh_email
        self.app_state["gitlab_git_name"]  = gl_name
        self.app_state["gitlab_git_email"] = gl_email

        # Keep backward-compat keys used elsewhere
        self.app_state["git_name"]  = gh_name or gl_name
        self.app_state["git_email"] = gh_email or gl_email

        self.on_next()
