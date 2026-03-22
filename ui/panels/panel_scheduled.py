"""Panel – Scheduled Push."""
import threading
import time
from datetime import datetime, timedelta
from tkinter import filedialog
import customtkinter as ctk
from ui.theme import *
from ui.widgets.common import Card, PrimaryButton, SecondaryButton, Label, StatusBadge, SectionHeader, LogBox
from core.git_manager import GitManager


class PanelScheduled(ctk.CTkFrame):
    def __init__(self, master, app_state, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app_state = app_state
        self._git = GitManager()
        self._jobs = []
        self._next_job_id = 1
        self._scheduler_running = False

        self._build_ui()

    def _build_ui(self):
        # Scrollable container
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        # Header
        Label(scroll, text="Scheduled Push", size=22, bold=True).pack(anchor="w", pady=(0, 4))
        Label(scroll, text="Schedule automatic commits and pushes at specific times",
              size=12, color=TEXT_DIM).pack(anchor="w", pady=(0, PAD))

        # New Schedule card
        new_card = Card(scroll)
        new_card.pack(fill="x", pady=(0, PAD_SM))

        SectionHeader(new_card, "🕐", "New Schedule", "").pack(
            fill="x", padx=PAD, pady=(PAD_SM, PAD_SM)
        )

        # Row 1: Repository path
        row1 = ctk.CTkFrame(new_card, fg_color="transparent")
        row1.pack(fill="x", padx=PAD, pady=(0, 8))
        Label(row1, text="Repository:", size=12, color=TEXT_DIM).pack(side="left", padx=(0, 8))
        self._path_var = ctk.StringVar()
        ctk.CTkEntry(
            row1, textvariable=self._path_var, width=260, state="readonly",
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            placeholder_text="/path/to/repo",
            placeholder_text_color=TEXT_MUTED, corner_radius=8, height=34,
            font=ctk.CTkFont(family="Inter", size=12),
        ).pack(side="left", padx=(0, 8))
        SecondaryButton(row1, text="Browse…", width=80, height=34,
                        command=self._browse).pack(side="left")

        # Row 2: Branch + Platforms
        row2 = ctk.CTkFrame(new_card, fg_color="transparent")
        row2.pack(fill="x", padx=PAD, pady=(0, 8))
        Label(row2, text="Branch:", size=12, color=TEXT_DIM).pack(side="left", padx=(0, 8))
        self._branch_var = ctk.StringVar(value="main")
        ctk.CTkEntry(
            row2, textvariable=self._branch_var, width=120,
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            corner_radius=8, height=34,
            font=ctk.CTkFont(family="Inter", size=12),
        ).pack(side="left", padx=(0, PAD_SM))

        Label(row2, text="Platforms:", size=12, color=TEXT_DIM).pack(side="left", padx=(0, 8))
        self._push_github = ctk.BooleanVar(value=bool(self.app_state.get("github_api")))
        self._push_gitlab = ctk.BooleanVar(value=bool(self.app_state.get("gitlab_api")))
        if self.app_state.get("github_api"):
            ctk.CTkCheckBox(
                row2, text="GitHub", variable=self._push_github,
                fg_color=PRIMARY, hover_color=PRIMARY_H,
                text_color=TEXT, font=ctk.CTkFont(family="Inter", size=12),
            ).pack(side="left", padx=(0, 8))
        if self.app_state.get("gitlab_api"):
            ctk.CTkCheckBox(
                row2, text="GitLab", variable=self._push_gitlab,
                fg_color=PRIMARY, hover_color=PRIMARY_H,
                text_color=TEXT, font=ctk.CTkFont(family="Inter", size=12),
            ).pack(side="left")

        # Row 3: Commit message
        row3 = ctk.CTkFrame(new_card, fg_color="transparent")
        row3.pack(fill="x", padx=PAD, pady=(0, 8))
        Label(row3, text="Commit message:", size=12, color=TEXT_DIM).pack(side="left", padx=(0, 8))
        self._msg_var = ctk.StringVar(value="Scheduled commit {datetime}")
        ctk.CTkEntry(
            row3, textvariable=self._msg_var, width=280,
            placeholder_text="Scheduled commit {datetime}",
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            placeholder_text_color=TEXT_MUTED, corner_radius=8, height=34,
            font=ctk.CTkFont(family="Inter", size=12),
        ).pack(side="left")

        # Row 4: Date/Time picker
        row4 = ctk.CTkFrame(new_card, fg_color="transparent")
        row4.pack(fill="x", padx=PAD, pady=(0, 8))
        Label(row4, text="Date:", size=12, color=TEXT_DIM).pack(side="left", padx=(0, 8))
        today = datetime.now().strftime("%Y-%m-%d")
        self._date_var = ctk.StringVar(value=today)
        ctk.CTkEntry(
            row4, textvariable=self._date_var, width=110,
            placeholder_text="2025-12-31",
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            placeholder_text_color=TEXT_MUTED, corner_radius=8, height=34,
            font=ctk.CTkFont(family="Inter", size=12),
        ).pack(side="left", padx=(0, PAD_SM))
        Label(row4, text="Time:", size=12, color=TEXT_DIM).pack(side="left", padx=(0, 8))
        self._hour_var = ctk.StringVar(value=datetime.now().strftime("%H"))
        ctk.CTkEntry(
            row4, textvariable=self._hour_var, width=50,
            placeholder_text="14",
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            placeholder_text_color=TEXT_MUTED, corner_radius=8, height=34,
            font=ctk.CTkFont(family="Inter", size=12),
        ).pack(side="left", padx=(0, 4))
        Label(row4, text=":", size=12, color=TEXT_DIM).pack(side="left", padx=(0, 4))
        self._minute_var = ctk.StringVar(value="00")
        ctk.CTkEntry(
            row4, textvariable=self._minute_var, width=50,
            placeholder_text="30",
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            placeholder_text_color=TEXT_MUTED, corner_radius=8, height=34,
            font=ctk.CTkFont(family="Inter", size=12),
        ).pack(side="left")

        # Row 5: Repeat
        row5 = ctk.CTkFrame(new_card, fg_color="transparent")
        row5.pack(fill="x", padx=PAD, pady=(0, PAD_SM))
        Label(row5, text="Repeat:", size=12, color=TEXT_DIM).pack(side="left", padx=(0, 8))
        self._repeat_var = ctk.StringVar(value="Once")
        ctk.CTkSegmentedButton(
            row5, values=["Once", "Hourly", "Daily", "Weekly"],
            variable=self._repeat_var,
            fg_color=BG3, selected_color=PRIMARY, selected_hover_color=PRIMARY_H,
            unselected_color=BG3, unselected_hover_color=BORDER,
            text_color=TEXT,
            font=ctk.CTkFont(family="Inter", size=12),
        ).pack(side="left")

        # Schedule button
        PrimaryButton(
            new_card, text="Schedule Push", height=42,
            command=self._schedule,
        ).pack(fill="x", padx=PAD, pady=(0, PAD_SM))

        # Scheduled jobs card
        jobs_card = Card(scroll)
        jobs_card.pack(fill="x", pady=(0, PAD_SM))

        SectionHeader(jobs_card, "📋", "Scheduled Jobs", "").pack(
            fill="x", padx=PAD, pady=(PAD_SM, PAD_SM)
        )

        self._jobs_scroll = ctk.CTkScrollableFrame(
            jobs_card, fg_color="transparent", height=260
        )
        self._jobs_scroll.pack(fill="x", padx=PAD, pady=(0, PAD_SM))

        self._no_jobs_label = Label(
            self._jobs_scroll, text="No scheduled jobs yet.",
            size=12, color=TEXT_MUTED
        )
        self._no_jobs_label.pack(anchor="w", pady=8)

        # Log card
        log_card = Card(scroll)
        log_card.pack(fill="x", pady=(0, PAD_SM))
        Label(log_card, text="Activity Log", size=13, bold=True).pack(
            anchor="w", padx=PAD, pady=(PAD_SM, 4)
        )
        self._logbox = LogBox(log_card, height=120)
        self._logbox.pack(fill="x", padx=PAD, pady=(0, PAD_SM))

    # ---------- Actions ----------

    def _browse(self):
        folder = filedialog.askdirectory(title="Select repository")
        if folder:
            self._path_var.configure(state="normal")
            self._path_var.set(folder)
            # Re-lock the entry if it exists
            try:
                self._path_var.configure(state="readonly")
            except Exception:
                pass

    def _schedule(self):
        path = self._path_var.get().strip()
        if not path:
            self._log("Error: Please select a repository path.")
            return

        date_str = self._date_var.get().strip()
        hour_str = self._hour_var.get().strip()
        minute_str = self._minute_var.get().strip()

        try:
            y, m, d = [int(x) for x in date_str.split("-")]
            hour = int(hour_str)
            minute = int(minute_str)
            target_dt = datetime(y, m, d, hour, minute)
        except Exception:
            self._log("Error: Invalid date/time format. Use YYYY-MM-DD and HH MM.")
            return

        if target_dt < datetime.now():
            self._log("Error: Scheduled time is in the past.")
            return

        repeat = self._repeat_var.get().lower()
        if repeat not in ("once", "hourly", "daily", "weekly"):
            repeat = "once"

        job = {
            "id": self._next_job_id,
            "path": path,
            "branch": self._branch_var.get().strip() or "main",
            "commit_msg": self._msg_var.get().strip() or "Scheduled commit {datetime}",
            "target_dt": target_dt,
            "repeat": repeat,
            "status": "pending",
            "last_run": "",
        }
        self._next_job_id += 1
        self._jobs.append(job)
        self._render_jobs()
        self._log(f"Scheduled job #{job['id']} for {target_dt.strftime('%Y-%m-%d %H:%M')} [{repeat}]")
        self._start_scheduler()

    def _start_scheduler(self):
        if self._scheduler_running:
            return
        self._scheduler_running = True

        def _scheduler_loop():
            while self._scheduler_running:
                now = datetime.now()
                for job in list(self._jobs):
                    if job["status"] == "pending" and now >= job["target_dt"]:
                        self.after(0, lambda j=job: self._run_job(j))
                time.sleep(30)

        t = threading.Thread(target=_scheduler_loop, daemon=True)
        t.start()

    def _run_job(self, job):
        if job["status"] != "pending":
            return
        job["status"] = "running"
        self._render_jobs()
        path = job["path"]
        branch = job["branch"]
        msg_tpl = job["commit_msg"]

        def _do():
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            msg = msg_tpl.replace("{datetime}", now_str)
            msg = msg.replace("{date}", datetime.now().strftime("%Y-%m-%d"))
            msg = msg.replace("{branch}", branch)

            self._log(f"Running job #{job['id']}: {msg}")
            ok_add, _ = self._git.add_all(path)
            ok_commit, out_commit = self._git.commit(path, msg)

            errors = []
            if ok_commit:
                self._log(f"Committed: {out_commit.strip()[:80] or 'ok'}")
                # Push GitHub
                if self._push_github.get() and self.app_state.get("github_api"):
                    token = self.app_state.get("github_token", "")
                    env = {"GIT_ASKPASS": "echo", "GIT_USERNAME": "x-token", "GIT_PASSWORD": token} if token else None
                    ok_p, out_p = self._git.push(path, "origin", branch, env=env)
                    self._log(f"GitHub push: {'ok' if ok_p else 'failed'} {out_p.strip()[:60]}")
                    if not ok_p:
                        errors.append("GitHub")
                # Push GitLab
                if self._push_gitlab.get() and self.app_state.get("gitlab_api"):
                    token = self.app_state.get("gitlab_token", "")
                    env = {"GIT_ASKPASS": "echo", "GIT_USERNAME": "oauth2", "GIT_PASSWORD": token} if token else None
                    ok_p, out_p = self._git.push(path, "gitlab", branch, env=env)
                    self._log(f"GitLab push: {'ok' if ok_p else 'failed'} {out_p.strip()[:60]}")
                    if not ok_p:
                        errors.append("GitLab")
                new_status = "error" if errors else "done"
            else:
                self._log(f"Commit failed: {out_commit.strip()[:80]}")
                new_status = "error"

            job["status"] = new_status
            job["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Handle repeat
            if job["repeat"] != "once" and new_status == "done":
                repeat = job["repeat"]
                if repeat == "hourly":
                    next_dt = job["target_dt"] + timedelta(hours=1)
                elif repeat == "daily":
                    next_dt = job["target_dt"] + timedelta(days=1)
                elif repeat == "weekly":
                    next_dt = job["target_dt"] + timedelta(weeks=1)
                else:
                    next_dt = None

                if next_dt:
                    new_job = {
                        "id": self._next_job_id,
                        "path": job["path"],
                        "branch": job["branch"],
                        "commit_msg": job["commit_msg"],
                        "target_dt": next_dt,
                        "repeat": job["repeat"],
                        "status": "pending",
                        "last_run": "",
                    }
                    self._next_job_id += 1
                    self._jobs.append(new_job)
                    self._log(f"Next scheduled job #{new_job['id']} at {next_dt.strftime('%Y-%m-%d %H:%M')}")

            self.after(0, self._render_jobs)

        threading.Thread(target=_do, daemon=True).start()

    def _render_jobs(self):
        for widget in self._jobs_scroll.winfo_children():
            widget.destroy()

        if not self._jobs:
            Label(
                self._jobs_scroll, text="No scheduled jobs yet.",
                size=12, color=TEXT_MUTED
            ).pack(anchor="w", pady=8)
            return

        status_map = {
            "pending": "info",
            "running": "info",
            "done": "ok",
            "error": "error",
            "cancelled": "pending",
        }

        for job in reversed(self._jobs):
            bg = BG3 if job["status"] == "pending" else BG2
            row = ctk.CTkFrame(self._jobs_scroll, fg_color=bg, corner_radius=8)
            row.pack(fill="x", pady=3)

            # Status badge
            badge_status = status_map.get(job["status"], "pending")
            StatusBadge(row, status=badge_status, text=job["status"].upper()).pack(
                side="left", padx=(8, 8), pady=6
            )

            # Center info
            center = ctk.CTkFrame(row, fg_color="transparent")
            center.pack(side="left", fill="x", expand=True, pady=6)

            folder_name = job["path"].split("/")[-1] or job["path"]
            Label(center, text=folder_name, size=12, bold=True).pack(anchor="w")

            detail = f"Branch: {job['branch']}  |  {job['target_dt'].strftime('%Y-%m-%d %H:%M')}  |  {job['repeat']}"
            if job["last_run"]:
                detail += f"  |  Last run: {job['last_run']}"
            Label(center, text=detail, size=10, color=TEXT_DIM).pack(anchor="w")

            # Cancel button (only for pending/running)
            if job["status"] in ("pending", "running"):
                def _cancel(j=job):
                    j["status"] = "cancelled"
                    self._render_jobs()
                    self._log(f"Job #{j['id']} cancelled.")

                SecondaryButton(
                    row, text="Cancel", width=70, height=28,
                    fg_color=ERROR, hover_color="#DC2626", text_color=WHITE,
                    command=_cancel,
                ).pack(side="right", padx=8, pady=6)

    def _log(self, msg):
        self.after(0, lambda: self._logbox.append(
            f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
        ))
