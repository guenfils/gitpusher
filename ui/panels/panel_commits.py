"""Panel – Visual commit history."""
import threading
import customtkinter as ctk
from tkinter import filedialog
from ui.theme import *
from ui.widgets.common import Card, PrimaryButton, SecondaryButton, Label, StatusBadge
from core.git_manager import GitManager


class PanelCommits(ctk.CTkFrame):
    def __init__(self, master, app_state, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app_state = app_state
        self.git = GitManager()
        self.path_var = ctk.StringVar()
        self.branch_var = ctk.StringVar()
        self._branch_combo = None
        self._stats_frame = None
        self._commits_scroll = None
        self._status_label = None
        self._build_ui()

    def _build_ui(self):
        # Scrollable outer container
        outer = ctk.CTkScrollableFrame(self, fg_color="transparent")
        outer.pack(fill="both", expand=True, padx=PAD, pady=PAD)
        outer.columnconfigure(0, weight=1)

        # Title row
        Label(outer, text="Commit History", size=22, bold=True).pack(anchor="w")
        Label(outer, text="Visual log of your repository commits", size=13,
              color=TEXT_DIM).pack(anchor="w", pady=(2, PAD_SM))

        # Controls card
        ctrl_card = Card(outer)
        ctrl_card.pack(fill="x", pady=(0, PAD_SM))

        # Row 1 – folder picker
        row1 = ctk.CTkFrame(ctrl_card, fg_color="transparent")
        row1.pack(fill="x", padx=PAD_SM, pady=(PAD_SM, 4))
        Label(row1, text="Repository:", size=12, color=TEXT_DIM).pack(side="left", padx=(0, 6))
        ctk.CTkEntry(
            row1,
            textvariable=self.path_var,
            state="readonly",
            width=300,
            fg_color=BG3,
            border_color=BORDER,
            text_color=TEXT,
            corner_radius=8,
            height=36,
            font=ctk.CTkFont(family="Inter", size=12),
        ).pack(side="left", padx=(0, 6))
        SecondaryButton(row1, text="Browse...", width=90, height=36,
                        command=self._browse).pack(side="left")

        # Row 2 – branch + load
        row2 = ctk.CTkFrame(ctrl_card, fg_color="transparent")
        row2.pack(fill="x", padx=PAD_SM, pady=(4, PAD_SM))
        Label(row2, text="Branch:", size=12, color=TEXT_DIM).pack(side="left", padx=(0, 6))
        self._branch_combo = ctk.CTkComboBox(
            row2,
            variable=self.branch_var,
            values=[],
            width=200,
            fg_color=BG3,
            border_color=BORDER,
            text_color=TEXT,
            button_color=BG3,
            button_hover_color=BORDER,
            dropdown_fg_color=BG2,
            dropdown_text_color=TEXT,
            corner_radius=8,
            height=36,
            font=ctk.CTkFont(family="Inter", size=12),
        )
        self._branch_combo.pack(side="left", padx=(0, 6))
        PrimaryButton(row2, text="Load History", width=130, height=36,
                      command=self._load_history).pack(side="left")

        # Stats row (hidden initially)
        self._stats_frame = ctk.CTkFrame(outer, fg_color="transparent")

        # Status / loading label
        self._status_label = Label(outer, text="", size=12, color=TEXT_DIM)
        self._status_label.pack(anchor="w", pady=(0, 4))

        # Commits scrollable list
        self._commits_scroll = ctk.CTkScrollableFrame(outer, fg_color=BG, height=380,
                                                       corner_radius=RADIUS)
        self._commits_scroll.pack(fill="x", pady=(0, PAD_SM))
        Label(self._commits_scroll, text="Browse a repository to view commit history.",
              size=12, color=TEXT_MUTED).pack(pady=PAD)

    def _browse(self):
        path = filedialog.askdirectory(title="Select Git Repository")
        if not path:
            return
        self.path_var.set(path)
        branches = self.git.get_branches(path)
        if branches:
            self._branch_combo.configure(values=branches)
            self.branch_var.set(branches[0])
        else:
            self._branch_combo.configure(values=["(default)"])
            self.branch_var.set("(default)")

    def _load_history(self):
        path = self.path_var.get().strip()
        if not path:
            self._status_label.configure(text="Please select a repository first.", text_color=WARNING)
            return
        branch = self.branch_var.get().strip()
        if branch in ("", "(default)"):
            branch = None

        self._status_label.configure(text="Loading...", text_color=TEXT_DIM)
        # Clear existing rows
        for w in self._commits_scroll.winfo_children():
            w.destroy()
        Label(self._commits_scroll, text="Loading...", size=12, color=TEXT_DIM).pack(pady=PAD)

        def worker():
            commits = self.git.get_log(path, branch, max_count=200)
            self.after(0, lambda: self._on_loaded(commits))

        threading.Thread(target=worker, daemon=True).start()

    def _on_loaded(self, commits):
        self._status_label.configure(text="")
        self._render_stats(commits)
        self._render_commits(commits)

    def _render_stats(self, commits):
        # Remove old stats frame children
        for w in self._stats_frame.winfo_children():
            w.destroy()

        total = len(commits)
        authors = len({c["author"] for c in commits if c["author"]})
        latest = commits[0]["when"] if commits else "—"

        stats = [
            ("Total Commits", str(total)),
            ("Contributors", str(authors)),
            ("Latest", latest),
        ]

        for label_text, value_text in stats:
            sc = ctk.CTkFrame(self._stats_frame, fg_color=BG3, corner_radius=RADIUS)
            sc.pack(side="left", padx=(0, PAD_SM), pady=(0, PAD_SM), fill="x", expand=True)
            Label(sc, text=label_text, size=11, color=TEXT_DIM).pack(anchor="w", padx=PAD_SM, pady=(PAD_SM, 2))
            Label(sc, text=value_text, size=18, bold=True, color=TEXT).pack(anchor="w", padx=PAD_SM, pady=(0, PAD_SM))

        self._stats_frame.pack(fill="x", pady=(0, PAD_SM), before=self._status_label)

    def _render_commits(self, commits):
        for w in self._commits_scroll.winfo_children():
            w.destroy()

        if not commits:
            Label(self._commits_scroll, text="No commits found.", size=12,
                  color=TEXT_MUTED).pack(pady=PAD)
            return

        for idx, commit in enumerate(commits):
            is_merge = commit["message"].lower().startswith("merge")
            has_tags = bool(commit["tags"])
            dot_color = SUCCESS if has_tags else (WARNING if is_merge else PRIMARY)
            row_bg = BG2 if idx % 2 == 0 else "transparent"

            row = ctk.CTkFrame(self._commits_scroll, fg_color=row_bg, corner_radius=6)
            row.pack(fill="x", pady=1, padx=2)

            # Left: dot + vertical line
            left = ctk.CTkFrame(row, fg_color="transparent", width=24)
            left.pack(side="left", fill="y", padx=(8, 0))
            left.pack_propagate(False)
            ctk.CTkLabel(
                left, text="●", text_color=dot_color,
                font=ctk.CTkFont(family="Inter", size=10),
                fg_color="transparent",
            ).pack(pady=(8, 0))
            ctk.CTkFrame(left, width=2, height=20, fg_color=BORDER).pack(pady=(2, 4))

            # Center: message + meta
            center = ctk.CTkFrame(row, fg_color="transparent")
            center.pack(side="left", fill="x", expand=True, padx=PAD_SM, pady=6)

            # Message row with badges
            msg_row = ctk.CTkFrame(center, fg_color="transparent")
            msg_row.pack(fill="x", anchor="w")

            msg_text = commit["message"]
            if len(msg_text) > 65:
                msg_text = msg_text[:62] + "..."
            Label(msg_row, text=msg_text, size=13, bold=True, color=TEXT).pack(side="left")

            for tag in commit["tags"]:
                ctk.CTkLabel(
                    msg_row,
                    text=f" {tag} ",
                    fg_color=SUCCESS,
                    text_color=WHITE,
                    corner_radius=4,
                    font=ctk.CTkFont(family="Inter", size=10, weight="bold"),
                ).pack(side="left", padx=(4, 0))

            for branch in commit["branches"]:
                ctk.CTkLabel(
                    msg_row,
                    text=f" {branch} ",
                    fg_color=PRIMARY,
                    text_color=WHITE,
                    corner_radius=4,
                    font=ctk.CTkFont(family="Inter", size=10),
                ).pack(side="left", padx=(4, 0))

            # Author + when
            meta_row = ctk.CTkFrame(center, fg_color="transparent")
            meta_row.pack(fill="x", anchor="w")
            Label(meta_row, text=commit["author"], size=11, color=TEXT_DIM).pack(side="left")
            Label(meta_row, text=" · ", size=11, color=TEXT_MUTED).pack(side="left")
            Label(meta_row, text=commit["when"], size=11, color=TEXT_MUTED).pack(side="left")

            # Right: short hash
            ctk.CTkLabel(
                row,
                text=commit["short"],
                fg_color=BG3,
                text_color=TEXT_MUTED,
                corner_radius=4,
                padx=8,
                pady=2,
                font=ctk.CTkFont(family="JetBrains Mono", size=11),
            ).pack(side="right", padx=(0, PAD_SM))
