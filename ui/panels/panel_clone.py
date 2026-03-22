"""Panel – Clone Repository."""
import threading
from tkinter import filedialog
import customtkinter as ctk
from ui.theme import *
from ui.widgets.common import Card, PrimaryButton, SecondaryButton, Label, StatusBadge, LogBox
from core.git_manager import GitManager


class PanelClone(ctk.CTkFrame):
    def __init__(self, master, app_state, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app_state = app_state
        self._git = GitManager()
        self._repos = []
        self._source_mode = ctk.StringVar(value="url")

        self._build_ui()
        self._load_platform_repos()

    def _build_ui(self):
        # Title
        Label(self, text="Clone Repository", size=18, bold=True).pack(anchor="w", pady=(0, 4))
        Label(self, text="Download a repository to your local machine", size=12, color=TEXT_DIM).pack(anchor="w", pady=(0, PAD))

        # Card: Source
        src_card = Card(self)
        src_card.pack(fill="x", pady=(0, PAD_SM))

        Label(src_card, text="Source", size=13, bold=True).pack(anchor="w", padx=PAD, pady=(PAD_SM, 8))

        radio_row = ctk.CTkFrame(src_card, fg_color="transparent")
        radio_row.pack(fill="x", padx=PAD, pady=(0, 8))

        ctk.CTkRadioButton(
            radio_row, text="From URL", variable=self._source_mode, value="url",
            fg_color=PRIMARY, hover_color=PRIMARY_H,
            text_color=TEXT, font=ctk.CTkFont(family="Inter", size=12),
            command=self._on_source_change,
        ).pack(side="left", padx=(0, PAD))

        ctk.CTkRadioButton(
            radio_row, text="From your repos", variable=self._source_mode, value="repos",
            fg_color=PRIMARY, hover_color=PRIMARY_H,
            text_color=TEXT, font=ctk.CTkFont(family="Inter", size=12),
            command=self._on_source_change,
        ).pack(side="left")

        # URL entry
        self._url_frame = ctk.CTkFrame(src_card, fg_color="transparent")
        self._url_frame.pack(fill="x", padx=PAD, pady=(0, PAD_SM))

        self._url_var = ctk.StringVar()
        self._url_entry = ctk.CTkEntry(
            self._url_frame,
            textvariable=self._url_var,
            placeholder_text="https://github.com/user/repo",
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            placeholder_text_color=TEXT_MUTED,
            corner_radius=8, height=38,
            font=ctk.CTkFont(family="Inter", size=12),
        )
        self._url_entry.pack(fill="x")

        # Repo combobox (hidden initially)
        self._repos_frame = ctk.CTkFrame(src_card, fg_color="transparent")
        self._repos_var = ctk.StringVar()
        self._repos_combo = ctk.CTkComboBox(
            self._repos_frame,
            variable=self._repos_var,
            values=["Loading..."],
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            button_color=BG3, button_hover_color=BORDER,
            dropdown_fg_color=BG2, dropdown_text_color=TEXT,
            corner_radius=8, height=38,
            font=ctk.CTkFont(family="Inter", size=12),
            command=self._on_repo_selected,
        )
        self._repos_combo.pack(fill="x", padx=PAD, pady=(0, PAD_SM))

        # Card: Destination
        dest_card = Card(self)
        dest_card.pack(fill="x", pady=(0, PAD_SM))

        Label(dest_card, text="Destination", size=13, bold=True).pack(anchor="w", padx=PAD, pady=(PAD_SM, 8))

        dest_row = ctk.CTkFrame(dest_card, fg_color="transparent")
        dest_row.pack(fill="x", padx=PAD, pady=(0, PAD_SM))

        self._dest_var = ctk.StringVar()
        ctk.CTkEntry(
            dest_row,
            textvariable=self._dest_var,
            placeholder_text="/home/user/projects/my-repo",
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            placeholder_text_color=TEXT_MUTED,
            corner_radius=8, height=38,
            font=ctk.CTkFont(family="Inter", size=12),
        ).pack(side="left", fill="x", expand=True, padx=(0, 8))

        SecondaryButton(
            dest_row, text="Browse", width=90, height=38,
            command=self._browse_dest,
        ).pack(side="right")

        # Card: Options
        opt_card = Card(self)
        opt_card.pack(fill="x", pady=(0, PAD_SM))

        Label(opt_card, text="Options", size=13, bold=True).pack(anchor="w", padx=PAD, pady=(PAD_SM, 8))

        self._branch_var = ctk.StringVar()
        ctk.CTkEntry(
            opt_card,
            textvariable=self._branch_var,
            placeholder_text="Leave empty for default branch",
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            placeholder_text_color=TEXT_MUTED,
            corner_radius=8, height=38,
            font=ctk.CTkFont(family="Inter", size=12),
        ).pack(fill="x", padx=PAD, pady=(0, PAD_SM))

        # Clone button
        PrimaryButton(self, text="Clone Repository", command=self._do_clone).pack(fill="x", pady=(0, PAD_SM))

        # Log box
        self._log = LogBox(self, height=120)
        self._log.pack(fill="x", pady=(0, PAD_SM))

        # Status badge
        self._badge = StatusBadge(self, status="pending", text="")
        self._badge.pack(anchor="w")

    def _on_source_change(self):
        mode = self._source_mode.get()
        if mode == "url":
            self._repos_frame.pack_forget()
            self._url_frame.pack(fill="x", padx=PAD, pady=(0, PAD_SM))
        else:
            self._url_frame.pack_forget()
            self._repos_frame.pack(fill="x")

    def _load_platform_repos(self):
        def _fetch():
            repo_names = []
            repo_map = {}
            for plat in ("github", "gitlab"):
                api = self.app_state.get(f"{plat}_api")
                if not api:
                    continue
                ok, repos = api.list_repos()
                if ok and isinstance(repos, list):
                    for r in repos:
                        if plat == "github":
                            name = r.get("full_name", r.get("name", ""))
                            url = r.get("clone_url") or r.get("html_url", "")
                        else:
                            name = r.get("path_with_namespace", r.get("name", ""))
                            url = r.get("http_url_to_repo") or r.get("web_url", "")
                        display = f"[{plat.upper()}] {name}"
                        repo_names.append(display)
                        repo_map[display] = url
            self._repo_map = repo_map
            self.after(0, lambda: self._repos_combo.configure(
                values=repo_names if repo_names else ["No repos found"]
            ))

        self._repo_map = {}
        threading.Thread(target=_fetch, daemon=True).start()

    def _on_repo_selected(self, choice):
        url = self._repo_map.get(choice, "")
        if url:
            self._url_var.set(url)

    def _browse_dest(self):
        folder = filedialog.askdirectory(title="Select destination folder")
        if folder:
            self._dest_var.set(folder)

    def _do_clone(self):
        url = self._url_var.get().strip()
        dest = self._dest_var.get().strip()
        branch = self._branch_var.get().strip() or None

        if not url:
            self._badge.update_status("error", "Please enter a repository URL")
            return
        if not dest:
            self._badge.update_status("error", "Please select a destination folder")
            return

        self._log.clear()
        self._log.append(f"Cloning {url} -> {dest} ...")
        self._badge.update_status("pending", "Cloning...")

        def _run():
            ok, output = self._git.clone(url, dest, branch=branch)
            def _update():
                self._log.append(output if output.strip() else "(no output)")
                if ok:
                    self._badge.update_status("ok", "Clone successful")
                    self._log.append("Done.")
                else:
                    self._badge.update_status("error", "Clone failed")
            self.after(0, _update)

        threading.Thread(target=_run, daemon=True).start()
