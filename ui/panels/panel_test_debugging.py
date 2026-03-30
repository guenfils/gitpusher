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
        self._ai_runtime_label_to_key = {
            label: key for key, label in self._system.ai_runtime_choices()
        }
        self._ai_runtime_key_to_label = {
            key: label for key, label in self._system.ai_runtime_choices()
        }
        self._approval_mode_label_to_key = {
            label: key for key, label in self._system.approval_mode_choices()
        }
        self._approval_mode_key_to_label = {
            key: label for key, label in self._system.approval_mode_choices()
        }
        self._current_ai_runtime = self._system.get_ai_runtime()
        self._current_approval_mode = self._system.get_approval_mode()
        self._incident_buttons = {}
        self._current_incident = None
        self._current_analysis = None
        self._current_plan = []
        self._current_automation_history = None
        self._current_approval_queue = None
        self._current_metrics = None
        self._current_debug_context = None
        self._current_repair_history = None
        self._current_repo_state = None
        self._current_push_guard = None
        self._current_flow_start_state = None
        self._current_rollback_target = None
        self._current_gate_state = None
        self._run_thread = None
        self._stop_event = None
        self._repair_thread = None
        self._commit_thread = None
        self._push_thread = None
        self._rollback_thread = None
        self._one_click_thread = None
        self._auto_ingest_job = None

        self._build_ui()
        self._apply_saved_settings()
        self._refresh_incidents()
        self._schedule_auto_ingest()

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
        auto_row = ctk.CTkFrame(source_card, fg_color="transparent")
        auto_row.pack(fill="x", padx=PAD, pady=(0, 6))
        self._auto_ingest_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            auto_row,
            text="Auto-ingest new failed incidents from NovaDeploy monitor",
            variable=self._auto_ingest_var,
            fg_color=PRIMARY,
            hover_color=PRIMARY_H,
            text_color=TEXT,
            font=ctk.CTkFont(family="Inter", size=12),
            command=self._save_auto_ingest_setting,
        ).pack(side="left")
        auto_run_row = ctk.CTkFrame(source_card, fg_color="transparent")
        auto_run_row.pack(fill="x", padx=PAD, pady=(0, PAD_SM))
        self._auto_run_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            auto_run_row,
            text="Auto-run approval flow for new failed incidents",
            variable=self._auto_run_var,
            fg_color=PRIMARY,
            hover_color=PRIMARY_H,
            text_color=TEXT,
            font=ctk.CTkFont(family="Inter", size=12),
            command=self._save_auto_run_setting,
        ).pack(side="left")
        self._auto_run_hint = Label(
            source_card,
            text="Uses the current approval mode and only runs when a repo map already exists.",
            size=11,
            color=TEXT_DIM,
        )
        self._auto_run_hint.pack(anchor="w", padx=PAD, pady=(0, PAD_SM))

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

        automation_card = Card(scroll)
        automation_card.pack(fill="x", pady=(0, PAD_SM))
        automation_header = ctk.CTkFrame(automation_card, fg_color="transparent")
        automation_header.pack(fill="x", padx=PAD, pady=(PAD_SM, 6))
        Label(automation_header, text="Automation Status", size=13, bold=True).pack(side="left")
        self._automation_badge = StatusBadge(automation_header, status="pending", text="No automation activity")
        self._automation_badge.pack(side="right", padx=(8, 0))
        SecondaryButton(
            automation_header, text="Refresh Status", width=120, height=32, command=self._refresh_automation_history
        ).pack(side="right")
        self._automation_box = LogBox(automation_card, height=150)
        self._automation_box.pack(fill="x", padx=PAD, pady=(0, PAD_SM))

        approval_card = Card(scroll)
        approval_card.pack(fill="x", pady=(0, PAD_SM))
        approval_header = ctk.CTkFrame(approval_card, fg_color="transparent")
        approval_header.pack(fill="x", padx=PAD, pady=(PAD_SM, 6))
        Label(approval_header, text="Approval Queue", size=13, bold=True).pack(side="left")
        self._approval_badge = StatusBadge(approval_header, status="pending", text="No pending approvals")
        self._approval_badge.pack(side="right", padx=(8, 0))
        SecondaryButton(
            approval_header, text="Refresh Queue", width=120, height=32, command=self._refresh_approval_queue
        ).pack(side="right")
        self._approval_box = LogBox(approval_card, height=140)
        self._approval_box.pack(fill="x", padx=PAD, pady=(0, 8))
        approval_btn_row = ctk.CTkFrame(approval_card, fg_color="transparent")
        approval_btn_row.pack(fill="x", padx=PAD, pady=(0, PAD_SM))
        self._approve_repair_btn = SecondaryButton(
            approval_btn_row, text="Approve Repair", width=130, height=34, command=lambda: self._handle_approval("repair", True)
        )
        self._approve_repair_btn.pack(side="left", padx=(0, 8))
        self._approve_commit_btn = SecondaryButton(
            approval_btn_row, text="Approve Commit", width=130, height=34, command=lambda: self._handle_approval("commit", True)
        )
        self._approve_commit_btn.pack(side="left", padx=(0, 8))
        self._approve_push_btn = PrimaryButton(
            approval_btn_row, text="Approve Push", width=120, height=34, command=lambda: self._handle_approval("push", True)
        )
        self._approve_push_btn.pack(side="left", padx=(0, 8))
        self._reject_approval_btn = SecondaryButton(
            approval_btn_row, text="Reject Latest", width=120, height=34, command=lambda: self._handle_approval("", False)
        )
        self._reject_approval_btn.pack(side="left")

        metrics_card = Card(scroll)
        metrics_card.pack(fill="x", pady=(0, PAD_SM))
        metrics_header = ctk.CTkFrame(metrics_card, fg_color="transparent")
        metrics_header.pack(fill="x", padx=PAD, pady=(PAD_SM, 6))
        Label(metrics_header, text="Run Metrics", size=13, bold=True).pack(side="left")
        SecondaryButton(
            metrics_header, text="Refresh Metrics", width=120, height=32, command=self._refresh_metrics
        ).pack(side="right")
        self._metrics_box = LogBox(metrics_card, height=120)
        self._metrics_box.pack(fill="x", padx=PAD, pady=(0, PAD_SM))

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
            text="Use a local AI runtime like ChatGPT/Codex or Claude. Git Pusher does not request, store, or send AI API keys here; it only invokes your local CLI session that is already authenticated on this machine.",
            size=11,
            color=TEXT_DIM,
        ).pack(anchor="w", padx=PAD, pady=(0, 6))

        runtime_row = ctk.CTkFrame(repair_card, fg_color="transparent")
        runtime_row.pack(fill="x", padx=PAD, pady=(0, 8))
        Label(runtime_row, text="AI runtime:", size=12, color=TEXT_DIM).pack(side="left", padx=(0, 8))
        self._ai_runtime_var = ctk.StringVar(
            value=self._ai_runtime_key_to_label.get(
                self._system.default_ai_runtime(),
                next(iter(self._ai_runtime_label_to_key), "ChatGPT / Codex"),
            )
        )
        self._ai_runtime_segment = ctk.CTkSegmentedButton(
            runtime_row,
            values=list(self._ai_runtime_label_to_key.keys()),
            variable=self._ai_runtime_var,
            fg_color=BG3,
            selected_color=PRIMARY,
            selected_hover_color=PRIMARY_H,
            unselected_color=BG3,
            unselected_hover_color=BORDER,
            text_color=TEXT,
            font=ctk.CTkFont(family="Inter", size=12),
            command=lambda _value: self._save_ai_runtime_setting(),
        )
        self._ai_runtime_segment.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self._ai_runtime_badge = StatusBadge(runtime_row, status="pending", text="Checking")
        self._ai_runtime_badge.pack(side="left")
        self._ai_runtime_hint = Label(repair_card, text="", size=11, color=TEXT_DIM)
        self._ai_runtime_hint.pack(anchor="w", padx=PAD, pady=(0, 8))

        approval_row = ctk.CTkFrame(repair_card, fg_color="transparent")
        approval_row.pack(fill="x", padx=PAD, pady=(0, 8))
        Label(approval_row, text="Approval mode:", size=12, color=TEXT_DIM).pack(side="left", padx=(0, 8))
        self._approval_mode_var = ctk.StringVar(
            value=self._approval_mode_key_to_label.get(
                self._system.default_approval_mode(),
                next(iter(self._approval_mode_label_to_key), "Repair Only"),
            )
        )
        self._approval_mode_segment = ctk.CTkSegmentedButton(
            approval_row,
            values=list(self._approval_mode_label_to_key.keys()),
            variable=self._approval_mode_var,
            fg_color=BG3,
            selected_color=PRIMARY,
            selected_hover_color=PRIMARY_H,
            unselected_color=BG3,
            unselected_hover_color=BORDER,
            text_color=TEXT,
            font=ctk.CTkFont(family="Inter", size=11),
            command=lambda _value: self._save_approval_mode_setting(),
        )
        self._approval_mode_segment.pack(side="left", fill="x", expand=True)
        self._approval_mode_hint = Label(repair_card, text="", size=11, color=TEXT_DIM)
        self._approval_mode_hint.pack(anchor="w", padx=PAD, pady=(0, 8))

        approval_gate_row = ctk.CTkFrame(repair_card, fg_color="transparent")
        approval_gate_row.pack(fill="x", padx=PAD, pady=(0, 8))
        self._require_repair_approval_var = ctk.BooleanVar(value=False)
        self._require_commit_approval_var = ctk.BooleanVar(value=False)
        self._require_push_approval_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            approval_gate_row,
            text="Queue repair approval",
            variable=self._require_repair_approval_var,
            fg_color=PRIMARY,
            hover_color=PRIMARY_H,
            text_color=TEXT,
            font=ctk.CTkFont(family="Inter", size=12),
            command=self._save_repair_settings,
        ).pack(side="left", padx=(0, PAD_SM))
        ctk.CTkCheckBox(
            approval_gate_row,
            text="Queue commit approval",
            variable=self._require_commit_approval_var,
            fg_color=PRIMARY,
            hover_color=PRIMARY_H,
            text_color=TEXT,
            font=ctk.CTkFont(family="Inter", size=12),
            command=self._save_repair_settings,
        ).pack(side="left", padx=(0, PAD_SM))
        ctk.CTkCheckBox(
            approval_gate_row,
            text="Queue push approval",
            variable=self._require_push_approval_var,
            fg_color=PRIMARY,
            hover_color=PRIMARY_H,
            text_color=TEXT,
            font=ctk.CTkFont(family="Inter", size=12),
            command=self._save_repair_settings,
        ).pack(side="left")

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
            placeholder_text="python3 .../repair_agent.py --runtime codex --repo {repo_path} --context {context_file}",
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
        self._one_click_btn = SecondaryButton(
            repair_opts_row, text="Analyze + Repair", width=190, height=36, command=self._start_one_click_flow
        )
        self._one_click_btn.pack(side="left", padx=(0, 8))
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

        debug_card = Card(scroll)
        debug_card.pack(fill="x", pady=(0, PAD_SM))
        debug_header = ctk.CTkFrame(debug_card, fg_color="transparent")
        debug_header.pack(fill="x", padx=PAD, pady=(PAD_SM, 6))
        Label(debug_header, text="Debug Context", size=13, bold=True).pack(side="left")
        SecondaryButton(
            debug_header, text="Refresh Context", width=130, height=32, command=self._refresh_debug_context
        ).pack(side="right")
        self._debug_context_box = LogBox(debug_card, height=170)
        self._debug_context_box.pack(fill="x", padx=PAD, pady=(0, PAD_SM))

        gate_card = Card(scroll)
        gate_card.pack(fill="x", pady=(0, PAD_SM))
        gate_header = ctk.CTkFrame(gate_card, fg_color="transparent")
        gate_header.pack(fill="x", padx=PAD, pady=(PAD_SM, 6))
        Label(gate_header, text="Safety Gate", size=13, bold=True).pack(side="left")
        self._gate_badge = StatusBadge(gate_header, status="pending", text="Gate pending")
        self._gate_badge.pack(side="right")
        self._gate_box = LogBox(gate_card, height=140)
        self._gate_box.pack(fill="x", padx=PAD, pady=(0, PAD_SM))

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
            command=self._refresh_repo_state,
        ).pack(side="left", padx=(0, PAD_SM))
        ctk.CTkCheckBox(
            commit_opts_row,
            text="GitLab",
            variable=self._push_gitlab_var,
            fg_color=PRIMARY,
            hover_color=PRIMARY_H,
            text_color=TEXT,
            font=ctk.CTkFont(family="Inter", size=12),
            command=self._refresh_repo_state,
        ).pack(side="left")

        push_guard_row = ctk.CTkFrame(commit_card, fg_color="transparent")
        push_guard_row.pack(fill="x", padx=PAD, pady=(0, 8))
        self._allow_auto_push_var = ctk.BooleanVar(value=False)
        self._require_clean_start_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            push_guard_row,
            text="Allow auto-push for this repo",
            variable=self._allow_auto_push_var,
            fg_color=PRIMARY,
            hover_color=PRIMARY_H,
            text_color=TEXT,
            font=ctk.CTkFont(family="Inter", size=12),
            command=self._save_push_guard_settings,
        ).pack(side="left", padx=(0, PAD_SM))
        ctk.CTkCheckBox(
            push_guard_row,
            text="Require clean repo at flow start",
            variable=self._require_clean_start_var,
            fg_color=PRIMARY,
            hover_color=PRIMARY_H,
            text_color=TEXT,
            font=ctk.CTkFont(family="Inter", size=12),
            command=self._save_push_guard_settings,
        ).pack(side="left")

        push_guard_entry_row = ctk.CTkFrame(commit_card, fg_color="transparent")
        push_guard_entry_row.pack(fill="x", padx=PAD, pady=(0, 8))
        Label(push_guard_entry_row, text="Allowed branches:", size=12, color=TEXT_DIM).pack(side="left", padx=(0, 8))
        self._allowed_branches_var = ctk.StringVar()
        self._allowed_branches_entry = ctk.CTkEntry(
            push_guard_entry_row,
            textvariable=self._allowed_branches_var,
            width=240,
            fg_color=BG3,
            border_color=BORDER,
            text_color=TEXT,
            corner_radius=8,
            height=34,
            font=ctk.CTkFont(family="Inter", size=12),
        )
        self._allowed_branches_entry.pack(side="left", padx=(0, 8))
        Label(push_guard_entry_row, text="Allowed remotes:", size=12, color=TEXT_DIM).pack(side="left", padx=(0, 8))
        self._allowed_remotes_var = ctk.StringVar()
        self._allowed_remotes_entry = ctk.CTkEntry(
            push_guard_entry_row,
            textvariable=self._allowed_remotes_var,
            width=220,
            fg_color=BG3,
            border_color=BORDER,
            text_color=TEXT,
            corner_radius=8,
            height=34,
            font=ctk.CTkFont(family="Inter", size=12),
        )
        self._allowed_remotes_entry.pack(side="left", padx=(0, 8))
        SecondaryButton(
            push_guard_entry_row, text="Save Guard", width=100, height=34, command=self._save_push_guard_settings
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
        self._push_only_btn = SecondaryButton(
            commit_btn_row, text="Push Current Commit", width=150, height=36, state="disabled",
            command=self._start_push_only
        )
        self._push_only_btn.pack(side="left", padx=(8, 0))

        rollback_btn_row = ctk.CTkFrame(commit_card, fg_color="transparent")
        rollback_btn_row.pack(fill="x", padx=PAD, pady=(0, PAD_SM))
        self._rollback_btn = SecondaryButton(
            rollback_btn_row, text="Rollback", width=120, height=36, state="disabled",
            command=lambda: self._start_rollback(push=False)
        )
        self._rollback_btn.pack(side="left", padx=(0, 8))
        self._rollback_push_btn = PrimaryButton(
            rollback_btn_row, text="Rollback + Push", width=150, height=36, state="disabled",
            command=lambda: self._start_rollback(push=True)
        )
        self._rollback_push_btn.pack(side="left")

        self._badge = StatusBadge(scroll, status="pending", text="Select an incident to begin")
        self._badge.pack(anchor="w")

    def _apply_saved_settings(self):
        incident_root = self.cfg.get(
            "test_debugging_incident_root",
            self.cfg.get("novadeploy_output_dir", str(CONFIG_PATH.parent / "novadeploy-failures")),
        )
        self._set_entry_value(self._incident_root_entry, self._incident_root_var, incident_root)
        config = self.cfg.get_all()
        ai_runtime = self._system.get_ai_runtime(
            self.cfg.get("test_debugging_ai_runtime", self._system.default_ai_runtime())
        )
        self._ai_runtime_var.set(
            self._ai_runtime_key_to_label.get(ai_runtime["key"], ai_runtime["label"])
        )
        if "test_debugging_repair_command" in config:
            repair_command = str(config.get("test_debugging_repair_command") or "")
        else:
            repair_command = self._system.default_repair_command_template(ai_runtime["key"])
        self._repair_cmd_var.set(repair_command)
        self._repair_attempts_var.set(str(self.cfg.get("test_debugging_repair_attempts", "2")))
        self._require_repair_approval_var.set(bool(self.cfg.get("test_debugging_require_repair_approval", False)))
        self._require_commit_approval_var.set(bool(self.cfg.get("test_debugging_require_commit_approval", False)))
        self._require_push_approval_var.set(bool(self.cfg.get("test_debugging_require_push_approval", True)))
        self._auto_ingest_var.set(bool(self.cfg.get("test_debugging_auto_ingest", True)))
        self._auto_run_var.set(bool(self.cfg.get("test_debugging_auto_run", False)))
        push_policy = self._system.normalize_push_policy(self.cfg.get("test_debugging_push_policy", {}))
        self._allow_auto_push_var.set(bool(push_policy.get("allow_auto_push")))
        self._require_clean_start_var.set(bool(push_policy.get("require_clean_start")))
        self._allowed_branches_var.set(", ".join(push_policy.get("allowed_branches") or []))
        self._allowed_remotes_var.set(", ".join(push_policy.get("allowed_remotes") or []))
        approval_mode = self._system.get_approval_mode(
            self.cfg.get("test_debugging_approval_mode", self._system.default_approval_mode())
        )
        self._approval_mode_var.set(
            self._approval_mode_key_to_label.get(approval_mode["key"], approval_mode["label"])
        )
        self._replace_logbox(self._automation_box, "No automation activity recorded yet for this incident.")
        self._replace_logbox(self._approval_box, "No approval requests recorded for this incident.")
        self._replace_logbox(self._metrics_box, "No incident metrics yet.")
        self._replace_logbox(self._repair_artifacts_box, "Select an incident to inspect repair artifacts.")
        self._replace_logbox(self._debug_context_box, "No debug context available yet.")
        self._replace_logbox(self._gate_box, "Run validation to evaluate required checks.")
        self._replace_logbox(self._repo_state_box, "Select and analyze a repository to inspect git state.")
        self._automation_badge.update_status("pending", "No automation activity")
        self._approval_badge.update_status("pending", "No pending approvals")
        self._apply_ai_runtime_ui(ai_runtime)
        self._apply_approval_mode_ui(approval_mode)
        self._update_repair_artifact_buttons()
        self._reset_safety_gate()
        self._update_commit_buttons()
        self._update_rollback_buttons()
        self._update_approval_buttons()

    # ---------- Incident inbox ----------

    def _browse_incident_root(self):
        folder = filedialog.askdirectory(title="Select incident export folder")
        if not folder:
            return
        self._set_entry_value(self._incident_root_entry, self._incident_root_var, folder)
        self.cfg.set("test_debugging_incident_root", folder)
        self._refresh_incidents()

    def _selected_ai_runtime(self):
        label = str(self._ai_runtime_var.get() or "").strip()
        key = self._ai_runtime_label_to_key.get(label, self._system.default_ai_runtime())
        return self._system.get_ai_runtime(key)

    def _apply_ai_runtime_ui(self, runtime=None):
        runtime = runtime or self._selected_ai_runtime()
        self._current_ai_runtime = runtime
        badge_status = "ok" if runtime.get("available") else "warning"
        badge_text = "Connected" if runtime.get("available") else "Not found"
        self._ai_runtime_badge.update_status(badge_status, badge_text)
        self._ai_runtime_hint.configure(
            text=f"{runtime['description']}\n{self._system.format_ai_runtime_summary()}"
        )

    def _save_ai_runtime_setting(self, notify=True):
        previous = dict(self._current_ai_runtime or self._system.get_ai_runtime())
        runtime = self._selected_ai_runtime()
        self.cfg.set("test_debugging_ai_runtime", runtime["key"])
        previous_default = self._system.default_repair_command_template(previous.get("key"))
        current_command = self._repair_cmd_var.get().strip()
        if not current_command or current_command == previous_default:
            self._repair_cmd_var.set(self._system.default_repair_command_template(runtime["key"]))
        self._apply_ai_runtime_ui(runtime)
        if notify:
            self._badge.update_status("ok", f"AI runtime set to {runtime['label']}")

    def _save_auto_ingest_setting(self):
        enabled = bool(self._auto_ingest_var.get())
        self.cfg.set("test_debugging_auto_ingest", enabled)
        if not enabled and self._auto_run_var.get():
            self._auto_run_var.set(False)
            self.cfg.set("test_debugging_auto_run", False)
            self._badge.update_status("warning", "Auto-run disabled because auto-ingest was turned off")

    def _save_auto_run_setting(self):
        enabled = bool(self._auto_run_var.get())
        if enabled and not self._auto_ingest_var.get():
            self._auto_ingest_var.set(True)
            self.cfg.set("test_debugging_auto_ingest", True)
        self.cfg.set("test_debugging_auto_run", enabled)

    def _selected_approval_mode(self):
        label = str(self._approval_mode_var.get() or "").strip()
        key = self._approval_mode_label_to_key.get(label, self._system.default_approval_mode())
        return self._system.get_approval_mode(key)

    def _apply_approval_mode_ui(self, mode=None):
        mode = mode or self._selected_approval_mode()
        self._current_approval_mode = mode
        self._approval_mode_hint.configure(text=mode["description"])
        button_label = {
            "analyze_only": "Analyze",
            "repair_only": "Analyze + Repair",
            "repair_commit": "Analyze + Repair + Commit",
            "repair_push": "Analyze + Repair + Push",
        }.get(mode["key"], mode["label"])
        self._one_click_btn.configure(text=button_label)

    def _save_approval_mode_setting(self, notify=True):
        mode = self._selected_approval_mode()
        self.cfg.set("test_debugging_approval_mode", mode["key"])
        self._apply_approval_mode_ui(mode)
        if notify:
            self._badge.update_status("ok", f"Approval mode set to {mode['label']}")

    def _refresh_incidents(self, auto=False):
        root_dir = self._incident_root_var.get().strip()
        incidents = self._system.list_incidents(root_dir)
        self._render_incident_list(incidents)
        count = len(incidents)
        self._incident_count_lbl.configure(
            text=f"{count} failed incident{'s' if count != 1 else ''} found in {root_dir}"
        )
        self._consume_pending_incident(incidents, auto=auto)
        if count == 0:
            self._badge.update_status("warning", "No failed incidents found yet")

    def _schedule_auto_ingest(self):
        if self._auto_ingest_job is not None:
            try:
                self.after_cancel(self._auto_ingest_job)
            except Exception:
                pass
        self._auto_ingest_job = self.after(5000, self._auto_ingest_tick)

    def _auto_ingest_tick(self):
        self._auto_ingest_job = None
        if not self.winfo_exists():
            return
        if self._auto_ingest_var.get():
            self._refresh_incidents(auto=True)
        self._schedule_auto_ingest()

    def _consume_pending_incident(self, incidents, auto=False):
        pending = self.cfg.get("test_debugging_pending_incident", {}) or {}
        if not pending or not self._auto_ingest_var.get():
            return
        if self._is_busy():
            return

        pending_id = str(pending.get("incident_id") or "").strip()
        pending_json = str(pending.get("json_path") or "").strip()
        pending_deployment_dir = str(pending.get("deployment_dir") or "").strip()
        matched = None
        for incident in incidents:
            if pending_id and incident.get("id") == pending_id:
                matched = incident
                break
            if pending_json and incident.get("payload_path") == pending_json:
                matched = incident
                break
            if pending_deployment_dir and incident.get("deployment_dir") == pending_deployment_dir:
                matched = incident
                break

        if not matched:
            return

        if not self._current_incident or self._current_incident.get("id") != matched.get("id"):
            self._select_incident(matched)
            if auto:
                self._badge.update_status("info", f"Auto-ingested incident: {self._short_id(matched.get('deployment_id'))}")
                self._record_automation_event(
                    incident=matched,
                    source="auto",
                    event="incident_ingested",
                    status="info",
                    message=f"Incident auto-ingested for {self._short_id(matched.get('deployment_id'))}.",
                )
        self.cfg.delete("test_debugging_pending_incident")
        if auto:
            self._schedule_auto_run(matched)

    def _schedule_auto_run(self, incident):
        if not self._auto_run_var.get():
            return
        incident_id = str((incident or {}).get("id") or "").strip()
        if not incident_id:
            return
        mode = self._selected_approval_mode()
        run_id = self._system.new_automation_run_id("auto")
        self._record_automation_event(
            incident=incident,
            source="auto",
            run_id=run_id,
            event="auto_run_scheduled",
            status="pending",
            message=f"Auto-run scheduled in {mode['label']} mode.",
            mode=mode,
        )
        self.after(250, lambda value=incident_id, current_run_id=run_id: self._auto_run_selected_incident(value, current_run_id))

    def _auto_run_selected_incident(self, incident_id, run_id=""):
        if not self.winfo_exists():
            return
        if not self._auto_run_var.get() or self._is_busy():
            return
        current = self._current_incident or {}
        if str(current.get("id") or "").strip() != str(incident_id or "").strip():
            return
        repo_path = self._repo_path_var.get().strip()
        if not repo_path:
            self._record_automation_event(
                source="auto",
                run_id=run_id,
                event="auto_run_skipped",
                status="warning",
                message="Auto-run skipped because no repository map is saved yet.",
                mode=self._selected_approval_mode(),
            )
            self._badge.update_status("warning", "Auto-run skipped: save a repository map for this project first")
            return
        mode = self._selected_approval_mode()
        self._run_log.append(f"[auto-run] Starting {mode['label']} for {self._short_id(current.get('deployment_id'))}")
        self._badge.update_status("pending", f"Auto-running {mode['label']}")
        self._start_one_click_flow(source="auto", run_id=run_id)

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
                    self._current_incident = incident
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
        self._current_automation_history = None
        self._current_approval_queue = None
        self._current_metrics = None
        self._current_debug_context = None
        self._current_repair_history = None
        self._current_repo_state = None
        self._current_push_guard = None
        self._current_flow_start_state = None
        self._current_rollback_target = None
        self._reset_safety_gate()

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
        self._refresh_automation_history()
        self._refresh_approval_queue()
        self._refresh_repair_history()
        self._refresh_repo_state()
        self._refresh_debug_context()
        self._refresh_metrics()
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
        self.cfg.set("test_debugging_ai_runtime", self._selected_ai_runtime().get("key"))
        self.cfg.set("test_debugging_repair_command", self._repair_cmd_var.get().strip())
        self.cfg.set("test_debugging_repair_attempts", self._repair_attempts_var.get().strip() or "2")
        self.cfg.set("test_debugging_require_repair_approval", bool(self._require_repair_approval_var.get()))
        self.cfg.set("test_debugging_require_commit_approval", bool(self._require_commit_approval_var.get()))
        self.cfg.set("test_debugging_require_push_approval", bool(self._require_push_approval_var.get()))
        self._badge.update_status("ok", "Repair loop settings saved")

    def _reset_default_repair_command(self):
        runtime = self._selected_ai_runtime()
        self._repair_cmd_var.set(self._system.default_repair_command_template(runtime["key"]))
        self._badge.update_status("info", f"Default {runtime['label']} repair command restored")

    def _selected_push_policy(self, source="manual"):
        return self._system.normalize_push_policy(
            {
                "allow_auto_push": bool(self._allow_auto_push_var.get()),
                "allowed_branches": self._allowed_branches_var.get().strip(),
                "allowed_remotes": self._allowed_remotes_var.get().strip(),
                "require_clean_start": bool(self._require_clean_start_var.get()),
                "source": source,
            }
        )

    def _save_push_guard_settings(self):
        self.cfg.set(
            "test_debugging_push_policy",
            {
                "allow_auto_push": bool(self._allow_auto_push_var.get()),
                "allowed_branches": self._allowed_branches_var.get().strip(),
                "allowed_remotes": self._allowed_remotes_var.get().strip(),
                "require_clean_start": bool(self._require_clean_start_var.get()),
            },
        )
        self._refresh_repo_state()
        self._badge.update_status("ok", "Push guard settings saved")

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
                self._reset_safety_gate()
                self._refresh_repo_state()
                if analysis.get("ok"):
                    self._badge.update_status("ok", f"Analysis ready: {len(plan)} step(s) detected")
                else:
                    self._badge.update_status("error", analysis.get("error", "Analysis failed"))
                self._analyze_btn.configure(text="Analyze Repo", state="normal")

            self.after(0, _finish)

        threading.Thread(target=_run, daemon=True).start()

    def _start_one_click_flow(self, source="manual", run_id=""):
        if not self._current_incident:
            self._badge.update_status("error", "Select an incident first")
            return
        if self._is_busy():
            return
        if self._one_click_thread and self._one_click_thread.is_alive():
            return

        repo_path = self._repo_path_var.get().strip()
        if not repo_path:
            self._badge.update_status("error", "Select or map a repository first")
            return

        approval_mode = self._selected_approval_mode()
        ai_runtime = self._selected_ai_runtime()
        initial_repo_state = self._system.inspect_repo_state(repo_path)
        self._current_flow_start_state = initial_repo_state
        flow_run_id = str(run_id or "").strip() or self._system.new_automation_run_id(source)
        push_targets = {
            "github": bool(self._push_github_var.get()),
            "gitlab": bool(self._push_gitlab_var.get()),
        }
        self._save_repair_settings()
        self._run_log.clear()
        self._stop_event = threading.Event()
        self._run_btn.configure(state="disabled")
        self._stop_btn.configure(state="normal")
        self._analyze_btn.configure(state="disabled")
        self._one_click_btn.configure(state="disabled")
        self._commit_btn.configure(state="disabled")
        self._commit_push_btn.configure(state="disabled")
        self._rollback_btn.configure(state="disabled")
        self._rollback_push_btn.configure(state="disabled")
        self._record_automation_event(
            source=source,
            run_id=flow_run_id,
            event="flow_started",
            status="pending",
            message=f"Started {approval_mode['label']} flow.",
            mode=approval_mode,
            metadata={"push_targets": push_targets},
        )
        self._badge.update_status("pending", f"Running {approval_mode['label']} flow")
        self._one_click_thread = threading.Thread(
            target=self._one_click_flow_worker,
            args=(
                repo_path,
                dict(self._current_incident),
                self._stop_event,
                dict(approval_mode),
                dict(push_targets),
                dict(initial_repo_state or {}),
                self._selected_push_policy(source=source),
                dict(ai_runtime),
                str(source or "manual"),
                flow_run_id,
            ),
            daemon=True,
        )
        self._one_click_thread.start()

    def _one_click_flow_worker(self, repo_path, incident, stop_event, approval_mode, push_targets, initial_repo_state, push_policy, ai_runtime, source, run_id):
        analysis = self._system.analyze_repository(repo_path)
        plan = analysis.get("plan") or []
        repair_result = None
        commit_result = None
        push_result = None
        commit_warning = ""

        def _apply_analysis():
            self._current_analysis = analysis
            self._current_plan = plan
            self._replace_logbox(self._analysis_box, self._system.format_analysis_summary(analysis))
            self._replace_logbox(self._plan_box, self._system.format_plan(plan))
            self._reset_safety_gate()
            self._refresh_repo_state()

        self.after(0, _apply_analysis)
        if not analysis.get("ok") or not plan:
            self._record_automation_event(
                incident=incident,
                source=source,
                run_id=run_id,
                event="flow_analysis_failed",
                status="error",
                message=analysis.get("error", "Analysis failed or no execution plan was detected."),
                mode=approval_mode,
            )
            def _finish_failed():
                self._run_btn.configure(state="normal")
                self._stop_btn.configure(state="disabled")
                self._analyze_btn.configure(state="normal")
                self._one_click_btn.configure(state="normal")
                self._update_commit_buttons()
                self._update_rollback_buttons()
                self._badge.update_status("error", analysis.get("error", f"{approval_mode['label']} could not start"))
            self.after(0, _finish_failed)
            return

        def on_event(event):
            msg = str(event.get("message") or "").rstrip()
            if msg:
                self.after(0, lambda text=msg: self._run_log.append(text))

        if approval_mode.get("auto_repair"):
            if self._require_repair_approval_var.get():
                approval = self._system.enqueue_approval_request(
                    incident,
                    action="repair",
                    message="Repair step is waiting for approval.",
                    run_id=run_id,
                    source=source,
                    metadata={"approval_mode": approval_mode, "push_targets": push_targets},
                )
                on_event({"type": "approval_queue", "message": "Repair approval queued."})
                repair_result = {"ok": False, "approval_pending": True, "approval": approval}
            else:
                repair_result = self._system.start_repair_loop(
                    repo_path=repo_path,
                    incident=incident,
                    analysis=analysis,
                    plan=plan,
                    on_event=on_event,
                    stop_event=stop_event,
                    max_attempts=int(self._repair_attempts_var.get() or "2"),
                    repair_command_template=self._repair_cmd_var.get().strip(),
                    ai_runtime=(ai_runtime or {}).get("key") or "",
                )

            if repair_result.get("ok") and approval_mode.get("auto_commit"):
                repair_history = self._system.inspect_repair_history(incident)
                commit_message = self._system.build_commit_message(incident, repair_history or {})
                if self._require_commit_approval_var.get():
                    approval = self._system.enqueue_approval_request(
                        incident,
                        action="commit",
                        message="Commit step is waiting for approval.",
                        run_id=run_id,
                        source=source,
                        metadata={"approval_mode": approval_mode, "push_targets": push_targets},
                    )
                    on_event({"type": "approval_queue", "message": "Commit approval queued."})
                    commit_result = {"ok": False, "approval_pending": True, "approval": approval}
                else:
                    commit_result = self._system.safe_commit_changes(
                        repo_path=repo_path,
                        commit_message=commit_message,
                        on_event=on_event,
                    )
                    if approval_mode.get("auto_push") and not any(push_targets.values()):
                        commit_warning = "Push mode selected, but no remotes are enabled. Commit will stay local."
                        on_event({"type": "approval_push_warning", "message": commit_warning})
                    elif commit_result.get("ok") and approval_mode.get("auto_push"):
                        if self._require_push_approval_var.get():
                            approval = self._system.enqueue_approval_request(
                                incident,
                                action="push",
                                message="Push step is waiting for approval.",
                                run_id=run_id,
                                source=source,
                                metadata={
                                    "approval_mode": approval_mode,
                                    "push_targets": push_targets,
                                    "initial_repo_state": initial_repo_state,
                                },
                            )
                            on_event({"type": "approval_queue", "message": "Push approval queued."})
                            push_result = {"ok": False, "approval_pending": True, "approval": approval}
                        else:
                            push_result = self._system.push_current_branch(
                                repo_path=repo_path,
                                on_event=on_event,
                                push_github=bool(push_targets.get("github")),
                                push_gitlab=bool(push_targets.get("gitlab")),
                                github_token=self.app_state.get("github_token") or self.cfg.get_github_token(),
                                gitlab_token=self.app_state.get("gitlab_token") or self.cfg.get_gitlab_token(),
                                push_policy=push_policy,
                                initial_repo_state=initial_repo_state,
                            )

        def _finish():
            self._run_btn.configure(state="normal")
            self._stop_btn.configure(state="disabled")
            self._analyze_btn.configure(state="normal")
            self._one_click_btn.configure(state="normal")
            self._refresh_repair_history()
            if repair_result is not None:
                self._apply_safety_gate(repair_result.get("results") or [], repair_result.get("ok"), executed=True)
            self._refresh_repo_state(force_message=True)
            automation_status = "warning"
            automation_event = "flow_stopped"
            automation_message = f"{approval_mode['label']} stopped."
            if not approval_mode.get("auto_repair"):
                automation_status = "ok"
                automation_event = "flow_ready"
                automation_message = f"{approval_mode['label']} analysis completed."
                self._badge.update_status("ok", f"{approval_mode['label']} ready")
            elif repair_result.get("approval_pending"):
                automation_status = "warning"
                automation_event = "approval_pending_repair"
                automation_message = "Repair approval is pending."
                self._badge.update_status("warning", "Repair approval pending")
            elif repair_result.get("ok") and approval_mode.get("auto_commit"):
                if commit_result and commit_result.get("approval_pending"):
                    automation_status = "warning"
                    automation_event = "approval_pending_commit"
                    automation_message = "Commit approval is pending."
                    self._badge.update_status("warning", "Commit approval pending")
                elif commit_result and commit_result.get("ok"):
                    if push_result and push_result.get("approval_pending"):
                        automation_status = "warning"
                        automation_event = "approval_pending_push"
                        automation_message = "Push approval is pending."
                        self._badge.update_status("warning", "Push approval pending")
                    elif approval_mode.get("auto_push") and any(push_targets.values()) and push_result and push_result.get("ok"):
                        automation_status = "ok"
                        automation_event = "flow_pushed"
                        automation_message = "Repair reached green and was pushed successfully."
                        self._badge.update_status("ok", "Repair + Push completed")
                    elif approval_mode.get("auto_push") and any(push_targets.values()) and push_result and push_result.get("reason") == "push_guard_blocked":
                        automation_status = "warning"
                        automation_event = "flow_push_guard_blocked"
                        automation_message = "Push guard blocked the automated push."
                        self._badge.update_status("warning", "Push guard blocked the automated push")
                    elif approval_mode.get("auto_push"):
                        automation_status = "warning"
                        automation_event = "flow_commit_local_only"
                        automation_message = commit_warning or "Repair reached green; commit stayed local."
                        self._badge.update_status("warning", commit_warning or "Repair reached green; commit stayed local.")
                    else:
                        automation_status = "ok"
                        automation_event = "flow_committed"
                        automation_message = "Repair reached green and was committed safely."
                        self._badge.update_status("ok", "Repair + Commit completed")
                elif commit_result and commit_result.get("reason") == "clean":
                    automation_status = "warning"
                    automation_event = "flow_clean"
                    automation_message = "Repair reached green, but there were no new changes to commit."
                    self._badge.update_status("warning", "Repair reached green; no new changes to commit.")
                else:
                    automation_status = "warning"
                    automation_event = "flow_commit_issue"
                    automation_message = "Repair reached green, but the safe commit flow had issues."
                    self._badge.update_status("warning", "Repair reached green, but the safe commit flow had issues.")
            elif repair_result.get("ok"):
                automation_status = "ok"
                automation_event = "flow_green"
                automation_message = "Repair loop reached green."
                self._badge.update_status("ok", "Repair Only reached green")
            elif repair_result.get("handoff_ready"):
                automation_status = "warning"
                automation_event = "flow_handoff_ready"
                automation_message = f"{approval_mode['label']} produced a repair handoff."
                self._badge.update_status("warning", f"{approval_mode['label']} produced a handoff")
            else:
                self._badge.update_status("warning", f"{approval_mode['label']} stopped")
            self._record_automation_event(
                incident=incident,
                source=source,
                run_id=run_id,
                event=automation_event,
                status=automation_status,
                message=automation_message,
                mode=approval_mode,
                metadata={
                    "repair_ok": bool((repair_result or {}).get("ok")),
                    "handoff_ready": bool((repair_result or {}).get("handoff_ready")),
                    "commit_ok": bool((commit_result or {}).get("ok")),
                    "commit_reason": (commit_result or {}).get("reason") or "",
                    "push_ok": bool((push_result or {}).get("ok")),
                    "push_reason": (push_result or {}).get("reason") or "",
                },
            )
            self._refresh_approval_queue()
            self._refresh_debug_context()
            self._refresh_metrics()

        self.after(0, _finish)

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
        self._one_click_btn.configure(state="disabled")
        self._commit_btn.configure(state="disabled")
        self._commit_push_btn.configure(state="disabled")
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
            self._one_click_btn.configure(state="normal")
            self._apply_safety_gate(result.get("results") or [], result.get("ok"), executed=True)
            self._refresh_repo_state()
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
        self._one_click_btn.configure(state="disabled")
        self._commit_btn.configure(state="disabled")
        self._commit_push_btn.configure(state="disabled")
        self._rollback_btn.configure(state="disabled")
        self._rollback_push_btn.configure(state="disabled")
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
                dict(self._selected_ai_runtime()),
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
        ai_runtime,
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
            ai_runtime=(ai_runtime or {}).get("key") or "",
        )

        def _finish():
            self._run_btn.configure(state="normal")
            self._stop_btn.configure(state="disabled")
            self._analyze_btn.configure(state="normal")
            self._one_click_btn.configure(state="normal")
            self._refresh_repair_history()
            self._apply_safety_gate(result.get("results") or [], result.get("ok"), executed=True)
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
            self._current_rollback_target = None
            self._replace_logbox(self._repair_artifacts_box, "Select an incident to inspect repair artifacts.")
            self._update_repair_artifact_buttons()
            self._update_rollback_buttons()
            self._suggest_commit_message(force=True)
            return

        history = self._system.inspect_repair_history(self._current_incident)
        self._current_repair_history = history
        self._current_rollback_target = self._system.resolve_rollback_snapshot(
            self._repo_path_var.get().strip(),
            history,
        )
        self._replace_logbox(self._repair_artifacts_box, self._system.format_repair_history(history))
        self._update_repair_artifact_buttons()
        self._update_rollback_buttons()
        self._suggest_commit_message(force=False)
        self._refresh_debug_context()
        self._refresh_metrics()

    def _refresh_automation_history(self):
        if not self._current_incident:
            self._current_automation_history = None
            self._replace_logbox(self._automation_box, "No automation activity recorded yet for this incident.")
            self._automation_badge.update_status("pending", "No automation activity")
            return

        history = self._system.inspect_automation_history(self._current_incident)
        self._current_automation_history = history
        self._replace_logbox(self._automation_box, self._system.format_automation_history(history))
        self._automation_badge.update_status(
            history.get("badge_status") or "pending",
            history.get("badge_text") or "No automation activity",
        )

    def _refresh_approval_queue(self):
        if not self._current_incident:
            self._current_approval_queue = None
            self._replace_logbox(self._approval_box, "No approval requests recorded for this incident.")
            self._approval_badge.update_status("pending", "No pending approvals")
            self._update_approval_buttons()
            return

        queue = self._system.inspect_approval_queue(self._current_incident)
        self._current_approval_queue = queue
        self._replace_logbox(self._approval_box, self._system.format_approval_queue(queue))
        latest_pending = queue.get("latest_pending") or {}
        if latest_pending:
            self._approval_badge.update_status("warning", f"Pending {latest_pending.get('action') or 'approval'}")
        else:
            self._approval_badge.update_status("ok", "Approval queue clear")
        self._update_approval_buttons()

    def _refresh_metrics(self):
        if not self._current_incident:
            self._current_metrics = None
            self._replace_logbox(self._metrics_box, "No incident metrics yet.")
            return
        metrics = self._system.build_incident_metrics(
            self._current_incident,
            automation_history=self._current_automation_history or {},
            repair_history=self._current_repair_history or {},
            approval_queue=self._current_approval_queue or {},
        )
        self._current_metrics = metrics
        self._replace_logbox(self._metrics_box, self._system.format_incident_metrics(metrics))

    def _refresh_debug_context(self):
        if not self._current_incident:
            self._current_debug_context = None
            self._replace_logbox(self._debug_context_box, "No debug context available yet.")
            return
        context = self._system.build_debug_context(
            self._current_incident,
            self._current_repair_history or {},
            self._current_repo_state or {},
        )
        self._current_debug_context = context
        self._replace_logbox(self._debug_context_box, self._system.format_debug_context(context))

    def _reset_safety_gate(self):
        gate = self._system.build_safety_gate(self._current_plan, results=[], run_ok=False, executed=False)
        self._current_gate_state = gate
        self._replace_logbox(self._gate_box, self._system.format_safety_gate(gate))
        self._gate_badge.update_status("pending", "Gate pending")

    def _apply_safety_gate(self, results, run_ok, executed=True):
        gate = self._system.build_safety_gate(
            self._current_plan,
            results=results or [],
            run_ok=bool(run_ok),
            executed=bool(executed),
        )
        self._current_gate_state = gate
        self._replace_logbox(self._gate_box, self._system.format_safety_gate(gate))
        if gate.get("ok"):
            self._gate_badge.update_status("ok", "Gate open")
        elif gate.get("executed"):
            self._gate_badge.update_status("warning", "Gate blocked")
        else:
            self._gate_badge.update_status("pending", "Gate pending")

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
            self._current_rollback_target = None
            self._replace_logbox(self._repo_state_box, "Select or map a repository first.")
            self._update_commit_buttons()
            self._update_rollback_buttons()
            return

        repo_state = self._system.inspect_repo_state(repo_path)
        self._current_repo_state = repo_state
        self._current_push_guard = self._system.evaluate_push_guard(
            repo_state,
            initial_repo_state=self._current_flow_start_state or {},
            push_github=bool(self._push_github_var.get()),
            push_gitlab=bool(self._push_gitlab_var.get()),
            policy=self._selected_push_policy(source="manual"),
        )
        self._current_rollback_target = self._system.resolve_rollback_snapshot(
            repo_path,
            self._current_repair_history or {},
        )
        repo_state_text = self._system.format_repo_state(repo_state)
        if self._current_push_guard:
            repo_state_text += "\n\nPush guard:\n" + self._system.format_push_guard(self._current_push_guard)
        if (self._current_rollback_target or {}).get("ok"):
            repo_state_text += (
                "\n\nRollback target:\n"
                f"{self._current_rollback_target.get('ref')}  "
                f"({self._current_rollback_target.get('ref_type')})"
            )
        self._replace_logbox(self._repo_state_box, repo_state_text)
        self._suggest_commit_message(force=force_message)
        self._update_commit_buttons()
        self._update_rollback_buttons()
        self._refresh_debug_context()

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
        commit_enabled = bool(
            (self._current_repo_state or {}).get("ok")
            and (self._current_repo_state or {}).get("dirty")
            and (self._current_gate_state or {}).get("ok")
        )
        push_guard_ok = bool((self._current_push_guard or {}).get("ok"))
        push_enabled = bool(
            (self._current_repo_state or {}).get("ok")
            and not (self._current_repo_state or {}).get("dirty")
            and push_guard_ok
            and (self._push_github_var.get() or self._push_gitlab_var.get())
        )
        self._commit_btn.configure(state="normal" if commit_enabled else "disabled")
        self._commit_push_btn.configure(state="normal" if (commit_enabled and push_guard_ok) else "disabled")
        self._push_only_btn.configure(state="normal" if push_enabled else "disabled")

    def _update_rollback_buttons(self):
        enabled = bool((self._current_rollback_target or {}).get("ok"))
        state = "normal" if enabled else "disabled"
        self._rollback_btn.configure(state=state)
        self._rollback_push_btn.configure(state=state)

    def _update_approval_buttons(self):
        pending = (self._current_approval_queue or {}).get("pending_items") or []
        action_states = {item.get("action"): item for item in pending}
        self._approve_repair_btn.configure(state="normal" if action_states.get("repair") else "disabled")
        self._approve_commit_btn.configure(state="normal" if action_states.get("commit") else "disabled")
        self._approve_push_btn.configure(state="normal" if action_states.get("push") else "disabled")
        self._reject_approval_btn.configure(state="normal" if pending else "disabled")

    def _start_safe_commit(self, push=False):
        if self._commit_thread and self._commit_thread.is_alive():
            return
        repo_path = self._repo_path_var.get().strip()
        if not repo_path:
            self._badge.update_status("error", "Select or map a repository first")
            return
        if not (self._current_gate_state or {}).get("ok"):
            self._badge.update_status("warning", "Safety gate is still blocked")
            return
        if not (self._current_repo_state or {}).get("dirty"):
            self._badge.update_status("warning", "No local changes to commit")
            return

        self._run_log.clear()
        self._run_btn.configure(state="disabled")
        self._stop_btn.configure(state="disabled")
        self._analyze_btn.configure(state="disabled")
        self._one_click_btn.configure(state="disabled")
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
            push_policy=self._selected_push_policy(source="manual"),
            initial_repo_state=self._current_flow_start_state or self._current_repo_state or {},
        )

        def _finish():
            self._run_btn.configure(state="normal")
            self._analyze_btn.configure(state="normal")
            self._one_click_btn.configure(state="normal")
            self._refresh_repo_state()
            self._refresh_metrics()
            if result.get("ok"):
                self._record_automation_event(
                    source="manual",
                    event="manual_commit_push" if push else "manual_commit",
                    status="ok",
                    message="Manual safe commit flow completed.",
                )
                self._badge.update_status("ok", "Safe commit flow completed")
            elif result.get("reason") == "clean":
                self._badge.update_status("warning", "No changes to commit")
            else:
                self._badge.update_status("warning", "Safe commit flow finished with issues")

        self.after(0, _finish)

    def _start_push_only(self):
        if self._push_thread and self._push_thread.is_alive():
            return
        repo_path = self._repo_path_var.get().strip()
        if not repo_path:
            self._badge.update_status("error", "Select or map a repository first")
            return
        if not (self._current_push_guard or {}).get("ok"):
            self._badge.update_status("warning", "Push guard is blocking the push")
            return
        self._run_log.clear()
        self._run_btn.configure(state="disabled")
        self._analyze_btn.configure(state="disabled")
        self._one_click_btn.configure(state="disabled")
        self._commit_btn.configure(state="disabled")
        self._commit_push_btn.configure(state="disabled")
        self._push_only_btn.configure(state="disabled")
        self._badge.update_status("pending", "Pushing current commit")
        self._push_thread = threading.Thread(target=self._push_only_worker, args=(repo_path,), daemon=True)
        self._push_thread.start()

    def _push_only_worker(self, repo_path):
        github_token = self.app_state.get("github_token") or self.cfg.get_github_token()
        gitlab_token = self.app_state.get("gitlab_token") or self.cfg.get_gitlab_token()

        def on_event(event):
            msg = str(event.get("message") or "").rstrip()
            if msg:
                self.after(0, lambda text=msg: self._run_log.append(text))

        result = self._system.push_current_branch(
            repo_path=repo_path,
            on_event=on_event,
            push_github=bool(self._push_github_var.get()),
            push_gitlab=bool(self._push_gitlab_var.get()),
            github_token=github_token,
            gitlab_token=gitlab_token,
            push_policy=self._selected_push_policy(source="manual"),
            initial_repo_state=self._current_flow_start_state or self._current_repo_state or {},
        )

        def _finish():
            self._run_btn.configure(state="normal")
            self._analyze_btn.configure(state="normal")
            self._one_click_btn.configure(state="normal")
            self._refresh_repo_state()
            self._refresh_metrics()
            if result.get("ok"):
                self._record_automation_event(
                    source="manual",
                    event="manual_push",
                    status="ok",
                    message="Manual push completed.",
                )
                self._badge.update_status("ok", "Push completed")
            else:
                self._badge.update_status("warning", "Push finished with issues")

        self.after(0, _finish)

    def _handle_approval(self, action, approved):
        if not self._current_incident:
            self._badge.update_status("error", "Select an incident first")
            return
        decision = "approved" if approved else "rejected"
        resolved = self._system.resolve_approval_request(
            self._current_incident,
            action=str(action or "").strip(),
            decision=decision,
        )
        if not resolved.get("ok"):
            self._badge.update_status("warning", resolved.get("reason", "No pending approval found"))
            return

        item = resolved.get("item") or {}
        self._refresh_approval_queue()
        self._refresh_metrics()
        self._record_automation_event(
            source="manual",
            run_id=item.get("run_id") or "",
            event=f"approval_{decision}",
            status="ok" if approved else "warning",
            message=f"{(item.get('action') or 'approval').capitalize()} {decision}.",
        )
        if not approved:
            self._badge.update_status("warning", "Approval request rejected")
            return

        action_name = str(item.get("action") or "").strip()
        if action_name == "repair":
            self._badge.update_status("pending", "Repair approval granted")
            self._start_repair_loop()
        elif action_name == "commit":
            self._badge.update_status("pending", "Commit approval granted")
            self._start_safe_commit(push=False)
        elif action_name == "push":
            metadata = item.get("metadata") or {}
            initial_repo_state = metadata.get("initial_repo_state") or {}
            if initial_repo_state:
                self._current_flow_start_state = initial_repo_state
            targets = metadata.get("push_targets") or {}
            self._push_github_var.set(bool(targets.get("github", self._push_github_var.get())))
            self._push_gitlab_var.set(bool(targets.get("gitlab", self._push_gitlab_var.get())))
            self._refresh_repo_state()
            self._badge.update_status("pending", "Push approval granted")
            self._start_push_only()

    def _start_rollback(self, push=False):
        if self._rollback_thread and self._rollback_thread.is_alive():
            return
        repo_path = self._repo_path_var.get().strip()
        if not repo_path:
            self._badge.update_status("error", "Select or map a repository first")
            return
        if not (self._current_rollback_target or {}).get("ok"):
            self._badge.update_status("error", "No rollback snapshot available")
            return

        self._run_log.clear()
        self._run_btn.configure(state="disabled")
        self._stop_btn.configure(state="disabled")
        self._analyze_btn.configure(state="disabled")
        self._one_click_btn.configure(state="disabled")
        self._commit_btn.configure(state="disabled")
        self._commit_push_btn.configure(state="disabled")
        self._rollback_btn.configure(state="disabled")
        self._rollback_push_btn.configure(state="disabled")
        self._badge.update_status("pending", "Running rollback flow")
        self._rollback_thread = threading.Thread(
            target=self._rollback_worker,
            args=(repo_path, push),
            daemon=True,
        )
        self._rollback_thread.start()

    def _rollback_worker(self, repo_path, push):
        github_token = self.app_state.get("github_token") or self.cfg.get_github_token()
        gitlab_token = self.app_state.get("gitlab_token") or self.cfg.get_gitlab_token()

        def on_event(event):
            msg = str(event.get("message") or "").rstrip()
            if msg:
                self.after(0, lambda text=msg: self._run_log.append(text))

        result = self._system.rollback_to_snapshot(
            repo_path=repo_path,
            repair_history=self._current_repair_history or {},
            on_event=on_event,
            push_github=bool(push and self._push_github_var.get()),
            push_gitlab=bool(push and self._push_gitlab_var.get()),
            github_token=github_token,
            gitlab_token=gitlab_token,
        )

        def _finish():
            self._run_btn.configure(state="normal")
            self._analyze_btn.configure(state="normal")
            self._one_click_btn.configure(state="normal")
            self._reset_safety_gate()
            self._refresh_repo_state(force_message=True)
            self._refresh_repair_history()
            if result.get("ok"):
                self._badge.update_status("ok", "Rollback completed")
            else:
                self._badge.update_status("warning", "Rollback finished with issues")

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

    def _is_busy(self):
        threads = [
            self._run_thread,
            self._repair_thread,
            self._commit_thread,
            self._push_thread,
            self._rollback_thread,
            self._one_click_thread,
        ]
        return any(thread and thread.is_alive() for thread in threads)

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

    def _record_automation_event(
        self,
        *,
        incident=None,
        source="auto",
        run_id="",
        event="",
        status="info",
        message="",
        mode=None,
        metadata=None,
    ):
        incident = incident or self._current_incident
        if not incident:
            return
        mode = mode or {}
        self._system.append_automation_history(
            incident,
            source=source,
            run_id=run_id,
            event=event,
            status=status,
            message=message,
            approval_mode=(mode.get("key") or ""),
            approval_mode_label=(mode.get("label") or ""),
            metadata=metadata,
        )
        if self.winfo_exists():
            self.after(0, self._refresh_automation_history)
            self.after(0, self._refresh_metrics)
