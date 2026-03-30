"""Panel – NovaDeploy live build monitor."""
import json
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from core.config_manager import CONFIG_PATH, ConfigManager
from core.novadeploy_api import NovaDeployAPI
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


DEFAULT_API_BASE = "https://novadeploy-backend.onrender.com/api"
DEFAULT_INTERVAL = "30 sec"
INTERVAL_OPTIONS = ["15 sec", "30 sec", "60 sec", "120 sec"]
ACTIVE_DEPLOYMENT_STATUSES = {
    "QUEUED",
    "BUILDING",
    "TESTING",
    "STAGING",
    "AWAITING_APPROVAL",
    "DEPLOYING",
}
FINAL_DEPLOYMENT_STATUSES = {"FAILED", "LIVE", "ROLLED_BACK"}
MAX_LIVE_TAIL_LINES = 180


class PanelNovaDeploy(ctk.CTkFrame):
    def __init__(self, master, app_state, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app_state = app_state
        self.cfg = ConfigManager()
        self._api = NovaDeployAPI()
        self._running = False
        self._checking = False
        self._monitor_thread = None
        self._processed = set(self.cfg.get("novadeploy_processed_failures", []))
        self._live_seen = {}
        self._live_status = {}
        self._last_active_ids = set()
        self._live_lines = []
        self._stats = {
            "checks": 0,
            "active": 0,
            "exports": 0,
            "last_deployment": "—",
        }

        self._build_ui()
        self._apply_saved_settings()

    def _build_ui(self):
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        Label(scroll, text="NovaDeploy Monitor", size=22, bold=True).pack(anchor="w", pady=(0, 4))
        Label(
            scroll,
            text="Follow active NovaDeploy builds from Render, tail developer logs in near real time, and export failed builds locally.",
            size=12,
            color=TEXT_DIM,
        ).pack(anchor="w", pady=(0, PAD))

        cfg_card = Card(scroll)
        cfg_card.pack(fill="x", pady=(0, PAD_SM))
        SectionHeader(cfg_card, "N", "Connection", "").pack(
            fill="x", padx=PAD, pady=(PAD_SM, PAD_SM)
        )

        row1 = ctk.CTkFrame(cfg_card, fg_color="transparent")
        row1.pack(fill="x", padx=PAD, pady=(0, 8))
        Label(row1, text="API base:", size=12, color=TEXT_DIM).pack(side="left", padx=(0, 8))
        self._api_base_var = ctk.StringVar()
        ctk.CTkEntry(
            row1,
            textvariable=self._api_base_var,
            width=360,
            fg_color=BG3,
            border_color=BORDER,
            text_color=TEXT,
            corner_radius=8,
            height=34,
            font=ctk.CTkFont(family="Inter", size=12),
        ).pack(side="left")

        row2 = ctk.CTkFrame(cfg_card, fg_color="transparent")
        row2.pack(fill="x", padx=PAD, pady=(0, 8))
        Label(row2, text="API key:", size=12, color=TEXT_DIM).pack(side="left", padx=(0, 8))
        self._api_key_var = ctk.StringVar()
        ctk.CTkEntry(
            row2,
            textvariable=self._api_key_var,
            width=360,
            show="*",
            fg_color=BG3,
            border_color=BORDER,
            text_color=TEXT,
            corner_radius=8,
            height=34,
            font=ctk.CTkFont(family="Inter", size=12),
        ).pack(side="left")

        row3 = ctk.CTkFrame(cfg_card, fg_color="transparent")
        row3.pack(fill="x", padx=PAD, pady=(0, 8))
        Label(row3, text="Project ID:", size=12, color=TEXT_DIM).pack(side="left", padx=(0, 8))
        self._project_id_var = ctk.StringVar()
        ctk.CTkEntry(
            row3,
            textvariable=self._project_id_var,
            width=220,
            fg_color=BG3,
            border_color=BORDER,
            text_color=TEXT,
            corner_radius=8,
            height=34,
            font=ctk.CTkFont(family="Inter", size=12),
        ).pack(side="left", padx=(0, PAD_SM))
        Label(row3, text="Interval:", size=12, color=TEXT_DIM).pack(side="left", padx=(0, 8))
        self._interval_var = ctk.StringVar(value=DEFAULT_INTERVAL)
        ctk.CTkSegmentedButton(
            row3,
            values=INTERVAL_OPTIONS,
            variable=self._interval_var,
            fg_color=BG3,
            selected_color=PRIMARY,
            selected_hover_color=PRIMARY_H,
            unselected_color=BG3,
            unselected_hover_color=BORDER,
            text_color=TEXT,
            font=ctk.CTkFont(family="Inter", size=12),
        ).pack(side="left")

        row4 = ctk.CTkFrame(cfg_card, fg_color="transparent")
        row4.pack(fill="x", padx=PAD, pady=(0, PAD_SM))
        Label(row4, text="Output folder:", size=12, color=TEXT_DIM).pack(side="left", padx=(0, 8))
        self._output_dir_var = ctk.StringVar()
        self._output_entry = ctk.CTkEntry(
            row4,
            textvariable=self._output_dir_var,
            width=320,
            state="readonly",
            fg_color=BG3,
            border_color=BORDER,
            text_color=TEXT,
            corner_radius=8,
            height=34,
            font=ctk.CTkFont(family="Inter", size=12),
        )
        self._output_entry.pack(side="left", padx=(0, 8))
        SecondaryButton(row4, text="Browse…", width=90, height=34, command=self._browse_output).pack(
            side="left", padx=(0, 8)
        )
        SecondaryButton(row4, text="Open", width=70, height=34, command=self._open_output).pack(side="left")

        btn_row = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_row.pack(fill="x", pady=(0, PAD_SM))
        self._save_btn = SecondaryButton(
            btn_row, text="Save Settings", width=150, height=42, command=self._save_settings
        )
        self._save_btn.pack(side="left", padx=(0, 8))
        self._check_btn = PrimaryButton(
            btn_row, text="Check Now", width=140, height=42, command=self._check_now
        )
        self._check_btn.pack(side="left", padx=(0, 8))
        self._start_btn = PrimaryButton(
            btn_row, text="Start Monitor", width=160, height=42, command=self._start_monitor
        )
        self._start_btn.pack(side="left", padx=(0, 8))
        self._stop_btn = SecondaryButton(
            btn_row, text="Stop", width=100, height=42, state="disabled", command=self._stop_monitor
        )
        self._stop_btn.pack(side="left", padx=(0, 8))
        self._clear_btn = SecondaryButton(
            btn_row, text="Clear Seen", width=120, height=42, command=self._clear_processed
        )
        self._clear_btn.pack(side="left")

        status_card = Card(scroll)
        status_card.pack(fill="x", pady=(0, PAD_SM))
        Label(status_card, text="Status", size=13, bold=True).pack(anchor="w", padx=PAD, pady=(PAD_SM, 8))

        stat_row = ctk.CTkFrame(status_card, fg_color="transparent")
        stat_row.pack(fill="x", padx=PAD, pady=(0, 8))
        stat_row.columnconfigure(0, weight=1)
        stat_row.columnconfigure(1, weight=1)
        stat_row.columnconfigure(2, weight=1)
        stat_row.columnconfigure(3, weight=1)

        def make_stat_block(parent, col, title, default_text="0"):
            frame = ctk.CTkFrame(parent, fg_color=BG3, corner_radius=8)
            frame.grid(row=0, column=col, sticky="ew", padx=(0 if col == 0 else 4, 0))
            Label(frame, text=title, size=10, color=TEXT_MUTED).pack(anchor="w", padx=8, pady=(6, 0))
            lbl = Label(frame, text=default_text, size=22, bold=True, color=TEXT)
            lbl.pack(anchor="w", padx=8, pady=(0, 6))
            return lbl

        self._checks_lbl = make_stat_block(stat_row, 0, "Checks")
        self._active_lbl = make_stat_block(stat_row, 1, "Active")
        self._exports_lbl = make_stat_block(stat_row, 2, "Exports")
        last_frame = ctk.CTkFrame(stat_row, fg_color=BG3, corner_radius=8)
        last_frame.grid(row=0, column=3, sticky="ew", padx=(4, 0))
        Label(last_frame, text="Last Deployment", size=10, color=TEXT_MUTED).pack(
            anchor="w", padx=8, pady=(6, 0)
        )
        self._last_lbl = Label(last_frame, text="—", size=11, color=TEXT_DIM)
        self._last_lbl.pack(anchor="w", padx=8, pady=(0, 6))

        badge_row = ctk.CTkFrame(status_card, fg_color="transparent")
        badge_row.pack(fill="x", padx=PAD, pady=(0, PAD_SM))
        self._state_badge = StatusBadge(badge_row, status="pending", text="● Idle")
        self._state_badge.pack(side="left")

        live_card = Card(scroll)
        live_card.pack(fill="x", pady=(0, PAD_SM))
        live_header = ctk.CTkFrame(live_card, fg_color="transparent")
        live_header.pack(fill="x", padx=PAD, pady=(PAD_SM, 4))
        Label(live_header, text="Live Developer Tail", size=13, bold=True).pack(side="left")
        SecondaryButton(
            live_header, text="Clear Tail", width=100, height=32, command=self._clear_live_tail
        ).pack(side="right")
        Label(
            live_card,
            text="Shows new developer log lines from active deployments as NovaDeploy receives them.",
            size=11,
            color=TEXT_DIM,
        ).pack(anchor="w", padx=PAD, pady=(0, 6))
        self._live_logbox = LogBox(live_card, height=260)
        self._live_logbox.pack(fill="x", padx=PAD, pady=(0, PAD_SM))

        log_card = Card(scroll)
        log_card.pack(fill="x", pady=(0, PAD_SM))
        Label(log_card, text="Monitor Log", size=13, bold=True).pack(anchor="w", padx=PAD, pady=(PAD_SM, 4))
        self._logbox = LogBox(log_card, height=220)
        self._logbox.pack(fill="x", padx=PAD, pady=(0, PAD_SM))

    def _apply_saved_settings(self):
        self._api_base_var.set(self.cfg.get("novadeploy_api_base", DEFAULT_API_BASE))
        self._api_key_var.set(self.cfg.get("novadeploy_api_key", ""))
        self._project_id_var.set(self.cfg.get("novadeploy_project_id", ""))
        self._interval_var.set(self.cfg.get("novadeploy_monitor_interval", DEFAULT_INTERVAL))
        self._output_dir_var.set(
            self.cfg.get("novadeploy_output_dir", str(CONFIG_PATH.parent / "novadeploy-failures"))
        )
        self._sync_stats()

    def _browse_output(self):
        folder = filedialog.askdirectory(title="Select output folder")
        if folder:
            self._output_entry.configure(state="normal")
            self._output_dir_var.set(folder)
            self._output_entry.configure(state="readonly")

    def _open_output(self):
        folder = Path(self._output_dir_var.get().strip() or CONFIG_PATH.parent / "novadeploy-failures")
        folder.mkdir(parents=True, exist_ok=True)
        os.system(f'xdg-open "{folder}" >/dev/null 2>&1')

    def _save_settings(self):
        self.cfg.set("novadeploy_api_base", self._api_base_var.get().strip() or DEFAULT_API_BASE)
        self.cfg.set("novadeploy_api_key", self._api_key_var.get().strip())
        self.cfg.set("novadeploy_project_id", self._project_id_var.get().strip())
        self.cfg.set("novadeploy_monitor_interval", self._interval_var.get().strip() or DEFAULT_INTERVAL)
        self.cfg.set(
            "novadeploy_output_dir",
            self._output_dir_var.get().strip() or str(CONFIG_PATH.parent / "novadeploy-failures"),
        )
        self._state_badge.update_status("ok", "Settings saved")

    def _clear_processed(self):
        self._processed = set()
        self.cfg.set("novadeploy_processed_failures", [])
        self._log("Cleared processed failed deployment memory.")

    def _clear_live_tail(self):
        self._live_lines = []
        self._live_logbox.clear()
        self._log("Cleared live developer tail.")

    def _check_now(self):
        if self._checking:
            return
        self._checking = True
        self._check_btn.configure(text="Checking…", state="disabled")
        threading.Thread(target=self._run_single_check, daemon=True).start()

    def _run_single_check(self):
        try:
            self._poll_once()
        finally:
            self._checking = False
            self.after(0, lambda: self._check_btn.configure(text="Check Now", state="normal"))

    def _start_monitor(self):
        if self._running:
            return
        self._save_settings()
        self._running = True
        self._start_btn.configure(state="disabled")
        self._stop_btn.configure(state="normal")
        self._state_badge.update_status("ok", "● Monitoring")
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        self._log("NovaDeploy monitor started.")

    def _stop_monitor(self):
        self._running = False
        self._start_btn.configure(state="normal")
        self._stop_btn.configure(state="disabled")
        self._state_badge.update_status("pending", "● Stopped")
        self._log("NovaDeploy monitor stopped.")

    def _monitor_loop(self):
        while self._running:
            self._poll_once()
            wait_seconds = self._interval_to_seconds(self._interval_var.get())
            slept = 0
            while self._running and slept < wait_seconds:
                time.sleep(1)
                slept += 1

    def _poll_once(self):
        api_base = self._api_base_var.get().strip() or DEFAULT_API_BASE
        api_key = self._api_key_var.get().strip()
        project_id = self._project_id_var.get().strip()
        output_dir = Path(
            self._output_dir_var.get().strip() or CONFIG_PATH.parent / "novadeploy-failures"
        )
        output_dir.mkdir(parents=True, exist_ok=True)
        self._api.set_credentials(api_base, api_key)

        if not api_key or not project_id:
            self.after(
                0,
                lambda: self._state_badge.update_status(
                    "warning", "NovaDeploy API key and project ID are required"
                ),
            )
            return

        ok, deployments = self._api.list_deployments(project_id)
        self._stats["checks"] += 1
        if not ok:
            self.after(0, lambda: self._state_badge.update_status("error", str(deployments)))
            self._log(f"Check failed: {deployments}")
            self._sync_stats()
            return

        deployments = list(deployments or [])
        payloads_by_id = {}
        active_ids = set()
        failed = []

        for deployment in deployments:
            deployment_id = str(deployment.get("id") or "").strip()
            status = str(deployment.get("status") or "").upper()
            if not deployment_id:
                continue
            previous_status = self._live_status.get(deployment_id)
            self._live_status[deployment_id] = status

            if status in ACTIVE_DEPLOYMENT_STATUSES:
                active_ids.add(deployment_id)
                if previous_status != status:
                    self._log(
                        f"Tracking active deployment {deployment_id} -> {status}"
                    )
                ok_logs, payload = self._api.get_developer_logs(deployment_id, limit=500)
                if not ok_logs:
                    self._log(f"Failed to fetch live logs for {deployment_id}: {payload}")
                    continue
                payloads_by_id[deployment_id] = payload
                self._consume_live_logs(output_dir, deployment, payload)
                continue

            if status == "FAILED":
                failed.append(deployment)
            elif (
                previous_status in ACTIVE_DEPLOYMENT_STATUSES
                and status in FINAL_DEPLOYMENT_STATUSES
            ):
                self._log(f"Deployment {deployment_id} finished with status {status}")

        exported = 0
        for deployment in failed:
            deployment_id = str(deployment.get("id") or "").strip()
            if not deployment_id or deployment_id in self._processed:
                continue
            ok_logs, payload = (
                (True, payloads_by_id[deployment_id])
                if deployment_id in payloads_by_id
                else self._api.get_developer_logs(deployment_id, limit=500)
            )
            if not ok_logs:
                self._log(f"Failed to fetch logs for {deployment_id}: {payload}")
                continue
            result = self._store_failed_build(output_dir, deployment, payload)
            self._processed.add(deployment_id)
            exported += 1
            self._stats["exports"] += 1
            self._stats["last_deployment"] = self._short_id(deployment_id)
            self._queue_test_debugging_incident(deployment, result)
            self._log(
                f"Exported failed build {deployment_id} -> {result['log_path'].name} | {result['summary']}"
            )

        self._stats["active"] = len(active_ids)
        for deployment_id in self._last_active_ids - active_ids:
            self._live_seen.pop(deployment_id, None)

        self._last_active_ids = active_ids
        self.cfg.set("novadeploy_processed_failures", sorted(self._processed))

        self.after(
            0,
            lambda: self._state_badge.update_status(
                "ok",
                f"Watching {len(active_ids)} active build(s)"
                if active_ids
                else f"Checked {len(deployments)} deployments",
            ),
        )
        self._sync_stats()

    def _consume_live_logs(self, output_dir, deployment, payload):
        deployment_id = str(payload.get("deploymentId") or deployment.get("id") or "unknown")
        project_id = str(payload.get("projectId") or deployment.get("projectId") or "unknown-project")
        status = str(payload.get("status") or deployment.get("status") or "").upper() or "UNKNOWN"
        logs = list(payload.get("logs") or [])
        seen = self._live_seen.get(deployment_id, set())
        current_keys = {self._entry_key(entry) for entry in logs}
        new_entries = [entry for entry in logs if self._entry_key(entry) not in seen]
        self._live_seen[deployment_id] = current_keys

        target_dir = output_dir / project_id / deployment_id
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / "latest.json").write_text(
            json.dumps(
                {
                    "polledAt": datetime.now(timezone.utc).isoformat(),
                    "deployment": deployment,
                    "developerLogs": payload,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        if not new_entries:
            return

        live_log_path = target_dir / "live.log"
        with live_log_path.open("a", encoding="utf-8") as handle:
            handle.write(self._render_log_text(new_entries))

        prefix = self._short_id(deployment_id)
        for entry in new_entries:
            timestamp = str(entry.get("timestamp") or "").strip()
            level = str(entry.get("level") or "info").upper()
            message = str(entry.get("message") or "").rstrip()
            line = f"[{prefix}][{status}][{timestamp}][{level}] {message}"
            self._append_live_line(line)

    def _store_failed_build(self, output_dir, deployment, payload):
        deployment_id = str(payload.get("deploymentId") or deployment.get("id") or "unknown")
        project_id = str(payload.get("projectId") or deployment.get("projectId") or "unknown-project")
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        target_dir = output_dir / project_id / deployment_id
        target_dir.mkdir(parents=True, exist_ok=True)

        logs = list(payload.get("logs") or [])
        summary = self._summarize_logs(logs)
        metadata = {
            "exportedAt": datetime.now(timezone.utc).isoformat(),
            "deployment": deployment,
            "developerLogs": payload,
            "summary": summary,
        }

        json_path = target_dir / f"{stamp}.json"
        log_path = target_dir / f"{stamp}.log"
        summary_path = target_dir / f"{stamp}.summary.txt"

        json_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        log_path.write_text(self._render_log_text(logs), encoding="utf-8")
        summary_path.write_text(summary + "\n", encoding="utf-8")

        return {
            "json_path": json_path,
            "log_path": log_path,
            "summary_path": summary_path,
            "summary": summary,
        }

    def _queue_test_debugging_incident(self, deployment, stored):
        project_id = str(deployment.get("projectId") or "unknown-project").strip()
        deployment_id = str(deployment.get("id") or "unknown").strip()
        json_path = Path(stored["json_path"])
        incident_id = f"{project_id}:{deployment_id}:{json_path.name}"
        self.cfg.set(
            "test_debugging_pending_incident",
            {
                "incident_id": incident_id,
                "project_id": project_id,
                "deployment_id": deployment_id,
                "deployment_dir": str(json_path.parent),
                "json_path": str(json_path),
                "summary": str(stored.get("summary") or "").strip(),
                "queued_at": datetime.now(timezone.utc).isoformat(),
            },
        )

    def _render_log_text(self, logs):
        rendered = []
        for entry in logs:
            timestamp = str(entry.get("timestamp") or "").strip()
            level = str(entry.get("level") or "info").upper()
            message = str(entry.get("message") or "").rstrip()
            rendered.append(f"[{timestamp}] [{level}] {message}")
        return "\n".join(rendered).strip() + ("\n" if rendered else "")

    def _summarize_logs(self, logs):
        for desired in ("error", "warn", "info"):
            for entry in reversed(list(logs or [])):
                if str(entry.get("level") or "").lower() != desired:
                    continue
                message = self._strip_log_tags(str(entry.get("message") or "").strip())
                if message:
                    return message[:240]
        return "No developer log lines were exported."

    def _strip_log_tags(self, message):
        cursor = message
        while cursor.startswith("["):
            end = cursor.find("]")
            if end <= 1:
                break
            cursor = cursor[end + 1 :].lstrip()
        return cursor or message

    def _append_live_line(self, line):
        self._live_lines.append(line)
        if len(self._live_lines) > MAX_LIVE_TAIL_LINES:
            self._live_lines = self._live_lines[-MAX_LIVE_TAIL_LINES:]

        def _render():
            self._live_logbox.clear()
            for item in self._live_lines:
                self._live_logbox.append(item)

        self.after(0, _render)

    def _entry_key(self, entry):
        return "|".join(
            [
                str(entry.get("timestamp") or "").strip(),
                str(entry.get("level") or "").strip(),
                str(entry.get("message") or "").strip(),
            ]
        )

    def _sync_stats(self):
        self.after(0, lambda: self._checks_lbl.configure(text=str(self._stats["checks"])))
        self.after(0, lambda: self._active_lbl.configure(text=str(self._stats["active"])))
        self.after(0, lambda: self._exports_lbl.configure(text=str(self._stats["exports"])))
        self.after(0, lambda: self._last_lbl.configure(text=self._stats["last_deployment"]))

    def _log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.after(0, lambda: self._logbox.append(f"[{timestamp}] {message}"))

    def _interval_to_seconds(self, label):
        mapping = {
            "15 sec": 15,
            "30 sec": 30,
            "60 sec": 60,
            "120 sec": 120,
        }
        return mapping.get(label, 30)

    def _short_id(self, value):
        value = str(value or "").strip()
        if len(value) <= 14:
            return value or "—"
        return value[:6] + "..." + value[-6:]
