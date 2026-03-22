"""Panel – Webhooks Configurator."""
import threading
import customtkinter as ctk
from ui.theme import *
from ui.widgets.common import Card, PrimaryButton, SecondaryButton, Label, StatusBadge, SectionHeader, LogBox


WEBHOOK_TEMPLATES = [
    ("Custom URL", ""),
    ("Vercel Deploy Hook", "https://api.vercel.com/v1/integrations/deploy/"),
    ("Netlify Build Hook", "https://api.netlify.com/build_hooks/"),
    ("Railway Deploy", "https://backboard.railway.app/webhooks/"),
    ("Render Deploy Hook", "https://api.render.com/deploy/srv-"),
]


class PanelWebhooks(ctk.CTkFrame):
    def __init__(self, master, app_state, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app_state = app_state
        self._platform = "github"
        self._repo_var = ctk.StringVar()
        self._url_var = ctk.StringVar()
        self._secret_var = ctk.StringVar()
        self._active_var = ctk.BooleanVar(value=True)
        self._webhook_list_frame = None
        self._create_status = None
        self._log_box = None
        self._template_var = ctk.StringVar(value=WEBHOOK_TEMPLATES[0][0])
        # GitHub event vars
        self._gh_events = {
            "push": ctk.BooleanVar(value=True),
            "pull_request": ctk.BooleanVar(value=False),
            "issues": ctk.BooleanVar(value=False),
            "release": ctk.BooleanVar(value=False),
            "deployment": ctk.BooleanVar(value=False),
            "workflow_run": ctk.BooleanVar(value=False),
        }
        # GitLab event vars
        self._gl_events = {
            "push_events": ctk.BooleanVar(value=True),
            "merge_requests_events": ctk.BooleanVar(value=False),
            "issues_events": ctk.BooleanVar(value=False),
            "tag_push_events": ctk.BooleanVar(value=False),
            "pipeline_events": ctk.BooleanVar(value=False),
        }
        self._gh_events_frame = None
        self._gl_events_frame = None
        self._platform_btns = {}
        self._build_ui()

    def _build_ui(self):
        outer = ctk.CTkScrollableFrame(self, fg_color="transparent")
        outer.pack(fill="both", expand=True, padx=PAD, pady=PAD)

        # Title
        Label(outer, text="Webhooks", size=22, bold=True).pack(anchor="w")
        Label(outer, text="Configure webhooks for CI/CD and integrations",
              size=13, color=TEXT_DIM).pack(anchor="w", pady=(2, PAD_SM))

        # --- Card: Repository selector ---
        repo_card = Card(outer)
        repo_card.pack(fill="x", pady=(0, PAD_SM))

        # Platform pills
        pill_row = ctk.CTkFrame(repo_card, fg_color="transparent")
        pill_row.pack(fill="x", padx=PAD_SM, pady=(PAD_SM, 6))
        Label(pill_row, text="Platform:", size=12, color=TEXT_DIM).pack(side="left", padx=(0, PAD_SM))

        for plat in ("github", "gitlab"):
            label = "GitHub" if plat == "github" else "GitLab"
            btn = ctk.CTkButton(
                pill_row,
                text=label,
                width=90, height=30,
                corner_radius=15,
                fg_color=PRIMARY if plat == self._platform else BG3,
                hover_color=PRIMARY_H if plat == self._platform else BORDER,
                text_color=WHITE if plat == self._platform else TEXT_DIM,
                font=ctk.CTkFont(family="Inter", size=12),
                command=lambda p=plat: self._set_platform(p),
            )
            btn.pack(side="left", padx=(0, 6))
            self._platform_btns[plat] = btn

        # Repo row
        repo_row = ctk.CTkFrame(repo_card, fg_color="transparent")
        repo_row.pack(fill="x", padx=PAD_SM, pady=(0, PAD_SM))
        Label(repo_row, text="Repository:", size=12, color=TEXT_DIM).pack(side="left", padx=(0, 6))
        ctk.CTkEntry(
            repo_row, textvariable=self._repo_var, width=250,
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            placeholder_text="owner/repo", placeholder_text_color=TEXT_MUTED,
            corner_radius=8, height=34,
            font=ctk.CTkFont(family="Inter", size=12),
        ).pack(side="left", padx=(0, 6))
        PrimaryButton(repo_row, text="Load Webhooks", width=140, height=36,
                      command=self._load_webhooks).pack(side="left")

        # Connection warning label
        self._conn_warn = Label(repo_card, text="", size=11, color=WARNING)
        self._conn_warn.pack(anchor="w", padx=PAD_SM, pady=(0, PAD_SM))
        self._update_conn_warning()

        # --- Card: Existing Webhooks ---
        wh_card = Card(outer)
        wh_card.pack(fill="x", pady=(0, PAD_SM))
        Label(wh_card, text="Active Webhooks", size=13, bold=True).pack(
            anchor="w", padx=PAD_SM, pady=(PAD_SM, PAD_SM))

        self._webhook_list_frame = ctk.CTkScrollableFrame(wh_card, fg_color="transparent", height=150)
        self._webhook_list_frame.pack(fill="x", padx=PAD_SM, pady=(0, PAD_SM))
        Label(self._webhook_list_frame, text="No webhooks loaded.",
              size=12, color=TEXT_MUTED).pack(pady=PAD_SM)

        # --- Card: Create New Webhook ---
        create_card = Card(outer)
        create_card.pack(fill="x", pady=(0, PAD_SM))

        SectionHeader(create_card, "+", "Add Webhook", "").pack(
            fill="x", padx=PAD_SM, pady=(PAD_SM, PAD_SM))

        # Template picker
        tmpl_row = ctk.CTkFrame(create_card, fg_color="transparent")
        tmpl_row.pack(fill="x", padx=PAD_SM, pady=(0, 6))
        Label(tmpl_row, text="Template:", size=12, color=TEXT_DIM).pack(side="left", padx=(0, 6))
        ctk.CTkComboBox(
            tmpl_row,
            variable=self._template_var,
            values=[t[0] for t in WEBHOOK_TEMPLATES],
            width=220,
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            button_color=BG3, button_hover_color=BORDER,
            dropdown_fg_color=BG2, dropdown_text_color=TEXT,
            corner_radius=8, height=34,
            font=ctk.CTkFont(family="Inter", size=12),
            command=self._on_template_change,
        ).pack(side="left")

        # URL entry
        url_row = ctk.CTkFrame(create_card, fg_color="transparent")
        url_row.pack(fill="x", padx=PAD_SM, pady=(0, 6))
        Label(url_row, text="URL:", size=12, color=TEXT_DIM).pack(side="left", padx=(0, 6))
        ctk.CTkEntry(
            url_row, textvariable=self._url_var,
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            placeholder_text="https://your-ci-service.com/hooks/...",
            placeholder_text_color=TEXT_MUTED,
            corner_radius=8, height=34,
            font=ctk.CTkFont(family="Inter", size=12),
        ).pack(side="left", fill="x", expand=True)

        # Secret entry
        secret_row = ctk.CTkFrame(create_card, fg_color="transparent")
        secret_row.pack(fill="x", padx=PAD_SM, pady=(0, 6))
        Label(secret_row, text="Secret:", size=12, color=TEXT_DIM).pack(side="left", padx=(0, 6))
        ctk.CTkEntry(
            secret_row, textvariable=self._secret_var,
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            placeholder_text="Webhook secret (optional)",
            placeholder_text_color=TEXT_MUTED,
            corner_radius=8, height=34,
            font=ctk.CTkFont(family="Inter", size=12),
        ).pack(side="left", fill="x", expand=True)

        # GitHub events
        self._gh_events_frame = ctk.CTkFrame(create_card, fg_color="transparent")
        Label(self._gh_events_frame, text="Events:", size=12, color=TEXT_DIM, bold=True).pack(
            anchor="w", padx=PAD_SM, pady=(4, 4))
        gh_row1 = ctk.CTkFrame(self._gh_events_frame, fg_color="transparent")
        gh_row1.pack(fill="x", padx=PAD_SM)
        gh_row2 = ctk.CTkFrame(self._gh_events_frame, fg_color="transparent")
        gh_row2.pack(fill="x", padx=PAD_SM, pady=(0, 6))
        gh_events_list = list(self._gh_events.items())
        for i, (event, var) in enumerate(gh_events_list):
            target_row = gh_row1 if i < 3 else gh_row2
            ctk.CTkCheckBox(
                target_row, text=event, variable=var,
                fg_color=PRIMARY, hover_color=PRIMARY_H,
                text_color=TEXT,
                font=ctk.CTkFont(family="Inter", size=12),
                width=20, height=20,
            ).pack(side="left", padx=(0, PAD_SM))

        # GitLab events
        self._gl_events_frame = ctk.CTkFrame(create_card, fg_color="transparent")
        Label(self._gl_events_frame, text="Events:", size=12, color=TEXT_DIM, bold=True).pack(
            anchor="w", padx=PAD_SM, pady=(4, 4))
        gl_row = ctk.CTkFrame(self._gl_events_frame, fg_color="transparent")
        gl_row.pack(fill="x", padx=PAD_SM, pady=(0, 6))
        for event, var in self._gl_events.items():
            ctk.CTkCheckBox(
                gl_row, text=event, variable=var,
                fg_color=PRIMARY, hover_color=PRIMARY_H,
                text_color=TEXT,
                font=ctk.CTkFont(family="Inter", size=11),
                width=20, height=20,
            ).pack(side="left", padx=(0, 8))

        # Show correct events frame
        self._refresh_events_visibility()

        # Active toggle
        active_row = ctk.CTkFrame(create_card, fg_color="transparent")
        active_row.pack(fill="x", padx=PAD_SM, pady=(0, 6))
        ctk.CTkSwitch(
            active_row,
            text="Active",
            variable=self._active_var,
            fg_color=BG3,
            progress_color=PRIMARY,
            button_color=WHITE,
            button_hover_color=TEXT_DIM,
            text_color=TEXT,
            font=ctk.CTkFont(family="Inter", size=12),
        ).pack(side="left")

        # Create button + status
        btn_row = ctk.CTkFrame(create_card, fg_color="transparent")
        btn_row.pack(fill="x", padx=PAD_SM, pady=(0, PAD_SM))
        PrimaryButton(btn_row, text="Create Webhook", height=40,
                      command=self._create_webhook).pack(fill="x")

        status_row = ctk.CTkFrame(create_card, fg_color="transparent")
        status_row.pack(fill="x", padx=PAD_SM, pady=(0, PAD_SM))
        self._create_status = StatusBadge(status_row, status="pending", text="")
        self._create_status.pack(anchor="w")

        # Log box
        self._log_box = LogBox(outer, height=100)
        self._log_box.pack(fill="x", pady=(0, PAD_SM))

    def _update_conn_warning(self):
        api = self._get_api()
        if api is None:
            plat = "GitHub" if self._platform == "github" else "GitLab"
            self._conn_warn.configure(
                text=f"Connect {plat} first in Push Mode to use webhooks.")
        else:
            self._conn_warn.configure(text="")

    def _get_api(self):
        if self._platform == "github":
            return self.app_state.get("github_api")
        else:
            return self.app_state.get("gitlab_api")

    def _set_platform(self, p):
        self._platform = p
        for plat, btn in self._platform_btns.items():
            if plat == p:
                btn.configure(fg_color=PRIMARY, hover_color=PRIMARY_H, text_color=WHITE)
            else:
                btn.configure(fg_color=BG3, hover_color=BORDER, text_color=TEXT_DIM)
        self._refresh_events_visibility()
        self._update_conn_warning()
        # Clear webhook list
        for w in self._webhook_list_frame.winfo_children():
            w.destroy()
        Label(self._webhook_list_frame, text="No webhooks loaded.",
              size=12, color=TEXT_MUTED).pack(pady=PAD_SM)

    def _refresh_events_visibility(self):
        if self._platform == "github":
            self._gl_events_frame.pack_forget()
            self._gh_events_frame.pack(fill="x", pady=(0, 6))
        else:
            self._gh_events_frame.pack_forget()
            self._gl_events_frame.pack(fill="x", pady=(0, 6))

    def _parse_repo(self):
        repo_str = self._repo_var.get().strip()
        if "/" not in repo_str:
            return None, None
        parts = repo_str.split("/", 1)
        return parts[0].strip(), parts[1].strip()

    def _load_webhooks(self):
        api = self._get_api()
        if api is None:
            self._log_box.append("Connect a platform first in Push Mode.")
            return

        owner, repo = self._parse_repo()
        if not owner or not repo:
            self._log_box.append("Enter repository as owner/repo")
            return

        self._log_box.append(f"Loading webhooks for {owner}/{repo}...")

        for w in self._webhook_list_frame.winfo_children():
            w.destroy()
        Label(self._webhook_list_frame, text="Loading...",
              size=12, color=TEXT_DIM).pack(pady=PAD_SM)

        def worker():
            ok, result = api.list_webhooks(owner, repo)
            self.after(0, lambda: self._render_webhooks(ok, result, owner, repo))

        threading.Thread(target=worker, daemon=True).start()

    def _render_webhooks(self, ok, result, owner, repo):
        for w in self._webhook_list_frame.winfo_children():
            w.destroy()

        if not ok:
            self._log_box.append(f"Error loading webhooks: {result}")
            Label(self._webhook_list_frame, text=f"Error: {result}",
                  size=12, color=ERROR).pack(pady=PAD_SM)
            return

        hooks = result if isinstance(result, list) else []
        if not hooks:
            Label(self._webhook_list_frame, text="No webhooks configured.",
                  size=12, color=TEXT_MUTED).pack(pady=PAD_SM)
            self._log_box.append("No webhooks found.")
            return

        self._log_box.append(f"Found {len(hooks)} webhook(s).")

        for hook in hooks:
            hook_id = hook.get("id", "")
            # GitHub uses config.url, GitLab uses url directly
            if self._platform == "github":
                url = hook.get("config", {}).get("url", "")
                events = hook.get("events", [])
                active = hook.get("active", False)
            else:
                url = hook.get("url", "")
                events = []
                if hook.get("push_events"):
                    events.append("push")
                if hook.get("merge_requests_events"):
                    events.append("merge_requests")
                if hook.get("issues_events"):
                    events.append("issues")
                if hook.get("tag_push_events"):
                    events.append("tag_push")
                if hook.get("pipeline_events"):
                    events.append("pipeline")
                active = hook.get("enable_ssl_verification", True)

            row = ctk.CTkFrame(self._webhook_list_frame, fg_color=BG3, corner_radius=8)
            row.pack(fill="x", pady=3)

            info = ctk.CTkFrame(row, fg_color="transparent")
            info.pack(side="left", fill="x", expand=True, padx=PAD_SM, pady=6)

            url_display = url if len(url) <= 55 else url[:52] + "..."
            ctk.CTkLabel(
                info,
                text=url_display,
                text_color=TEXT,
                font=ctk.CTkFont(family="JetBrains Mono", size=11),
                anchor="w",
            ).pack(anchor="w")

            pills_row = ctk.CTkFrame(info, fg_color="transparent")
            pills_row.pack(anchor="w", pady=(2, 0))
            for ev in events[:4]:
                ctk.CTkLabel(
                    pills_row, text=ev,
                    fg_color=BG2, text_color=TEXT_DIM,
                    corner_radius=4, padx=6, pady=1,
                    font=ctk.CTkFont(family="Inter", size=9),
                ).pack(side="left", padx=(0, 4))

            right = ctk.CTkFrame(row, fg_color="transparent")
            right.pack(side="right", padx=PAD_SM, pady=6)

            status_text = "Active" if active else "Inactive"
            status_color = "ok" if active else "warning"
            StatusBadge(right, status=status_color, text=status_text).pack(side="left", padx=(0, 6))

            def make_delete(hid):
                def _del():
                    self._delete_webhook(hid, owner, repo)
                return _del

            SecondaryButton(
                right, text="Delete", width=70, height=28,
                fg_color="#7F1D1D", hover_color=ERROR, text_color=WHITE,
                command=make_delete(hook_id),
            ).pack(side="left")

    def _create_webhook(self):
        api = self._get_api()
        if api is None:
            self._create_status.update_status("warning", "Connect a platform first")
            return

        owner, repo = self._parse_repo()
        if not owner or not repo:
            self._create_status.update_status("error", "Enter owner/repo")
            return

        url = self._url_var.get().strip()
        if not url:
            self._create_status.update_status("error", "URL required")
            return

        secret = self._secret_var.get().strip()
        active = self._active_var.get()

        self._create_status.update_status("pending", "Creating...")
        self._log_box.append(f"Creating webhook for {owner}/{repo}...")

        def worker():
            if self._platform == "github":
                events = [ev for ev, var in self._gh_events.items() if var.get()]
                if not events:
                    events = ["push"]
                ok, result = api.create_webhook(owner, repo, url,
                                                events=events, secret=secret, active=active)
            else:
                gl_kw = {ev: var.get() for ev, var in self._gl_events.items()}
                ok, result = api.create_webhook(owner, repo, url,
                                                token=secret, **gl_kw)

            def update():
                if ok:
                    self._create_status.update_status("ok", "Created!")
                    self._log_box.append("Webhook created successfully.")
                    self._load_webhooks()
                else:
                    self._create_status.update_status("error", str(result)[:50])
                    self._log_box.append(f"Error: {result}")

            self.after(0, update)

        threading.Thread(target=worker, daemon=True).start()

    def _delete_webhook(self, hook_id, owner, repo):
        api = self._get_api()
        if api is None:
            return

        self._log_box.append(f"Deleting webhook {hook_id}...")

        def worker():
            ok, msg = api.delete_webhook(owner, repo, hook_id)

            def update():
                if ok:
                    self._log_box.append("Webhook deleted.")
                    self._load_webhooks()
                else:
                    self._log_box.append(f"Delete failed: {msg}")

            self.after(0, update)

        threading.Thread(target=worker, daemon=True).start()

    def _on_template_change(self, name):
        for tmpl_name, tmpl_url in WEBHOOK_TEMPLATES:
            if tmpl_name == name:
                self._url_var.set(tmpl_url)
                break
