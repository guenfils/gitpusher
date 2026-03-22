"""Panel – Repository Statistics."""
import threading
from datetime import datetime
from tkinter import filedialog
import customtkinter as ctk
from ui.theme import *
from ui.widgets.common import Card, PrimaryButton, SecondaryButton, Label, StatusBadge, SectionHeader
from core.git_manager import GitManager

AVATAR_COLORS = [PRIMARY, SUCCESS, WARNING, ERROR, "#06B6D4", "#8B5CF6", "#F97316", "#EC4899"]


class PanelStats(ctk.CTkFrame):
    def __init__(self, master, app_state, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app_state = app_state
        self._git = GitManager()
        self._path_var = ctk.StringVar()
        self._stat_labels = {}
        self._chart_frame = None
        self._contrib_frame = None
        self._files_frame = None
        self._timeline_frame = None
        self._analyze_btn = None

        self._build_ui()

    def _build_ui(self):
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True)
        self._scroll = scroll

        # Header
        Label(scroll, text="Repository Statistics", size=22, bold=True).pack(anchor="w", pady=(0, 4))
        Label(scroll, text="Insights and metrics for your git repository",
              size=12, color=TEXT_DIM).pack(anchor="w", pady=(0, PAD))

        # Repo selector card
        sel_card = Card(scroll)
        sel_card.pack(fill="x", pady=(0, PAD_SM))
        sel_row = ctk.CTkFrame(sel_card, fg_color="transparent")
        sel_row.pack(fill="x", padx=PAD, pady=PAD_SM)

        self._path_entry = ctk.CTkEntry(
            sel_row, textvariable=self._path_var, width=320, state="readonly",
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            placeholder_text="/path/to/repo",
            placeholder_text_color=TEXT_MUTED, corner_radius=8, height=36,
            font=ctk.CTkFont(family="Inter", size=12),
        )
        self._path_entry.pack(side="left", padx=(0, 8))
        SecondaryButton(sel_row, text="Browse…", width=100, height=36,
                        command=self._browse).pack(side="left", padx=(0, 8))
        self._analyze_btn = PrimaryButton(sel_row, text="Analyze", width=120, height=36,
                                          command=self._analyze)
        self._analyze_btn.pack(side="left")

        # Summary stats row (5 cards)
        self._summary_row = ctk.CTkFrame(scroll, fg_color="transparent")
        self._summary_row.pack(fill="x", pady=(0, PAD_SM))
        for col in range(5):
            self._summary_row.columnconfigure(col, weight=1)

        stat_defs = [
            ("commits", "Commits"),
            ("contributors", "Contributors"),
            ("branches", "Branches"),
            ("tags", "Tags"),
            ("files", "Active Files"),
        ]
        for col, (key, label) in enumerate(stat_defs):
            frame = ctk.CTkFrame(self._summary_row, fg_color=BG2, corner_radius=10)
            frame.grid(row=0, column=col, sticky="ew", padx=(0 if col == 0 else 4, 0), pady=0)
            val_lbl = Label(frame, text="—", size=24, bold=True, color=TEXT)
            val_lbl.pack(anchor="w", padx=PAD_SM, pady=(PAD_SM, 0))
            Label(frame, text=label, size=10, color=TEXT_MUTED).pack(
                anchor="w", padx=PAD_SM, pady=(0, PAD_SM)
            )
            self._stat_labels[key] = val_lbl

        # Two-column section
        two_col = ctk.CTkFrame(scroll, fg_color="transparent")
        two_col.pack(fill="x", pady=(0, PAD_SM))
        two_col.columnconfigure(0, weight=1)
        two_col.columnconfigure(1, weight=1)

        # Col 0: Activity chart card
        self._chart_card = Card(two_col)
        self._chart_card.grid(row=0, column=0, sticky="nsew", padx=(0, PAD_SM // 2))

        SectionHeader(self._chart_card, "📈", "Commits by Month", "(last 12 months)").pack(
            fill="x", padx=PAD, pady=(PAD_SM, PAD_SM)
        )
        self._chart_frame = ctk.CTkFrame(self._chart_card, fg_color="transparent")
        self._chart_frame.pack(fill="x", padx=PAD, pady=(0, PAD_SM))
        Label(self._chart_frame, text="No commit data.", size=11, color=TEXT_MUTED).pack(anchor="w")

        # Col 1: Top contributors card
        self._contrib_card = Card(two_col)
        self._contrib_card.grid(row=0, column=1, sticky="nsew", padx=(PAD_SM // 2, 0))

        SectionHeader(self._contrib_card, "👤", "Top Contributors", "").pack(
            fill="x", padx=PAD, pady=(PAD_SM, PAD_SM)
        )
        self._contrib_frame = ctk.CTkFrame(self._contrib_card, fg_color="transparent")
        self._contrib_frame.pack(fill="x", padx=PAD, pady=(0, PAD_SM))
        Label(self._contrib_frame, text="No data.", size=11, color=TEXT_MUTED).pack(anchor="w")

        # Most changed files card
        self._files_card = Card(scroll)
        self._files_card.pack(fill="x", pady=(0, PAD_SM))
        SectionHeader(self._files_card, "📁", "Most Active Files", "(by number of commits)").pack(
            fill="x", padx=PAD, pady=(PAD_SM, PAD_SM)
        )
        self._files_frame = ctk.CTkFrame(self._files_card, fg_color="transparent")
        self._files_frame.pack(fill="x", padx=PAD, pady=(0, PAD_SM))
        Label(self._files_frame, text="No data.", size=11, color=TEXT_MUTED).pack(anchor="w")

        # Timeline card
        self._timeline_card = Card(scroll)
        self._timeline_card.pack(fill="x", pady=(0, PAD_SM))
        Label(self._timeline_card, text="Timeline", size=13, bold=True).pack(
            anchor="w", padx=PAD, pady=(PAD_SM, 4)
        )
        self._timeline_frame = ctk.CTkFrame(self._timeline_card, fg_color="transparent")
        self._timeline_frame.pack(fill="x", padx=PAD, pady=(0, PAD_SM))
        Label(self._timeline_frame, text="Select a repository and click Analyze.",
              size=11, color=TEXT_MUTED).pack(anchor="w")

    # ---------- Browse ----------

    def _browse(self):
        folder = filedialog.askdirectory(title="Select repository")
        if folder:
            self._path_entry.configure(state="normal")
            self._path_var.set(folder)
            self._path_entry.configure(state="readonly")

    # ---------- Analyze ----------

    def _analyze(self):
        path = self._path_var.get().strip()
        if not path:
            return
        if not self._git.is_git_repo(path):
            self._stat_labels["commits"].configure(text="Not a git repo")
            return

        if self._analyze_btn:
            self._analyze_btn.configure(text="Analyzing…", state="disabled")

        def _do():
            total = self._git.get_total_commits(path)
            contributors = self._git.get_contributor_stats(path)
            by_month = self._git.get_commits_by_month(path)
            hot_files = self._git.get_most_changed_files(path)
            branches = self._git.get_branches(path)
            tags = self._git.get_tags(path)
            first_date = self._git.get_first_commit_date(path)
            last = self._git.get_last_commit(path)
            self.after(0, lambda: self._render(
                total, contributors, by_month, hot_files, branches, tags, first_date, last
            ))

        threading.Thread(target=_do, daemon=True).start()

    def _render(self, total, contributors, by_month, hot_files, branches, tags, first_date, last):
        # Re-enable analyze button
        if self._analyze_btn:
            self._analyze_btn.configure(text="Analyze", state="normal")

        # Summary stats
        self._stat_labels["commits"].configure(text=str(total))
        self._stat_labels["contributors"].configure(text=str(len(contributors)))
        self._stat_labels["branches"].configure(text=str(len(branches)))
        self._stat_labels["tags"].configure(text=str(len(tags)))
        self._stat_labels["files"].configure(text=str(len(hot_files)))

        # Chart: Commits by month
        for w in self._chart_frame.winfo_children():
            w.destroy()

        if by_month:
            max_count = max(by_month.values()) if by_month.values() else 1
            max_count = max_count if max_count > 0 else 1
            for month_key, count in by_month.items():
                # Format month label: "Jan", "Feb", etc.
                try:
                    dt = datetime.strptime(month_key, "%Y-%m")
                    month_label = dt.strftime("%b")
                except Exception:
                    month_label = month_key[-2:]

                row = ctk.CTkFrame(self._chart_frame, fg_color="transparent")
                row.pack(fill="x", pady=1)

                ctk.CTkLabel(
                    row, text=month_label, width=35, anchor="e",
                    font=ctk.CTkFont(family="Inter", size=10),
                    text_color=TEXT_DIM,
                ).pack(side="left", padx=(0, 6))

                bar_val = count / max_count if max_count > 0 else 0
                bar = ctk.CTkProgressBar(
                    row, width=180, height=12,
                    fg_color=BG3, progress_color=PRIMARY, corner_radius=4,
                )
                bar.set(bar_val)
                bar.pack(side="left", padx=(0, 6))

                ctk.CTkLabel(
                    row, text=str(count), width=30, anchor="w",
                    font=ctk.CTkFont(family="Inter", size=10),
                    text_color=TEXT_DIM,
                ).pack(side="left")
        else:
            Label(self._chart_frame, text="No commit data.", size=11, color=TEXT_MUTED).pack(anchor="w")

        # Contributors
        for w in self._contrib_frame.winfo_children():
            w.destroy()

        if contributors:
            for idx, c in enumerate(contributors[:8]):
                row = ctk.CTkFrame(self._contrib_frame, fg_color="transparent")
                row.pack(fill="x", pady=2)

                color = AVATAR_COLORS[idx % len(AVATAR_COLORS)]
                initial = c["name"][0].upper() if c["name"] else "?"
                ctk.CTkLabel(
                    row, text=initial, width=24, height=24,
                    fg_color=color, text_color=WHITE,
                    corner_radius=12,
                    font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
                ).pack(side="left", padx=(0, 8))

                ctk.CTkLabel(
                    row, text=c["name"],
                    font=ctk.CTkFont(family="Inter", size=12),
                    text_color=TEXT, anchor="w",
                ).pack(side="left", fill="x", expand=True)

                StatusBadge(row, status="ok", text=str(c["count"])).pack(side="right")
        else:
            Label(self._contrib_frame, text="No data.", size=11, color=TEXT_MUTED).pack(anchor="w")

        # Most changed files
        for w in self._files_frame.winfo_children():
            w.destroy()

        if hot_files:
            max_fc = hot_files[0]["count"] if hot_files else 1
            max_fc = max_fc if max_fc > 0 else 1
            for item in hot_files:
                filepath = item["file"]
                count = item["count"]
                # Truncate from left
                if len(filepath) > 55:
                    filepath = "…" + filepath[-54:]

                row = ctk.CTkFrame(self._files_frame, fg_color="transparent")
                row.pack(fill="x", pady=1)

                ctk.CTkLabel(
                    row, text=filepath, width=260, anchor="w",
                    font=ctk.CTkFont(family="JetBrains Mono", size=10),
                    text_color=TEXT_DIM,
                ).pack(side="left", padx=(0, 6))

                bar_val = count / max_fc
                bar = ctk.CTkProgressBar(
                    row, height=10,
                    fg_color=BG3, progress_color=SUCCESS, corner_radius=4,
                )
                bar.set(bar_val)
                bar.pack(side="left", fill="x", expand=True, padx=(0, 6))

                ctk.CTkLabel(
                    row, text=str(count), width=35, anchor="e",
                    font=ctk.CTkFont(family="Inter", size=10),
                    text_color=TEXT_DIM,
                ).pack(side="right")
        else:
            Label(self._files_frame, text="No data.", size=11, color=TEXT_MUTED).pack(anchor="w")

        # Timeline
        for w in self._timeline_frame.winfo_children():
            w.destroy()

        tl_row = ctk.CTkFrame(self._timeline_frame, fg_color="transparent")
        tl_row.pack(fill="x")

        first_str = first_date or "unknown"
        last_str = last["when"] if last else "unknown"
        age_str = ""
        if first_date:
            try:
                fd = datetime.strptime(first_date, "%Y-%m-%d")
                delta = datetime.now() - fd
                years = delta.days // 365
                months = (delta.days % 365) // 30
                parts = []
                if years:
                    parts.append(f"{years} year{'s' if years != 1 else ''}")
                if months:
                    parts.append(f"{months} month{'s' if months != 1 else ''}")
                age_str = ", ".join(parts) if parts else "< 1 month"
            except Exception:
                age_str = ""

        Label(tl_row, text=f"First commit: {first_str}", size=11, color=TEXT_DIM).pack(
            side="left", padx=(0, PAD)
        )
        Label(tl_row, text=f"Latest commit: {last_str}", size=11, color=TEXT_DIM).pack(
            side="left", padx=(0, PAD)
        )
        if age_str:
            Label(tl_row, text=f"Repo age: {age_str}", size=11, color=TEXT_DIM).pack(side="left")
