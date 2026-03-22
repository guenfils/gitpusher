"""Panel – Auto-push Watch Mode."""
import threading
import time
from datetime import datetime
from tkinter import filedialog
import customtkinter as ctk
from ui.theme import *
from ui.widgets.common import Card, PrimaryButton, SecondaryButton, Label, StatusBadge, SectionHeader, LogBox
from core.git_manager import GitManager


class PanelWatch(ctk.CTkFrame):
    def __init__(self, master, app_state, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app_state = app_state
        self._git = GitManager()
        self._running = False
        self._watch_thread = None
        self._stats = {
            "checks": 0,
            "pushes": 0,
            "last_check": "",
            "last_push": "",
        }

        self._build_ui()

    def _build_ui(self):
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        # Header
        Label(scroll, text="Watch Mode", size=22, bold=True).pack(anchor="w", pady=(0, 4))
        Label(scroll, text="Monitor changes and auto-commit + push on a fixed interval",
              size=12, color=TEXT_DIM).pack(anchor="w", pady=(0, PAD))

        # Configuration card
        cfg_card = Card(scroll)
        cfg_card.pack(fill="x", pady=(0, PAD_SM))

        SectionHeader(cfg_card, "👁", "Watch Settings", "").pack(
            fill="x", padx=PAD, pady=(PAD_SM, PAD_SM)
        )

        # Row 1: Repository
        row1 = ctk.CTkFrame(cfg_card, fg_color="transparent")
        row1.pack(fill="x", padx=PAD, pady=(0, 8))
        Label(row1, text="Repository:", size=12, color=TEXT_DIM).pack(side="left", padx=(0, 8))
        self._path_var = ctk.StringVar()
        self._path_entry = ctk.CTkEntry(
            row1, textvariable=self._path_var, width=280, state="readonly",
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            placeholder_text="/path/to/repo",
            placeholder_text_color=TEXT_MUTED, corner_radius=8, height=34,
            font=ctk.CTkFont(family="Inter", size=12),
        )
        self._path_entry.pack(side="left", padx=(0, 8))
        SecondaryButton(row1, text="Browse…", width=90, height=34,
                        command=self._browse).pack(side="left")

        # Row 2: Branch + Remote
        row2 = ctk.CTkFrame(cfg_card, fg_color="transparent")
        row2.pack(fill="x", padx=PAD, pady=(0, 8))
        Label(row2, text="Branch:", size=12, color=TEXT_DIM).pack(side="left", padx=(0, 8))
        self._branch_var = ctk.StringVar(value="main")
        ctk.CTkEntry(
            row2, textvariable=self._branch_var, width=120,
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            corner_radius=8, height=34,
            font=ctk.CTkFont(family="Inter", size=12),
        ).pack(side="left", padx=(0, PAD_SM))
        Label(row2, text="Remote:", size=12, color=TEXT_DIM).pack(side="left", padx=(0, 8))
        self._remote_var = ctk.StringVar(value="origin")
        ctk.CTkEntry(
            row2, textvariable=self._remote_var, width=100,
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            corner_radius=8, height=34,
            font=ctk.CTkFont(family="Inter", size=12),
        ).pack(side="left")

        # Row 3: Interval
        row3 = ctk.CTkFrame(cfg_card, fg_color="transparent")
        row3.pack(fill="x", padx=PAD, pady=(0, 8))
        Label(row3, text="Interval:", size=12, color=TEXT_DIM).pack(side="left", padx=(0, 8))
        self._interval_var = ctk.StringVar(value="10 min")
        ctk.CTkSegmentedButton(
            row3, values=["5 min", "10 min", "15 min", "30 min", "1 hour"],
            variable=self._interval_var,
            fg_color=BG3, selected_color=PRIMARY, selected_hover_color=PRIMARY_H,
            unselected_color=BG3, unselected_hover_color=BORDER,
            text_color=TEXT,
            font=ctk.CTkFont(family="Inter", size=12),
        ).pack(side="left")

        # Row 4: Commit message
        row4 = ctk.CTkFrame(cfg_card, fg_color="transparent")
        row4.pack(fill="x", padx=PAD, pady=(0, 8))
        Label(row4, text="Commit message:", size=12, color=TEXT_DIM).pack(side="left", padx=(0, 8))
        self._msg_var = ctk.StringVar(value="Auto-commit {datetime}")
        ctk.CTkEntry(
            row4, textvariable=self._msg_var, width=300,
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            corner_radius=8, height=34,
            font=ctk.CTkFont(family="Inter", size=12),
        ).pack(side="left")

        # Row 5: Platform checkboxes
        row5 = ctk.CTkFrame(cfg_card, fg_color="transparent")
        row5.pack(fill="x", padx=PAD, pady=(0, 8))
        self._push_github = ctk.BooleanVar(value=bool(self.app_state.get("github_api")))
        self._push_gitlab = ctk.BooleanVar(value=bool(self.app_state.get("gitlab_api")))
        if self.app_state.get("github_api"):
            ctk.CTkCheckBox(
                row5, text="Push to GitHub", variable=self._push_github,
                fg_color=PRIMARY, hover_color=PRIMARY_H,
                text_color=TEXT, font=ctk.CTkFont(family="Inter", size=12),
            ).pack(side="left", padx=(0, PAD_SM))
        if self.app_state.get("gitlab_api"):
            ctk.CTkCheckBox(
                row5, text="Push to GitLab", variable=self._push_gitlab,
                fg_color=PRIMARY, hover_color=PRIMARY_H,
                text_color=TEXT, font=ctk.CTkFont(family="Inter", size=12),
            ).pack(side="left")

        # Row 6: Push after commit switch
        row6 = ctk.CTkFrame(cfg_card, fg_color="transparent")
        row6.pack(fill="x", padx=PAD, pady=(0, PAD_SM))
        self._do_push_var = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(
            row6, text="Push after commit",
            variable=self._do_push_var,
            progress_color=PRIMARY,
            button_color=WHITE,
            text_color=TEXT,
            font=ctk.CTkFont(family="Inter", size=12),
        ).pack(side="left")

        # Status card
        status_card = Card(scroll)
        status_card.pack(fill="x", pady=(0, PAD_SM))

        Label(status_card, text="Status", size=13, bold=True).pack(
            anchor="w", padx=PAD, pady=(PAD_SM, 8)
        )

        # 3 stat blocks
        stat_row = ctk.CTkFrame(status_card, fg_color="transparent")
        stat_row.pack(fill="x", padx=PAD, pady=(0, 8))
        stat_row.columnconfigure(0, weight=1)
        stat_row.columnconfigure(1, weight=1)
        stat_row.columnconfigure(2, weight=1)

        def make_stat_block(parent, col, title):
            frame = ctk.CTkFrame(parent, fg_color=BG3, corner_radius=8)
            frame.grid(row=0, column=col, sticky="ew", padx=(0 if col == 0 else 4, 0))
            Label(frame, text=title, size=10, color=TEXT_MUTED).pack(anchor="w", padx=8, pady=(6, 0))
            lbl = Label(frame, text="0", size=22, bold=True, color=TEXT)
            lbl.pack(anchor="w", padx=8, pady=(0, 6))
            return lbl

        self._checks_lbl = make_stat_block(stat_row, 0, "Checks")
        self._pushes_lbl = make_stat_block(stat_row, 1, "Auto-pushes")

        # Last activity block (string, not counter)
        last_frame = ctk.CTkFrame(stat_row, fg_color=BG3, corner_radius=8)
        last_frame.grid(row=0, column=2, sticky="ew", padx=(4, 0))
        Label(last_frame, text="Last Activity", size=10, color=TEXT_MUTED).pack(anchor="w", padx=8, pady=(6, 0))
        self._last_lbl = Label(last_frame, text="—", size=11, color=TEXT_DIM)
        self._last_lbl.pack(anchor="w", padx=8, pady=(0, 6))

        # State badge
        badge_row = ctk.CTkFrame(status_card, fg_color="transparent")
        badge_row.pack(fill="x", padx=PAD, pady=(0, PAD_SM))
        self._state_badge = StatusBadge(badge_row, status="pending", text="● Stopped")
        self._state_badge.pack(side="left")

        # Start/Stop buttons
        btn_row = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_row.pack(fill="x", pady=(0, PAD_SM))
        self._start_btn = PrimaryButton(
            btn_row, text="▶  Start Watching", width=200, height=44,
            command=self._start,
        )
        self._start_btn.pack(side="left", padx=(0, 8))
        self._stop_btn = SecondaryButton(
            btn_row, text="■  Stop", width=140, height=44,
            state="disabled", command=self._stop,
        )
        self._stop_btn.pack(side="left")

        # Log card
        log_card = Card(scroll)
        log_card.pack(fill="x", pady=(0, PAD_SM))
        Label(log_card, text="Activity Log", size=13, bold=True).pack(
            anchor="w", padx=PAD, pady=(PAD_SM, 4)
        )
        self._logbox = LogBox(log_card, height=180)
        self._logbox.pack(fill="x", padx=PAD, pady=(0, PAD_SM))

    # ---------- Browse ----------

    def _browse(self):
        folder = filedialog.askdirectory(title="Select repository to watch")
        if folder:
            self._path_entry.configure(state="normal")
            self._path_var.set(folder)
            self._path_entry.configure(state="readonly")

    # ---------- Watch control ----------

    def _start(self):
        path = self._path_var.get().strip()
        if not path:
            self._log("Error: Please select a repository path.")
            return
        if not self._git.is_git_repo(path):
            self._log("Error: Selected path is not a git repository.")
            return

        self._running = True
        self._start_btn.configure(state="disabled")
        self._stop_btn.configure(state="normal")
        self._state_badge.update_status("info", "● Watching…")
        self._log("Watch mode started.")

        self._watch_thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._watch_thread.start()

    def _stop(self):
        self._running = False
        self._start_btn.configure(state="normal")
        self._stop_btn.configure(state="disabled")
        self._state_badge.update_status("pending", "● Stopped")
        self._log("Watch mode stopped.")

    def _watch_loop(self):
        interval_map = {
            "5 min": 300,
            "10 min": 600,
            "15 min": 900,
            "30 min": 1800,
            "1 hour": 3600,
        }
        while self._running:
            interval = interval_map.get(self._interval_var.get(), 600)
            path = self._path_var.get().strip()
            branch = self._branch_var.get().strip() or "main"
            remote = self._remote_var.get().strip() or "origin"

            # Update stats
            self._stats["checks"] += 1
            self._stats["last_check"] = datetime.now().strftime("%H:%M:%S")
            self.after(0, self._update_stats)

            # Check for changes
            try:
                status = self._git.get_status(path)
            except Exception as e:
                self._log(f"Error checking status: {e}")
                status = ""

            if status:
                self._log(f"Changes detected: {status[:100]}")
                ok_add, _ = self._git.add_all(path)
                msg = self._format_message(self._msg_var.get().strip() or "Auto-commit {datetime}")
                ok_commit, out_commit = self._git.commit(path, msg)
                if ok_commit:
                    self._log(f"Committed: {msg}")
                    if self._do_push_var.get():
                        any_pushed = False
                        if self._push_github.get() and self.app_state.get("github_api"):
                            token = self.app_state.get("github_token", "")
                            env = {"GIT_ASKPASS": "echo", "GIT_USERNAME": "x-token", "GIT_PASSWORD": token} if token else None
                            ok_p, out_p = self._git.push(path, remote, branch, env=env)
                            self._log(f"GitHub: {'pushed ok' if ok_p else 'push failed'}")
                            if ok_p:
                                any_pushed = True
                        if self._push_gitlab.get() and self.app_state.get("gitlab_api"):
                            token = self.app_state.get("gitlab_token", "")
                            env = {"GIT_ASKPASS": "echo", "GIT_USERNAME": "oauth2", "GIT_PASSWORD": token} if token else None
                            ok_p, out_p = self._git.push(path, "gitlab", branch, env=env)
                            self._log(f"GitLab: {'pushed ok' if ok_p else 'push failed'}")
                            if ok_p:
                                any_pushed = True
                        if any_pushed:
                            self._stats["pushes"] += 1
                            self._stats["last_push"] = datetime.now().strftime("%H:%M:%S")
                            self.after(0, self._update_stats)
                else:
                    self._log(f"Commit result: {out_commit.strip()[:80]}")
            else:
                self._log("No changes detected.")

            # Sleep in small increments to allow stopping
            elapsed = 0
            while self._running and elapsed < interval:
                time.sleep(5)
                elapsed += 5

    def _update_stats(self):
        try:
            self._checks_lbl.configure(text=str(self._stats["checks"]))
            self._pushes_lbl.configure(text=str(self._stats["pushes"]))
            last = self._stats["last_push"] or self._stats["last_check"] or "—"
            self._last_lbl.configure(text=last)
        except Exception:
            pass

    def _format_message(self, template):
        now = datetime.now()
        msg = template.replace("{datetime}", now.strftime("%Y-%m-%d %H:%M"))
        msg = msg.replace("{date}", now.strftime("%Y-%m-%d"))
        msg = msg.replace("{time}", now.strftime("%H:%M"))
        return msg

    def _log(self, msg):
        self.after(0, lambda: self._logbox.append(
            f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
        ))
