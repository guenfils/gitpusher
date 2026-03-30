"""Panel – Test & Debugging workspace fed by NovaDeploy incidents."""
import os
import threading
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from core.config_manager import CONFIG_PATH, ConfigManager
from core.test_debugging import TestDebugSystem
from ui.theme import *
from ui.widgets.common import (
    Card,
    Label,
    LogBox,
    PrimaryButton,
    SecondaryButton,
    SectionHeader,
    StatusBadge,
)


class PanelTestDebugging(ctk.CTkFrame):
    def __init__(self, master, app_state, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app_state = app_state
        self.cfg = ConfigManager()
        self._system = TestDebugSystem()
        self._incident_buttons = {}
        self._current_incident = None
        self._current_analysis = None
        self._current_plan = []
        self._current_repair_history = None
        self._current_repo_state = None
        self._run_thread = None
        self._stop_event = None
        self._repair_thread = None
        self._commit_thread = None

        self._build_ui()
        self._apply_saved_settings()
        self._refresh_incidents()

    def _build_ui(self):
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True)
        self._scroll = scroll

        Label(scroll, text="Test & Debugging", size=22, bold=True).pack(anchor="w", pady=(0, 4))
        Label(
            scroll,
            text="Load failed NovaDeploy incidents, resolve the local repo, analyze the stack, and run deterministic checks before any repair loop.",
            size=12,
            color=TEXT_DIM,
        ).pack(anchor="w", pady=(0, PAD))

        source_card = Card(scroll)
        source_card.pack(fill="x", pady=(0, PAD_SM))
        SectionHeader(source_card, "T", "Incident Source", "").pack(
            fill="x", padx=PAD, pady=(PAD_SM, PAD_SM)
        )

        source_row = ctk.CTkFrame(source_card, fg_color="transparent")
        source_row.pack(fill="x", padx=PAD, pady=(0, PAD_SM))
        self._incident_root_var = ctk.StringVar()
        self._incident_root_entry = ctk.CTkEntry(
            source_row,
            textvariable=self._incident_root_var,
            width=420,
            state="readonly",
            fg_color=BG3,
            border_color=BORDER,
            text_color=TEXT,
            corner_radius=8,
            height=36,
            font=ctk.CTkFont(family="Inter", size=12),
        )
        self._incident_root_entry.pack(side="left", padx=(0, 8))
        SecondaryButton(source_row, text="Browse…", width=100, height=36, command=self._browse_incident_root).pack(
            side="left", padx=(0, 8)
        )
        SecondaryButton(source_row, text="Refresh", width=90, height=36, command=self._refresh_incidents).pack(
            side="left"
        )

        self._incident_count_lbl = Label(source_card, text="", size=11, color=TEXT_DIM)
        self._incident_count_lbl.pack(anchor="w", padx=PAD, pady=(0, PAD_SM))

        inbox_card = Card(scroll)
        inbox_card.pack(fill="x", pady=(0, PAD_SM))
        inbox_header = ctk.CTkFrame(inbox_card, fg_color="transparent")
        inbox_header.pack(fill="x", padx=PAD, pady=(PAD_SM, 6))
        Label(inbox_header, text="Incident Inbox", size=13, bold=True).pack(side="left")
        SecondaryButton(inbox_header, text="Clear Logs", width=90, height=30, command=self._clear_logs).pack(
            side="right"
        )
        self._incident_list = ctk.CTkScrollableFrame(
            inbox_card,
            fg_color=BG,
            height=190,
            scrollbar_button_color=BG3,
            scrollbar_button_hover_color=BORDER,
        )
        self._incident_list.pack(fill="x", padx=PAD, pady=(0, PAD_SM))

        detail_card = Card(scroll)
        detail_card.pack(fill="x", pady=(0, PAD_SM))
        SectionHeader(detail_card, "I", "Selected Incident", "").pack(
            fill="x", padx=PAD, pady=(PAD_SM, PAD_SM)
        )
        self._incident_detail = LogBox(detail_card, height=130)
        self._incident_detail.pack(fill="x", padx=PAD, pady=(0, 8))

        detail_btn_row = ctk.CTkFrame(detail_card, fg_color="transparent")
        detail_btn_row.pack(fill="x", padx=PAD, pady=(0, PAD_SM))
        SecondaryButton(detail_btn_row, text="Open Incident Folder", width=150, height=34, command=self._open_incident_folder).pack(
            side="left", padx=(0, 8)
        )
        SecondaryButton(detail_btn_row, text="Open Exported Log", width=140, height=34, command=self._open_incident_log).pack(
            side="left"
        )

        repo_card = Card(scroll)
        repo_card.pack(fill="x", pady=(0, PAD_SM))
        SectionHeader(repo_card, "R", "Repository Resolver", "").pack(
            fill="x", padx=PAD, pady=(PAD_SM, PAD_SM)
        )

        repo_row = ctk.CTkFrame(repo_card, fg_color="transparent")
        repo_row.pack(fill="x", padx=PAD, pady=(0, 8))
        self._repo_path_var = ctk.StringVar()
        self._repo_entry = ctk.CTkEntry(
            repo_row,
            textvariable=self._repo_path_var,
            width=420,
            state="readonly",
            fg_color=BG3,
            border_color=BORDER,
            text_color=TEXT,
            corner_radius=8,
            height=36,
            font=ctk.CTkFont(family="Inter", size=12),
        )
        self._repo_entry.pack(side="left", padx=(0, 8))
        SecondaryButton(repo_row, text="Browse…", width=100, height=36, command=self._browse_repo).pack(
            side="left", padx=(0, 8)
        )
        SecondaryButton(repo_row, text="Save Map", width=100, height=36, command=self._save_repo_map).pack(
            side="left", padx=(0, 8)
        )
        SecondaryButton(repo_row, text="Open Repo", width=90, height=36, command=self._open_repo).pack(
            side="left"
        )

        self._repo_hint_lbl = Label(repo_card, text="", size=11, color=TEXT_DIM)
        self._repo_hint_lbl.pack(anchor="w", padx=PAD, pady=(0, PAD_SM))

        analysis_card = Card(scroll)
        analysis_card.pack(fill="x", pady=(0, PAD_SM))
        analysis_header = ctk.CTkFrame(analysis_card, fg_color="transparent")
        analysis_header.pack(fill="x", padx=PAD, pady=(PAD_SM, 6))
        Label(analysis_header, text="Repository Analysis", size=13, bold=True).pack(side="left")
        self._analyze_btn = PrimaryButton(
            analysis_header,
            text="Analyze Repo",
            width=120,
            height=34,
            command=self._analyze_repo,
        )
        self._analyze_btn.pack(side="right")
        self._analysis_box = LogBox(analysis_card, height=150)
        self._analysis_box.pack(fill="x", padx=PAD, pady=(0, PAD_SM))

        plan_card = Card(scroll)
        plan_card.pack(fill="x", pady=(0, PAD_SM))
        plan_header = ctk.CTkFrame(plan_card, fg_color="transparent")
        plan_header.pack(fill="x", padx=PAD, pady=(PAD_SM, 6))
        Label(plan_header, text="Execution Plan", size=13, bold=True).pack(side="left")
        self._run_btn = PrimaryButton(
            plan_header,
            text="Run Plan",
            width=110,
            height=34,
            command=self._run_plan,
        )
        self._run_btn.pack(side="right", padx=(8, 0))
        self._stop_btn = SecondaryButton(
            plan_header,
            text="Stop",
            width=80,
            height=34,
            state="disabled",
            command=self._stop_run,
        )
        self._stop_btn.pack(side="right")
        self._plan_box = LogBox(plan_card, height=160)
        self._plan_box.pack(fill="x", padx=PAD, pady=(0, PAD_SM))

        repair_card = Card(scroll)
        repair_card.pack(fill="x", pady=(0, PAD_SM))
        SectionHeader(repair_card, "L", "Repair Loop", "").pack(
            fill="x", padx=PAD, pady=(PAD_SM, PAD_SM)
        )
        Label(
            repair_card,
            text="A default Codex repair command is preloaded. Override it if needed, or clear it to keep the loop in handoff-only mode.",
            size=11,
            color=TEXT_DIM,
        ).pack(anchor="w", padx=PAD, pady=(0, 6))

        repair_cmd_row = ctk.CTkFrame(repair_card, fg_color="transparent")
        repair_cmd_row.pack(fill="x", padx=PAD, pady=(0, 8))
        self._repair_cmd_var = ctk.StringVar()
        self._repair_cmd_entry = ctk.CTkEntry(
            repair_cmd_row,
            textvariable=self._repair_cmd_var,
            width=520,
            fg_color=BG3,
            border_color=BORDER,
            text_color=TEXT,
            corner_radius=8,
            height=36,
            font=ctk.CTkFont(family="Inter", size=12),
            placeholder_text="python3 .../repair_agent.py --repo {repo_path} --context {context_file}",
            placeholder_text_color=TEXT_MUTED,
        )
        self._repair_cmd_entry.pack(side="left", padx=(0, 8))
        SecondaryButton(
            repair_cmd_row, text="Default", width=90, height=36, command=self._reset_default_repair_command
        ).pack(side="left", padx=(0, 8))
        SecondaryButton(
            repair_cmd_row, text="Save", width=80, height=36, command=self._save_repair_settings
        ).pack(side="left")

        repair_opts_row = ctk.CTkFrame(repair_card, fg_color="transparent")
        repair_opts_row.pack(fill="x", padx=PAD, pady=(0, PAD_SM))
        Label(repair_opts_row, text="Max attempts:", size=12, color=TEXT_DIM).pack(side="left", padx=(0, 8))
        self._repair_attempts_var = ctk.StringVar(value="2")
        ctk.CTkSegmentedButton(
            repair_opts_row,
            values=["1", "2", "3"],
            variable=self._repair_attempts_var,
            fg_color=BG3,
            selected_color=PRIMARY,
            selected_hover_color=PRIMARY_H,
            unselected_color=BG3,
            unselected_hover_color=BORDER,
            text_color=TEXT,
            font=ctk.CTkFont(family="Inter", size=12),
        ).pack(side="left", padx=(0, PAD_SM))
        PrimaryButton(
            repair_opts_row, text="Start Repair Loop", width=160, height=36, command=self._start_repair_loop
        ).pack(side="left", padx=(0, 8))
        SecondaryButton(
            repair_opts_row, text="Open Repair Folder", width=150, height=36, command=self._open_repair_folder
        ).pack(side="left")

        run_card = Card(scroll)
        run_card.pack(fill="x", pady=(0, PAD_SM))
        Label(run_card, text="Execution Log", size=13, bold=True).pack(anchor="w", padx=PAD, pady=(PAD_SM, 6))
        self._run_log = LogBox(run_card, height=220)
        self._run_log.pack(fill="x", padx=PAD, pady=(0, PAD_SM))

        artifacts_card = Card(scroll)
        artifacts_card.pack(fill="x", pady=(0, PAD_SM))
        artifacts_header = ctk.CTkFrame(artifacts_card, fg_color="transparent")
        artifacts_header.pack(fill="x", padx=PAD, pady=(PAD_SM, 6))
        Label(artifacts_header, text="Repair Artifacts", size=13, bold=True).pack(side="left")
        SecondaryButton(
            artifacts_header, text="Refresh Artifacts", width=130, height=32, command=self._refresh_repair_history
        ).pack(side="right")
        self._repair_artifacts_box = LogBox(artifacts_card, height=180)
        self._repair_artifacts_box.pack(fill="x", padx=PAD, pady=(0, 8))

        artifacts_btn_row = ctk.CTkFrame(artifacts_card, fg_color="transparent")
        artifacts_btn_row.pack(fill="x", padx=PAD, pady=(0, PAD_SM))
        self._open_latest_brief_btn = SecondaryButton(
            artifacts_btn_row, text="Open Latest Brief", width=140, height=34, state="disabled",
            command=lambda: self._open_latest_repair_file("brief_file")
        )
        self._open_latest_brief_btn.pack(side="left", padx=(0, 8))
        self._open_latest_summary_btn = SecondaryButton(
            artifacts_btn_row, text="Open AI Summary", width=130, height=34, state="disabled",
            command=lambda: self._open_latest_repair_file("last_message_file")
        )
        self._open_latest_summary_btn.pack(side="left", padx=(0, 8))
        self._open_latest_command_log_btn = SecondaryButton(
            artifacts_btn_row, text="Open Command Log", width=140, height=34, state="disabled",
            command=lambda: self._open_latest_repair_file("command_log_file")
        )
        self._open_latest_command_log_btn.pack(side="left")

        commit_card = Card(scroll)
        commit_card.pack(fill="x", pady=(0, PAD_SM))
        commit_header = ctk.CTkFrame(commit_card, fg_color="transparent")
        commit_header.pack(fill="x", padx=PAD, pady=(PAD_SM, 6))
        Label(commit_header, text="Safe Commit", size=13, bold=True).pack(side="left")
        SecondaryButton(
            commit_header, text="Refresh Repo State", width=130, height=32, command=self._refresh_repo_state
        ).pack(side="right")

        self._repo_state_box = LogBox(commit_card, height=170)
        self._repo_state_box.pack(fill="x", padx=PAD, pady=(0, 8))

        commit_msg_row = ctk.CTkFrame(commit_card, fg_color="transparent")
        commit_msg_row.pack(fill="x", padx=PAD, pady=(0, 8))
        Label(commit_msg_row, text="Commit message:", size=12, color=TEXT_DIM).pack(side="left", padx=(0, 8))
        self._commit_msg_var = ctk.StringVar()
        self._commit_msg_entry = ctk.CTkEntry(
            commit_msg_row,
            textvariable=self._commit_msg_var,
            fg_color=BG3,
            border_color=BORDER,
            text_color=TEXT,
            corner_radius=8,
            height=36,
            font=ctk.CTkFont(family="Inter", size=12),
        )
        self._commit_msg_entry.pack(side="left", fill="x", expand=True)

        commit_opts_row = ctk.CTkFrame(commit_card, fg_color="transparent")
        commit_opts_row.pack(fill="x", padx=PAD, pady=(0, 8))
        Label(commit_opts_row, text="Push to:", size=12, color=TEXT_DIM).pack(side="left", padx=(0, 8))
        self._push_github_var = ctk.BooleanVar(
            value=bool(self.app_state.get("github_token") or self.cfg.get_github_token())
        )
        self._push_gitlab_var = ctk.BooleanVar(
            value=bool(self.app_state.get("gitlab_token") or self.cfg.get_gitlab_token())
        )
        ctk.CTkCheckBox(
            commit_opts_row,
            text="GitHub",
            variable=self._push_github_var,
            fg_color=PRIMARY,
            hover_color=PRIMARY_H,
            text_color=TEXT,
            font=ctk.CTkFont(family="Inter", size=12),
        ).pack(side="left", padx=(0, PAD_SM))
        ctk.CTkCheckBox(
            commit_opts_row,
            text="GitLab",
            variable=self._push_gitlab_var,
            fg_color=PRIMARY,
            hover_color=PRIMARY_H,
            text_color=TEXT,
            font=ctk.CTkFont(family="Inter", size=12),
        ).pack(side="left")

        commit_btn_row = ctk.CTkFrame(commit_card, fg_color="transparent")
        commit_btn_row.pack(fill="x", padx=PAD, pady=(0, PAD_SM))
        self._commit_btn = SecondaryButton(
            commit_btn_row, text="Commit Fix", width=120, height=36, state="disabled",
            command=lambda: self._start_safe_commit(push=False)
        )
        self._commit_btn.pack(side="left", padx=(0, 8))
        self._commit_push_btn = PrimaryButton(
            commit_btn_row, text="Commit + Push", width=140, height=36, state="disabled",
            command=lambda: self._start_safe_commit(push=True)
        )
        self._commit_push_btn.pack(side="left")

        self._badge = StatusBadge(scroll, status="pending", text="Select an incident to begin")
        self._badge.pack(anchor="w")

    def _apply_saved_settings(self):
        incident_root = self.cfg.get(
            "test_debugging_incident_root",
            self.cfg.get("novadeploy_output_dir", str(CONFIG_PATH.parent / "novadeploy-failures")),
        )
        self._set_entry_value(self._incident_root_entry, self._incident_root_var, incident_root)
        config = self.cfg.get_all()
        if "test_debugging_repair_command" in config:
            repair_command = str(config.get("test_debugging_repair_command") or "")
        else:
            repair_command = self._system.default_repair_command_template()
        self._repair_cmd_var.set(repair_command)
        self._repair_attempts_var.set(str(self.cfg.get("test_debugging_repair_attempts", "2")))
        self._replace_logbox(self._repair_artifacts_box, "Select an incident to inspect repair artifacts.")
        self._replace_logbox(self._repo_state_box, "Select and analyze a repository to inspect git state.")
        self._update_repair_artifact_buttons()
        self._update_commit_buttons()

    # ---------- Incident inbox ----------

    def _browse_incident_root(self):
        folder = filedialog.askdirectory(title="Select incident export folder")
        if not folder:
            return
        self._set_entry_value(self._incident_root_entry, self._incident_root_var, folder)
        self.cfg.set("test_debugging_incident_root", folder)
        self._refresh_incidents()

    def _refresh_incidents(self):
        root_dir = self._incident_root_var.get().strip()
        incidents = self._system.list_incidents(root_dir)
        self._render_incident_list(incidents)
        count = len(incidents)
        self._incident_count_lbl.configure(
            text=f"{count} failed incident{'s' if count != 1 else ''} found in {root_dir}"
        )
        if count == 0:
            self._badge.update_status("warning", "No failed incidents found yet")

    def _render_incident_list(self, incidents):
        for widget in self._incident_list.winfo_children():
            widget.destroy()
        self._incident_buttons = {}

        if not incidents:
            Label(
                self._incident_list,
                text="No failed incidents exported yet.",
                size=11,
                color=TEXT_MUTED,
            ).pack(anchor="w", padx=PAD_SM, pady=PAD_SM)
            return

        for incident in incidents:
            btn = ctk.CTkButton(
                self._incident_list,
                text=self._incident_label(incident),
                anchor="w",
                height=54,
                corner_radius=8,
                fg_color=BG3 if self._current_incident and self._current_incident["id"] == incident["id"] else "transparent",
                hover_color=BG3,
                text_color=TEXT,
                font=ctk.CTkFont(family="Inter", size=11),
                command=lambda value=incident: self._select_incident(value),
            )
            btn.pack(fill="x", padx=PAD_SM, pady=4)
            self._incident_buttons[incident["id"]] = btn

        if self._current_incident:
            for incident in incidents:
                if incident["id"] == self._current_incident["id"]:
                    self._select_incident(incident)
                    return
        self._select_incident(incidents[0])

    def _incident_label(self, incident):
        project_label = incident.get("project_name") or incident.get("project_id") or "unknown-project"
        deployment = incident.get("deployment_id") or "unknown"
        summary = incident.get("summary") or "No summary"
        summary = summary[:80] + ("…" if len(summary) > 80 else "")
        return f"{project_label}\n{self._short_id(deployment)}  •  {summary}"

    def _select_incident(self, incident):
        self._current_incident = incident
        self._current_analysis = None
        self._current_plan = []
        self._current_repair_history = None
        self._current_repo_state = None
        self._current_repair_history = None

        for incident_id, button in self._incident_buttons.items():
            button.configure(
                fg_color=PRIMARY if incident_id == incident["id"] else "transparent",
                hover_color=PRIMARY_H if incident_id == incident["id"] else BG3,
                text_color=WHITE if incident_id == incident["id"] else TEXT,
            )

        detail_lines = [
            f"Project: {incident.get('project_name') or 'Unknown'}",
            f"Project ID: {incident.get('project_id') or 'Unknown'}",
            f"Deployment: {incident.get('deployment_id') or 'Unknown'}",
            f"Commit: {incident.get('git_commit_sha') or 'Unknown'}",
            f"Environment: {incident.get('environment_slug') or 'Unknown'}",
            f"Exported: {incident.get('exported_at') or 'Unknown'}",
            f"Developer log lines: {incident.get('log_count') or 0}",
            "",
            "Summary:",
            incident.get("summary") or "No summary available.",
        ]
        self._replace_logbox(self._incident_detail, "\n".join(detail_lines))
        self._replace_logbox(self._analysis_box, "Select 'Analyze Repo' to inspect the mapped repository.")
        self._replace_logbox(self._plan_box, "No execution plan yet.")

        mapped_path = self._resolve_repo_mapping(incident)
        self._set_entry_value(self._repo_entry, self._repo_path_var, mapped_path)
        if mapped_path:
            self._repo_hint_lbl.configure(text="Mapped repository loaded from settings.")
        else:
            self._repo_hint_lbl.configure(
                text="No repo mapping saved yet. Browse to the affected local repository."
            )
        config = self.cfg.get_all()
        if "test_debugging_repair_command" in config:
            repair_command = str(config.get("test_debugging_repair_command") or "")
        else:
            repair_command = self._system.default_repair_command_template()
        self._repair_cmd_var.set(repair_command)
        self._refresh_repair_history()
        self._refresh_repo_state()
        self._badge.update_status("info", f"Incident selected: {self._short_id(incident.get('deployment_id'))}")

    def _resolve_repo_mapping(self, incident):
        mapping = self.cfg.get("test_debugging_repo_map", {}) or {}
        project_id = incident.get("project_id") or ""
        project_slug = incident.get("project_slug") or ""
        return str(mapping.get(project_id) or mapping.get(project_slug) or "").strip()

    def _open_incident_folder(self):
        if not self._current_incident:
            return
        self._open_path(self._current_incident.get("deployment_dir"))

    def _open_incident_log(self):
        if not self._current_incident:
            return
        log_path = self._current_incident.get("log_path") or self._current_incident.get("payload_path")
        self._open_path(log_path)

    # ---------- Repository resolver ----------

    def _browse_repo(self):
        folder = filedialog.askdirectory(title="Select local repository")
        if not folder:
            return
        self._set_entry_value(self._repo_entry, self._repo_path_var, folder)
        self._repo_hint_lbl.configure(text="Repository path selected manually.")

    def _save_repo_map(self):
        if not self._current_incident:
            self._badge.update_status("error", "Select an incident first")
            return
        path = self._repo_path_var.get().strip()
        if not path:
            self._badge.update_status("error", "Select a repository path first")
            return
        mapping = self.cfg.get("test_debugging_repo_map", {}) or {}
        project_id = self._current_incident.get("project_id") or ""
        project_slug = self._current_incident.get("project_slug") or ""
        if project_id:
            mapping[project_id] = path
        if project_slug:
            mapping[project_slug] = path
        self.cfg.set("test_debugging_repo_map", mapping)
        self._repo_hint_lbl.configure(text="Repository mapping saved for this incident/project.")
        self._badge.update_status("ok", "Repository mapping saved")

    def _open_repo(self):
        self._open_path(self._repo_path_var.get().strip())

    def _save_repair_settings(self):
        self.cfg.set("test_debugging_repair_command", self._repair_cmd_var.get().strip())
        self.cfg.set("test_debugging_repair_attempts", self._repair_attempts_var.get().strip() or "2")
        self._badge.update_status("ok", "Repair loop settings saved")

    def _reset_default_repair_command(self):
        self._repair_cmd_var.set(self._system.default_repair_command_template())
        self._badge.update_status("info", "Default Codex repair command restored")

    # ---------- Analyze / run ----------

    def _analyze_repo(self):
        repo_path = self._repo_path_var.get().strip()
        if not repo_path:
            self._badge.update_status("error", "Select or map a repository first")
            return

        self._analyze_btn.configure(text="Analyzing…", state="disabled")
        self._replace_logbox(self._analysis_box, "Analyzing repository...")
        self._replace_logbox(self._plan_box, "Building execution plan...")

        def _run():
            analysis = self._system.analyze_repository(repo_path)
            plan = analysis.get("plan") or []

            def _finish():
                self._current_analysis = analysis
                self._current_plan = plan
                self._replace_logbox(self._analysis_box, self._system.format_analysis_summary(analysis))
                self._replace_logbox(self._plan_box, self._system.format_plan(plan))
                self._refresh_repo_state()
                if analysis.get("ok"):
                    self._badge.update_status("ok", f"Analysis ready: {len(plan)} step(s) detected")
                else:
                    self._badge.update_status("error", analysis.get("error", "Analysis failed"))
                self._analyze_btn.configure(text="Analyze Repo", state="normal")

            self.after(0, _finish)

        threading.Thread(target=_run, daemon=True).start()

    def _run_plan(self):
        if not self._current_plan:
            self._badge.update_status("error", "Analyze the repository first")
            return
        if self._run_thread and self._run_thread.is_alive():
            return

        repo_path = self._repo_path_var.get().strip()
        self._stop_event = threading.Event()
        self._run_thread = threading.Thread(
            target=self._run_plan_worker,
            args=(repo_path, list(self._current_plan), self._stop_event),
            daemon=True,
        )
        self._run_log.clear()
        self._run_btn.configure(text="Running…", state="disabled")
        self._stop_btn.configure(state="normal")
        self._badge.update_status("pending", "Running execution plan")
        self._run_thread.start()

    def _run_plan_worker(self, repo_path, plan, stop_event):
        def on_event(event):
            msg = str(event.get("message") or "").rstrip()
            if not msg:
                return
            self.after(0, lambda text=msg: self._run_log.append(text))

        result = self._system.run_plan(repo_path, plan, on_event, stop_event=stop_event)

        def _finish():
            self._run_btn.configure(text="Run Plan", state="normal")
            self._stop_btn.configure(state="disabled")
            if result.get("ok"):
                self._badge.update_status("ok", "Execution plan passed")
            else:
                self._badge.update_status("warning", "Execution plan stopped or failed")

        self.after(0, _finish)

    def _stop_run(self):
        if self._stop_event:
            self._stop_event.set()
        self._system.stop_active_run()
        self._badge.update_status("warning", "Stopping execution…")

    def _start_repair_loop(self):
        if not self._current_incident:
            self._badge.update_status("error", "Select an incident first")
            return
        if not self._current_analysis or not self._current_plan:
            self._badge.update_status("error", "Analyze the repository first")
            return
        if self._repair_thread and self._repair_thread.is_alive():
            return

        repo_path = self._repo_path_var.get().strip()
        if not repo_path:
            self._badge.update_status("error", "Select or map a repository first")
            return

        self._save_repair_settings()
        self._run_log.clear()
        self._stop_event = threading.Event()
        self._run_btn.configure(state="disabled")
        self._stop_btn.configure(state="normal")
        self._analyze_btn.configure(state="disabled")
        self._badge.update_status("pending", "Starting repair loop")
        self._repair_thread = threading.Thread(
            target=self._repair_loop_worker,
            args=(
                repo_path,
                dict(self._current_incident),
                dict(self._current_analysis),
                list(self._current_plan),
                self._stop_event,
                int(self._repair_attempts_var.get() or "2"),
                self._repair_cmd_var.get().strip(),
            ),
            daemon=True,
        )
        self._repair_thread.start()

    def _repair_loop_worker(
        self,
        repo_path,
        incident,
        analysis,
        plan,
        stop_event,
        max_attempts,
        repair_command_template,
    ):
        def on_event(event):
            msg = str(event.get("message") or "").rstrip()
            if msg:
                self.after(0, lambda text=msg: self._run_log.append(text))

        result = self._system.start_repair_loop(
            repo_path=repo_path,
            incident=incident,
            analysis=analysis,
            plan=plan,
            on_event=on_event,
            stop_event=stop_event,
            max_attempts=max_attempts,
            repair_command_template=repair_command_template,
        )

        def _finish():
            self._run_btn.configure(state="normal")
            self._stop_btn.configure(state="disabled")
            self._analyze_btn.configure(state="normal")
            self._refresh_repair_history()
            self._refresh_repo_state(force_message=True)
            if result.get("ok"):
                self._badge.update_status("ok", "Repair loop reached green")
            elif result.get("handoff_ready"):
                self._badge.update_status("warning", "Repair handoff ready")
            else:
                self._badge.update_status("warning", "Repair loop stopped")

        self.after(0, _finish)

    def _open_repair_folder(self):
        if not self._current_incident:
            self._badge.update_status("error", "Select an incident first")
            return
        deployment_dir = self._current_incident.get("deployment_dir") or ""
        repair_dir = Path(deployment_dir) / "repair-loop"
        self._open_path(str(repair_dir))

    def _refresh_repair_history(self):
        if not self._current_incident:
            self._current_repair_history = None
            self._replace_logbox(self._repair_artifacts_box, "Select an incident to inspect repair artifacts.")
            self._update_repair_artifact_buttons()
            self._suggest_commit_message(force=True)
            return

        history = self._system.inspect_repair_history(self._current_incident)
        self._current_repair_history = history
        self._replace_logbox(self._repair_artifacts_box, self._system.format_repair_history(history))
        self._update_repair_artifact_buttons()
        self._suggest_commit_message(force=False)

    def _update_repair_artifact_buttons(self):
        latest = ((self._current_repair_history or {}).get("latest_attempt")) or {}
        self._open_latest_brief_btn.configure(
            state="normal" if latest.get("brief_file") else "disabled"
        )
        self._open_latest_summary_btn.configure(
            state="normal" if latest.get("last_message_file") else "disabled"
        )
        self._open_latest_command_log_btn.configure(
            state="normal" if latest.get("command_log_file") else "disabled"
        )

    def _open_latest_repair_file(self, key):
        latest = ((self._current_repair_history or {}).get("latest_attempt")) or {}
        self._open_path(latest.get(key))

    def _refresh_repo_state(self, force_message=False):
        repo_path = self._repo_path_var.get().strip()
        if not repo_path:
            self._current_repo_state = None
            self._replace_logbox(self._repo_state_box, "Select or map a repository first.")
            self._update_commit_buttons()
            return

        repo_state = self._system.inspect_repo_state(repo_path)
        self._current_repo_state = repo_state
        self._replace_logbox(self._repo_state_box, self._system.format_repo_state(repo_state))
        self._suggest_commit_message(force=force_message)
        self._update_commit_buttons()

    def _suggest_commit_message(self, force=False):
        if not self._current_incident:
            if force:
                self._commit_msg_var.set("")
            return
        if self._commit_msg_var.get().strip() and not force:
            return
        suggestion = self._system.build_commit_message(
            self._current_incident,
            self._current_repair_history or {},
        )
        self._commit_msg_var.set(suggestion)

    def _update_commit_buttons(self):
        enabled = bool((self._current_repo_state or {}).get("ok") and (self._current_repo_state or {}).get("dirty"))
        state = "normal" if enabled else "disabled"
        self._commit_btn.configure(state=state)
        self._commit_push_btn.configure(state=state)

    def _start_safe_commit(self, push=False):
        if self._commit_thread and self._commit_thread.is_alive():
            return
        repo_path = self._repo_path_var.get().strip()
        if not repo_path:
            self._badge.update_status("error", "Select or map a repository first")
            return
        if not (self._current_repo_state or {}).get("dirty"):
            self._badge.update_status("warning", "No local changes to commit")
            return

        self._run_log.clear()
        self._run_btn.configure(state="disabled")
        self._stop_btn.configure(state="disabled")
        self._analyze_btn.configure(state="disabled")
        self._commit_btn.configure(state="disabled")
        self._commit_push_btn.configure(state="disabled")
        self._badge.update_status("pending", "Running safe commit flow")
        self._commit_thread = threading.Thread(
            target=self._safe_commit_worker,
            args=(repo_path, push),
            daemon=True,
        )
        self._commit_thread.start()

    def _safe_commit_worker(self, repo_path, push):
        github_token = self.app_state.get("github_token") or self.cfg.get_github_token()
        gitlab_token = self.app_state.get("gitlab_token") or self.cfg.get_gitlab_token()

        def on_event(event):
            msg = str(event.get("message") or "").rstrip()
            if msg:
                self.after(0, lambda text=msg: self._run_log.append(text))

        result = self._system.safe_commit_and_push(
            repo_path=repo_path,
            commit_message=self._commit_msg_var.get().strip(),
            on_event=on_event,
            push_github=bool(push and self._push_github_var.get()),
            push_gitlab=bool(push and self._push_gitlab_var.get()),
            github_token=github_token,
            gitlab_token=gitlab_token,
        )

        def _finish():
            self._run_btn.configure(state="normal")
            self._analyze_btn.configure(state="normal")
            self._refresh_repo_state()
            if result.get("ok"):
                self._badge.update_status("ok", "Safe commit flow completed")
            elif result.get("reason") == "clean":
                self._badge.update_status("warning", "No changes to commit")
            else:
                self._badge.update_status("warning", "Safe commit flow finished with issues")

        self.after(0, _finish)

    # ---------- Helpers ----------

    def _replace_logbox(self, box, text):
        box.clear()
        for line in str(text or "").splitlines():
            box.append(line)

    def _set_entry_value(self, entry, variable, value):
        entry.configure(state="normal")
        variable.set(value or "")
        entry.configure(state="readonly")

    def _clear_logs(self):
        self._run_log.clear()
        self._badge.update_status("pending", "Execution log cleared")

    def _open_path(self, path):
        if not path:
            self._badge.update_status("error", "No path available")
            return
        os.system(f'xdg-open "{path}" >/dev/null 2>&1')

    def _short_id(self, value):
        value = str(value or "").strip()
        if len(value) <= 14:
            return value or "—"
        return value[:6] + "..." + value[-6:]
