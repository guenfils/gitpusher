"""Settings & Preferences panel."""
import os
import customtkinter as ctk
from ui.theme import *
from ui.widgets.common import Card, PrimaryButton, SecondaryButton, Label, SectionHeader, StatusBadge
from core.config_manager import ConfigManager, CONFIG_PATH


class PanelSettings(ctk.CTkFrame):
    def __init__(self, master, app_state, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app_state = app_state
        self.cfg = ConfigManager()
        self._build_ui()

    def _build_ui(self):
        # Scrollable container
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=0, pady=0)

        # Header
        header = ctk.CTkFrame(scroll, fg_color="transparent")
        header.pack(fill="x", padx=PAD, pady=(PAD, PAD_SM))
        Label(header, text="Settings & Preferences", size=22, bold=True).pack(anchor="w")
        Label(header, text=f"Saved to {CONFIG_PATH}", size=11, color=TEXT_MUTED).pack(anchor="w")

        # ── Push Wizard Defaults ──────────────────────────────
        wiz_card = Card(scroll)
        wiz_card.pack(fill="x", padx=PAD, pady=(0, PAD_SM))
        SectionHeader(wiz_card, "W", "Push Wizard", "").pack(fill="x", padx=PAD_SM, pady=(PAD_SM, PAD_SM))

        self._branch_var = ctk.StringVar(value=self.cfg.get_default_branch())
        row = ctk.CTkFrame(wiz_card, fg_color="transparent")
        row.pack(fill="x", padx=PAD_SM, pady=(0, PAD_SM))
        Label(row, text="Default branch:", size=12).pack(side="left", padx=(0, 8))
        ctk.CTkEntry(
            row, textvariable=self._branch_var, width=120,
            fg_color=BG3, border_color=BORDER, text_color=TEXT, corner_radius=8,
        ).pack(side="left")

        self._msg_var = ctk.StringVar(value=self.cfg.get_default_commit_msg())
        row2 = ctk.CTkFrame(wiz_card, fg_color="transparent")
        row2.pack(fill="x", padx=PAD_SM, pady=(0, PAD_SM))
        Label(row2, text="Default commit message:", size=12).pack(side="left", padx=(0, 8))
        ctk.CTkEntry(
            row2, textvariable=self._msg_var, width=280,
            fg_color=BG3, border_color=BORDER, text_color=TEXT, corner_radius=8,
        ).pack(side="left")

        self._vis_var = ctk.StringVar(value=self.cfg.get_default_visibility())
        row3 = ctk.CTkFrame(wiz_card, fg_color="transparent")
        row3.pack(fill="x", padx=PAD_SM, pady=(0, PAD_SM))
        Label(row3, text="Default visibility:", size=12).pack(side="left", padx=(0, 8))
        ctk.CTkOptionMenu(
            row3, variable=self._vis_var, values=["private", "public"],
            fg_color=BG3, button_color=BG3, button_hover_color=BORDER,
            text_color=TEXT, dropdown_fg_color=BG2,
            font=ctk.CTkFont(family="Inter", size=12), corner_radius=8,
        ).pack(side="left")

        self._skip_readme_var = ctk.BooleanVar(value=bool(self.cfg.get_skip_readme_step()))
        row4 = ctk.CTkFrame(wiz_card, fg_color="transparent")
        row4.pack(fill="x", padx=PAD_SM, pady=(0, PAD_SM))
        ctk.CTkSwitch(
            row4, text="Skip README Generator step by default",
            variable=self._skip_readme_var,
            text_color=TEXT, fg_color=BG3, progress_color=PRIMARY,
            font=ctk.CTkFont(family="Inter", size=12),
        ).pack(side="left")

        self._skip_gitignore_var = ctk.BooleanVar(value=bool(self.cfg.get_skip_gitignore_step()))
        row5 = ctk.CTkFrame(wiz_card, fg_color="transparent")
        row5.pack(fill="x", padx=PAD_SM, pady=(0, PAD_SM))
        ctk.CTkSwitch(
            row5, text="Skip .gitignore Generator by default",
            variable=self._skip_gitignore_var,
            text_color=TEXT, fg_color=BG3, progress_color=PRIMARY,
            font=ctk.CTkFont(family="Inter", size=12),
        ).pack(side="left")

        # ── Authentication ────────────────────────────────────
        auth_card = Card(scroll)
        auth_card.pack(fill="x", padx=PAD, pady=(0, PAD_SM))
        SectionHeader(auth_card, "K", "Saved Credentials", "").pack(fill="x", padx=PAD_SM, pady=(PAD_SM, PAD_SM))

        gh_token = self.cfg.get_github_token()
        gh_row = ctk.CTkFrame(auth_card, fg_color="transparent")
        gh_row.pack(fill="x", padx=PAD_SM, pady=(0, PAD_SM))
        Label(gh_row, text="GitHub token:", size=12).pack(side="left", padx=(0, 8))
        if gh_token:
            Label(gh_row, text="●●●●●●●● ..." + gh_token[-4:], size=12, color=TEXT_DIM).pack(side="left", padx=(0, 8))
            StatusBadge(gh_row, status="ok", text="Connected").pack(side="left")
        else:
            Label(gh_row, text="(not set)", size=12, color=TEXT_MUTED).pack(side="left", padx=(0, 8))
            StatusBadge(gh_row, status="pending", text="Not set").pack(side="left")

        gl_token = self.cfg.get_gitlab_token()
        gl_row = ctk.CTkFrame(auth_card, fg_color="transparent")
        gl_row.pack(fill="x", padx=PAD_SM, pady=(0, PAD_SM))
        Label(gl_row, text="GitLab token:", size=12).pack(side="left", padx=(0, 8))
        if gl_token:
            Label(gl_row, text="●●●●●●●● ..." + gl_token[-4:], size=12, color=TEXT_DIM).pack(side="left", padx=(0, 8))
            StatusBadge(gl_row, status="ok", text="Connected").pack(side="left")
        else:
            Label(gl_row, text="(not set)", size=12, color=TEXT_MUTED).pack(side="left", padx=(0, 8))
            StatusBadge(gl_row, status="pending", text="Not set").pack(side="left")

        gl_url_row = ctk.CTkFrame(auth_card, fg_color="transparent")
        gl_url_row.pack(fill="x", padx=PAD_SM, pady=(0, PAD_SM))
        Label(gl_url_row, text="GitLab URL:", size=12).pack(side="left", padx=(0, 8))
        Label(gl_url_row, text=self.cfg.get_gitlab_url(), size=12, color=TEXT_DIM).pack(side="left")

        Label(auth_card, text="Tokens are saved to ~/.config/git-pusher/config.json",
              size=11, color=TEXT_MUTED).pack(anchor="w", padx=PAD_SM, pady=(0, PAD_SM))

        SecondaryButton(
            auth_card, text="Clear All Credentials", width=180, height=36,
            fg_color=ERROR, text_color=WHITE, hover_color="#DC2626",
            command=self._clear_credentials,
        ).pack(anchor="w", padx=PAD_SM, pady=(0, PAD_SM))

        # ── Watch Mode ────────────────────────────────────────
        watch_card = Card(scroll)
        watch_card.pack(fill="x", padx=PAD, pady=(0, PAD_SM))
        SectionHeader(watch_card, "W", "Watch Mode", "").pack(fill="x", padx=PAD_SM, pady=(PAD_SM, PAD_SM))

        self._interval_var = ctk.StringVar(value=self.cfg.get_watch_interval())
        ctk.CTkSegmentedButton(
            watch_card, variable=self._interval_var,
            values=["5 min", "10 min", "15 min", "30 min", "1 hour"],
            fg_color=BG3, selected_color=PRIMARY, selected_hover_color=PRIMARY_H,
            unselected_color=BG3, unselected_hover_color=BORDER,
            text_color=TEXT, font=ctk.CTkFont(family="Inter", size=12),
        ).pack(anchor="w", padx=PAD_SM, pady=(0, PAD_SM))

        self._watch_msg_var = ctk.StringVar(value=self.cfg.get_watch_msg_template())
        wmsg_row = ctk.CTkFrame(watch_card, fg_color="transparent")
        wmsg_row.pack(fill="x", padx=PAD_SM, pady=(0, PAD_SM))
        Label(wmsg_row, text="Commit message template:", size=12).pack(side="left", padx=(0, 8))
        ctk.CTkEntry(
            wmsg_row, textvariable=self._watch_msg_var, width=280,
            fg_color=BG3, border_color=BORDER, text_color=TEXT, corner_radius=8,
        ).pack(side="left")

        # ── Export Defaults ───────────────────────────────────
        export_card = Card(scroll)
        export_card.pack(fill="x", padx=PAD, pady=(0, PAD_SM))
        SectionHeader(export_card, "E", "Export / Backup", "").pack(fill="x", padx=PAD_SM, pady=(PAD_SM, PAD_SM))

        self._format_var = ctk.StringVar(value=self.cfg.get_export_format())
        ctk.CTkSegmentedButton(
            export_card, variable=self._format_var,
            values=["ZIP", "TAR.GZ"],
            fg_color=BG3, selected_color=PRIMARY, selected_hover_color=PRIMARY_H,
            unselected_color=BG3, unselected_hover_color=BORDER,
            text_color=TEXT, font=ctk.CTkFont(family="Inter", size=12),
        ).pack(anchor="w", padx=PAD_SM, pady=(0, PAD_SM))

        self._exclude_var = ctk.StringVar(value=self.cfg.get_export_exclude())
        excl_row = ctk.CTkFrame(export_card, fg_color="transparent")
        excl_row.pack(fill="x", padx=PAD_SM, pady=(0, PAD_SM))
        Label(excl_row, text="Exclude patterns:", size=12).pack(side="left", padx=(0, 8))
        ctk.CTkEntry(
            excl_row, textvariable=self._exclude_var, width=400,
            fg_color=BG3, border_color=BORDER, text_color=TEXT, corner_radius=8,
        ).pack(side="left")

        # ── Gitflow Defaults ──────────────────────────────────
        gf_card = Card(scroll)
        gf_card.pack(fill="x", padx=PAD, pady=(0, PAD_SM))
        SectionHeader(gf_card, "G", "Gitflow", "").pack(fill="x", padx=PAD_SM, pady=(PAD_SM, PAD_SM))

        self._gitflow_main_var = ctk.StringVar(value=self.cfg.get_gitflow_main())
        gf_row1 = ctk.CTkFrame(gf_card, fg_color="transparent")
        gf_row1.pack(fill="x", padx=PAD_SM, pady=(0, PAD_SM))
        Label(gf_row1, text="Main branch name:", size=12).pack(side="left", padx=(0, 8))
        ctk.CTkEntry(
            gf_row1, textvariable=self._gitflow_main_var, width=120,
            fg_color=BG3, border_color=BORDER, text_color=TEXT, corner_radius=8,
        ).pack(side="left")

        self._gitflow_develop_var = ctk.StringVar(value=self.cfg.get_gitflow_develop())
        gf_row2 = ctk.CTkFrame(gf_card, fg_color="transparent")
        gf_row2.pack(fill="x", padx=PAD_SM, pady=(0, PAD_SM))
        Label(gf_row2, text="Develop branch name:", size=12).pack(side="left", padx=(0, 8))
        ctk.CTkEntry(
            gf_row2, textvariable=self._gitflow_develop_var, width=120,
            fg_color=BG3, border_color=BORDER, text_color=TEXT, corner_radius=8,
        ).pack(side="left")

        # ── About ─────────────────────────────────────────────
        about_card = Card(scroll)
        about_card.pack(fill="x", padx=PAD, pady=(0, PAD_SM))
        SectionHeader(about_card, "i", "About", "").pack(fill="x", padx=PAD_SM, pady=(PAD_SM, PAD_SM))
        Label(about_card, text="Git Pusher — GitHub & GitLab in one click", size=13, bold=True).pack(
            anchor="w", padx=PAD_SM, pady=(0, 4))
        Label(about_card, text="Developed by Guenson  •  v2.0.0", size=12, color=TEXT_DIM).pack(
            anchor="w", padx=PAD_SM, pady=(0, 4))
        Label(about_card, text="github.com/guenfils  |  gitlab.com/guenson", size=11, color=TEXT_MUTED).pack(
            anchor="w", padx=PAD_SM, pady=(0, 4))
        Label(about_card, text="Config: ~/.config/git-pusher/config.json", size=11, color=TEXT_MUTED).pack(
            anchor="w", padx=PAD_SM, pady=(0, PAD_SM))
        about_btns = ctk.CTkFrame(about_card, fg_color="transparent")
        about_btns.pack(anchor="w", padx=PAD_SM, pady=(0, PAD_SM))
        SecondaryButton(
            about_btns, text="Open Config Folder", width=160, height=34,
            command=lambda: os.system("xdg-open ~/.config/git-pusher"),
        ).pack(side="left", padx=(0, 8))
        SecondaryButton(
            about_btns, text="Reset to Defaults", width=140, height=34,
            command=self._reset_defaults,
        ).pack(side="left")

        # Status badge + Save button
        self._status_badge = StatusBadge(scroll, status="pending", text="")
        self._status_badge.pack(anchor="w", padx=PAD, pady=(0, PAD_SM))

        PrimaryButton(
            scroll, text="Save All Settings", height=46,
            command=self._save_all,
        ).pack(fill="x", padx=PAD, pady=(0, PAD))

    def _save_all(self):
        self.cfg.set_default_branch(self._branch_var.get())
        self.cfg.set_default_commit_msg(self._msg_var.get())
        self.cfg.set_default_visibility(self._vis_var.get())
        self.cfg.set_skip_readme_step(self._skip_readme_var.get())
        self.cfg.set_skip_gitignore_step(self._skip_gitignore_var.get())
        self.cfg.set_watch_interval(self._interval_var.get())
        self.cfg.set_watch_msg_template(self._watch_msg_var.get())
        self.cfg.set_export_format(self._format_var.get())
        self.cfg.set_export_exclude(self._exclude_var.get())
        self.cfg.set_gitflow_main(self._gitflow_main_var.get())
        self.cfg.set_gitflow_develop(self._gitflow_develop_var.get())

        self.app_state["default_branch"] = self._branch_var.get()
        self.app_state["default_commit_msg"] = self._msg_var.get()

        self._status_badge.update_status("ok", "Settings saved")
        self.after(3000, lambda: self._status_badge.update_status("pending", ""))

    def _clear_credentials(self):
        win = ctk.CTkToplevel(self)
        win.title("Clear Credentials")
        win.geometry("360x160")
        win.configure(fg_color=BG)
        win.grab_set()
        Label(win, text="Clear all saved tokens and credentials?", size=13).pack(padx=PAD, pady=(PAD, PAD_SM))
        btn_row = ctk.CTkFrame(win, fg_color="transparent")
        btn_row.pack(padx=PAD, pady=PAD_SM)
        SecondaryButton(btn_row, text="Cancel", width=120, height=36,
                        command=win.destroy).pack(side="left", padx=(0, PAD_SM))

        def _do_clear():
            self.cfg.delete("github_token")
            self.cfg.delete("gitlab_token")
            win.destroy()
            self._status_badge.update_status("warning", "Credentials cleared")
            self.after(3000, lambda: self._status_badge.update_status("pending", ""))

        ctk.CTkButton(
            btn_row, text="Clear", width=120, height=36,
            fg_color=ERROR, text_color=WHITE, hover_color="#DC2626",
            corner_radius=8, font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
            command=_do_clear,
        ).pack(side="left")

    def _reset_defaults(self):
        win = ctk.CTkToplevel(self)
        win.title("Reset to Defaults")
        win.geometry("380x160")
        win.configure(fg_color=BG)
        win.grab_set()
        Label(win, text="Reset all preference settings to defaults?", size=13).pack(padx=PAD, pady=(PAD, PAD_SM))
        btn_row = ctk.CTkFrame(win, fg_color="transparent")
        btn_row.pack(padx=PAD, pady=PAD_SM)
        SecondaryButton(btn_row, text="Cancel", width=120, height=36,
                        command=win.destroy).pack(side="left", padx=(0, PAD_SM))

        def _do_reset():
            keys = [
                "default_branch", "default_commit_msg", "default_visibility",
                "skip_readme_step", "skip_gitignore_step", "watch_interval",
                "watch_msg_template", "export_format", "export_exclude",
                "gitflow_main", "gitflow_develop",
            ]
            for k in keys:
                self.cfg.delete(k)
            win.destroy()
            # Reload values from cfg defaults
            self._branch_var.set(self.cfg.get_default_branch())
            self._msg_var.set(self.cfg.get_default_commit_msg())
            self._vis_var.set(self.cfg.get_default_visibility())
            self._skip_readme_var.set(self.cfg.get_skip_readme_step())
            self._skip_gitignore_var.set(self.cfg.get_skip_gitignore_step())
            self._interval_var.set(self.cfg.get_watch_interval())
            self._watch_msg_var.set(self.cfg.get_watch_msg_template())
            self._format_var.set(self.cfg.get_export_format())
            self._exclude_var.set(self.cfg.get_export_exclude())
            self._gitflow_main_var.set(self.cfg.get_gitflow_main())
            self._gitflow_develop_var.set(self.cfg.get_gitflow_develop())
            self._status_badge.update_status("warning", "Reset to defaults")
            self.after(3000, lambda: self._status_badge.update_status("pending", ""))

        ctk.CTkButton(
            btn_row, text="Reset", width=120, height=36,
            fg_color=WARNING, text_color=WHITE, hover_color="#D97706",
            corner_radius=8, font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
            command=_do_reset,
        ).pack(side="left")
