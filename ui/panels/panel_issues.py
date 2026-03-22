"""Panel – Issue Tracker."""
import threading
import customtkinter as ctk
from ui.theme import *
from ui.widgets.common import Card, PrimaryButton, SecondaryButton, Label, StatusBadge, SectionHeader, LogBox


def _fmt_date(raw):
    """Return shortened date string."""
    if not raw:
        return ""
    return raw[:10]


def _pill(master, text, bg=BG3, fg=TEXT_DIM):
    return ctk.CTkLabel(
        master, text=text,
        fg_color=bg, text_color=fg,
        corner_radius=5, padx=5, pady=1,
        font=ctk.CTkFont(family="Inter", size=10),
    )


class PanelIssues(ctk.CTkFrame):
    def __init__(self, master, app_state, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app_state = app_state
        self._platform = None
        self._owner = ""
        self._repo = ""
        self._issues = []
        self._state_filter = "open"
        self._active_issue = None
        self._right_mode = "detail"   # "detail" or "new"
        self._issue_row_frames = []

        has_gh = bool(self.app_state.get("github_api"))
        has_gl = bool(self.app_state.get("gitlab_api"))

        if not has_gh and not has_gl:
            warn = Card(self)
            warn.pack(fill="both", expand=True, padx=PAD, pady=PAD)
            Label(warn, text="Connect a platform first (Push Mode -> Platform Auth)",
                  size=13, color=WARNING).pack(padx=PAD, pady=PAD)
            return

        self._has_gh = has_gh
        self._has_gl = has_gl
        self._build_ui()
        default = "github" if has_gh else "gitlab"
        self._set_platform(default)

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.columnconfigure(0, weight=2)
        self.columnconfigure(1, weight=3)
        self.rowconfigure(0, weight=1)

        # ── LEFT COLUMN ────────────────────────────────────────────────────
        left = ctk.CTkFrame(self, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(PAD_SM, PAD_SM), pady=PAD_SM)

        Label(left, text="Issues", size=18, bold=True).pack(anchor="w", pady=(0, PAD_SM))

        # Platform + repo controls
        ctrl = ctk.CTkFrame(left, fg_color=BG2, corner_radius=RADIUS)
        ctrl.pack(fill="x", pady=(0, PAD_SM))
        ctrl_inner = ctk.CTkFrame(ctrl, fg_color="transparent")
        ctrl_inner.pack(padx=PAD_SM, pady=PAD_SM, fill="x")

        self._plat_btns = {}
        for label, key in ([("GitHub", "github")] if self._has_gh else []) + \
                          ([("GitLab", "gitlab")] if self._has_gl else []):
            b = ctk.CTkButton(
                ctrl_inner, text=label, width=72, height=28,
                corner_radius=6,
                fg_color=BG3, text_color=TEXT_DIM,
                hover_color=BG3,
                font=ctk.CTkFont(family="Inter", size=11),
                command=lambda k=key: self._set_platform(k),
            )
            b.pack(side="left", padx=(0, 4))
            self._plat_btns[key] = b

        repo_row = ctk.CTkFrame(ctrl, fg_color="transparent")
        repo_row.pack(padx=PAD_SM, pady=(0, PAD_SM), fill="x")
        self._repo_entry = ctk.CTkEntry(
            repo_row, width=200, placeholder_text="owner/repo",
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            placeholder_text_color=TEXT_MUTED, corner_radius=8, height=32,
            font=ctk.CTkFont(family="Inter", size=12),
        )
        self._repo_entry.pack(side="left", padx=(0, PAD_SM))
        SecondaryButton(repo_row, text="Load", width=70, height=32,
                        command=self._load_issues).pack(side="left")

        # State filter + search
        filter_row = ctk.CTkFrame(left, fg_color="transparent")
        filter_row.pack(fill="x", pady=(0, PAD_SM))

        self._state_btns = {}
        for label, key in [("Open", "open"), ("Closed", "closed")]:
            b = ctk.CTkButton(
                filter_row, text=label, width=60, height=28,
                corner_radius=6,
                fg_color=BG3, text_color=TEXT_DIM,
                hover_color=BG3,
                font=ctk.CTkFont(family="Inter", size=11),
                command=lambda k=key: self._set_state(k),
            )
            b.pack(side="left", padx=(0, 4))
            self._state_btns[key] = b

        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._render_list(self._search_var.get()))
        search_entry = ctk.CTkEntry(
            filter_row, width=180, placeholder_text="Search issues…",
            textvariable=self._search_var,
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            placeholder_text_color=TEXT_MUTED, corner_radius=8, height=28,
            font=ctk.CTkFont(family="Inter", size=11),
        )
        search_entry.pack(side="left", padx=(0, 0))

        # Issue list scroll
        self._issue_scroll = ctk.CTkScrollableFrame(left, height=400, fg_color=BG)
        self._issue_scroll.pack(fill="both", expand=True)

        # ── RIGHT COLUMN ───────────────────────────────────────────────────
        right = ctk.CTkFrame(self, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", padx=(0, PAD_SM), pady=PAD_SM)

        # Toggle buttons
        toggle_row = ctk.CTkFrame(right, fg_color="transparent")
        toggle_row.pack(fill="x", pady=(0, PAD_SM))
        self._detail_toggle_btn = ctk.CTkButton(
            toggle_row, text="Detail", width=80, height=30,
            corner_radius=6, fg_color=PRIMARY, text_color=WHITE, hover_color=PRIMARY_H,
            font=ctk.CTkFont(family="Inter", size=12),
            command=lambda: self._toggle_right("detail"),
        )
        self._detail_toggle_btn.pack(side="left", padx=(0, 4))
        self._new_toggle_btn = ctk.CTkButton(
            toggle_row, text="New Issue", width=90, height=30,
            corner_radius=6, fg_color=BG3, text_color=TEXT_DIM, hover_color=BG3,
            font=ctk.CTkFont(family="Inter", size=12),
            command=lambda: self._toggle_right("new"),
        )
        self._new_toggle_btn.pack(side="left")

        # ── Detail view ────────────────────────────────────────────────────
        self._detail_frame = ctk.CTkScrollableFrame(right, fg_color="transparent")
        self._detail_frame.pack(fill="both", expand=True)

        self._issue_title_label = Label(self._detail_frame, text="Select an issue", size=16, bold=True)
        self._issue_title_label.pack(anchor="w", pady=(0, PAD_SM))

        self._meta_row = ctk.CTkFrame(self._detail_frame, fg_color="transparent")
        self._meta_row.pack(fill="x", pady=(0, PAD_SM))

        self._issue_num_badge = StatusBadge(self._meta_row, status="pending", text="")
        self._issue_num_badge.pack(side="left", padx=(0, 4))
        self._issue_state_badge = StatusBadge(self._meta_row, status="pending", text="")
        self._issue_state_badge.pack(side="left", padx=(0, 4))
        self._issue_author_label = Label(self._meta_row, text="", size=11, color=TEXT_DIM)
        self._issue_author_label.pack(side="left", padx=(0, 4))
        self._issue_date_label = Label(self._meta_row, text="", size=11, color=TEXT_MUTED)
        self._issue_date_label.pack(side="left")

        self._issue_body = ctk.CTkTextbox(
            self._detail_frame, height=120,
            fg_color=BG2, text_color=TEXT,
            font=ctk.CTkFont(family="Inter", size=12),
            corner_radius=8, border_color=BORDER, border_width=1,
            state="disabled",
        )
        self._issue_body.pack(fill="x", pady=(0, PAD_SM))

        # Action buttons
        act_row = ctk.CTkFrame(self._detail_frame, fg_color="transparent")
        act_row.pack(fill="x", pady=(0, PAD_SM))
        self._toggle_btn = SecondaryButton(act_row, text="Close Issue", width=120, height=34,
                                           command=self._toggle_issue)
        self._toggle_btn.pack(side="left", padx=(0, PAD_SM))
        SecondaryButton(act_row, text="Refresh", width=80, height=34,
                        command=self._refresh_detail).pack(side="left")

        # Separator
        ctk.CTkFrame(self._detail_frame, height=1, fg_color=BORDER).pack(fill="x", pady=PAD_SM)

        Label(self._detail_frame, text="Comments", size=13, bold=True).pack(anchor="w", pady=(0, PAD_SM))

        self._comments_scroll = ctk.CTkScrollableFrame(self._detail_frame, height=150, fg_color=BG)
        self._comments_scroll.pack(fill="x", pady=(0, PAD_SM))

        # Add comment
        self._comment_box = ctk.CTkTextbox(
            self._detail_frame, height=60,
            fg_color=BG2, text_color=TEXT,
            font=ctk.CTkFont(family="Inter", size=12),
            corner_radius=8, border_color=BORDER, border_width=1,
        )
        self._comment_box.pack(fill="x", pady=(0, PAD_SM))
        comment_row = ctk.CTkFrame(self._detail_frame, fg_color="transparent")
        comment_row.pack(fill="x")
        PrimaryButton(comment_row, text="Comment", width=100, height=36,
                      command=self._add_comment).pack(side="right")
        self._comment_badge = StatusBadge(comment_row, status="pending", text="")
        self._comment_badge.pack(side="left")
        self._comment_badge.pack_forget()

        # ── New Issue form ──────────────────────────────────────────────────
        self._new_frame = ctk.CTkFrame(right, fg_color="transparent")

        Label(self._new_frame, text="Create New Issue", size=14, bold=True).pack(
            anchor="w", pady=(0, PAD_SM))

        self._new_title_entry = ctk.CTkEntry(
            self._new_frame, placeholder_text="Issue title…",
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            placeholder_text_color=TEXT_MUTED, corner_radius=8, height=40,
            font=ctk.CTkFont(family="Inter", size=13),
        )
        self._new_title_entry.pack(fill="x", pady=(0, PAD_SM))

        self._new_desc_box = ctk.CTkTextbox(
            self._new_frame, height=120,
            fg_color=BG2, text_color=TEXT,
            font=ctk.CTkFont(family="Inter", size=12),
            corner_radius=8, border_color=BORDER, border_width=1,
        )
        self._new_desc_box.pack(fill="x", pady=(0, PAD_SM))

        self._new_labels_entry = ctk.CTkEntry(
            self._new_frame, placeholder_text="bug,enhancement,… (optional)",
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            placeholder_text_color=TEXT_MUTED, corner_radius=8, height=36,
            font=ctk.CTkFont(family="Inter", size=12),
        )
        self._new_labels_entry.pack(fill="x", pady=(0, PAD_SM))

        self._new_assignees_entry = ctk.CTkEntry(
            self._new_frame, placeholder_text="username1,username2 (optional, GitHub only)",
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            placeholder_text_color=TEXT_MUTED, corner_radius=8, height=36,
            font=ctk.CTkFont(family="Inter", size=12),
        )
        self._new_assignees_entry.pack(fill="x", pady=(0, PAD_SM))

        PrimaryButton(self._new_frame, text="Create Issue", height=42,
                      command=self._create_issue).pack(fill="x", pady=(0, PAD_SM))

        self._create_badge = StatusBadge(self._new_frame, status="pending", text="")
        self._create_badge.pack(anchor="w")
        self._create_badge.pack_forget()

        # Initial state filter button appearance
        self._set_state("open")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _toggle_right(self, mode):
        self._right_mode = mode
        if mode == "detail":
            self._detail_toggle_btn.configure(fg_color=PRIMARY, text_color=WHITE, hover_color=PRIMARY_H)
            self._new_toggle_btn.configure(fg_color=BG3, text_color=TEXT_DIM, hover_color=BG3)
            self._new_frame.pack_forget()
            self._detail_frame.pack(fill="both", expand=True)
        else:
            self._new_toggle_btn.configure(fg_color=PRIMARY, text_color=WHITE, hover_color=PRIMARY_H)
            self._detail_toggle_btn.configure(fg_color=BG3, text_color=TEXT_DIM, hover_color=BG3)
            self._detail_frame.pack_forget()
            self._new_frame.pack(fill="both", expand=True)

    def _set_platform(self, p):
        self._platform = p
        for key, btn in self._plat_btns.items():
            if key == p:
                btn.configure(fg_color=PRIMARY, text_color=WHITE, hover_color=PRIMARY_H)
            else:
                btn.configure(fg_color=BG3, text_color=TEXT_DIM, hover_color=BG3)
        self._issues = []
        self._active_issue = None
        self._render_list()

    def _set_state(self, s):
        self._state_filter = s
        for key, btn in self._state_btns.items():
            if key == s:
                btn.configure(fg_color=PRIMARY, text_color=WHITE, hover_color=PRIMARY_H)
            else:
                btn.configure(fg_color=BG3, text_color=TEXT_DIM, hover_color=BG3)
        if self._owner and self._repo:
            threading.Thread(target=self._do_load_issues, daemon=True).start()

    # ── Load ──────────────────────────────────────────────────────────────────

    def _load_issues(self):
        raw = self._repo_entry.get().strip()
        if "/" not in raw:
            return
        parts = raw.split("/", 1)
        self._owner, self._repo = parts[0].strip(), parts[1].strip()
        threading.Thread(target=self._do_load_issues, daemon=True).start()

    def _do_load_issues(self):
        owner, repo = self._owner, self._repo
        if self._platform == "github":
            api = self.app_state.get("github_api")
            state = self._state_filter  # "open" or "closed"
            ok, data = api.list_issues(owner, repo, state=state)
        else:
            api = self.app_state.get("gitlab_api")
            state = "opened" if self._state_filter == "open" else "closed"
            ok, data = api.list_issues(owner, repo, state=state)

        if ok and isinstance(data, list):
            self._issues = data
        else:
            self._issues = []
        self.after(0, self._render_list)

    def _render_list(self, filter_text=""):
        for w in self._issue_scroll.winfo_children():
            w.destroy()
        self._issue_row_frames = []

        ft = filter_text.lower()
        for issue in self._issues:
            if self._platform == "github":
                num = issue.get("number", 0)
                title = issue.get("title", "")
                author = issue.get("user", {}).get("login", "")
                date = _fmt_date(issue.get("created_at", ""))
                labels = [lb.get("name", "") for lb in issue.get("labels", [])]
                # GitHub returns PRs in issues endpoint; skip pull requests
                if issue.get("pull_request"):
                    continue
            else:
                num = issue.get("iid", 0)
                title = issue.get("title", "")
                author = issue.get("author", {}).get("name", "")
                date = _fmt_date(issue.get("created_at", ""))
                labels = issue.get("labels", [])

            if ft and ft not in title.lower():
                continue

            row = ctk.CTkFrame(
                self._issue_scroll, fg_color=BG3,
                corner_radius=6, cursor="hand2",
            )
            row.pack(fill="x", pady=2, padx=2)

            r1 = ctk.CTkFrame(row, fg_color="transparent")
            r1.pack(fill="x", padx=PAD_SM, pady=(PAD_SM, 2))
            ctk.CTkLabel(r1, text=f"#{num}",
                         font=ctk.CTkFont(family="JetBrains Mono", size=11),
                         text_color=TEXT_MUTED).pack(side="left", padx=(0, 6))
            short_title = title[:50] + ("…" if len(title) > 50 else "")
            ctk.CTkLabel(r1, text=short_title,
                         font=ctk.CTkFont(family="Inter", size=13),
                         text_color=TEXT, anchor="w").pack(side="left", fill="x", expand=True)

            r2 = ctk.CTkFrame(row, fg_color="transparent")
            r2.pack(fill="x", padx=PAD_SM, pady=(0, PAD_SM))
            ctk.CTkLabel(r2, text=author,
                         font=ctk.CTkFont(family="Inter", size=11),
                         text_color=TEXT_DIM).pack(side="left")
            ctk.CTkLabel(r2, text=" · " + date,
                         font=ctk.CTkFont(family="Inter", size=11),
                         text_color=TEXT_MUTED).pack(side="left")
            for lb in labels[:3]:
                _pill(r2, lb).pack(side="left", padx=(4, 0))

            # Bind click
            for widget in (row, r1, r2):
                widget.bind("<Button-1>", lambda e, iss=issue, fr=row: self._show_detail(iss, fr))

            self._issue_row_frames.append((row, issue))

    # ── Detail ────────────────────────────────────────────────────────────────

    def _show_detail(self, issue, frame=None):
        self._active_issue = issue
        self._toggle_right("detail")

        # Deactivate all rows, highlight selected
        for fr, _ in self._issue_row_frames:
            fr.configure(border_width=0)
        if frame:
            frame.configure(border_width=2, border_color=PRIMARY)

        if self._platform == "github":
            num = issue.get("number", 0)
            title = issue.get("title", "")
            body = issue.get("body") or "No description provided."
            state = issue.get("state", "open")
            author = issue.get("user", {}).get("login", "")
            date = _fmt_date(issue.get("created_at", ""))
        else:
            num = issue.get("iid", 0)
            title = issue.get("title", "")
            body = issue.get("description") or "No description provided."
            state = issue.get("state", "opened")
            author = issue.get("author", {}).get("name", "")
            date = _fmt_date(issue.get("created_at", ""))

        self._issue_title_label.configure(text=title)
        self._issue_num_badge.update_status("info", f"#{num}")

        is_open = state in ("open", "opened")
        self._issue_state_badge.update_status(
            "ok" if is_open else "pending",
            "Open" if is_open else "Closed",
        )
        self._toggle_btn.configure(text="Close Issue" if is_open else "Reopen Issue")
        self._issue_author_label.configure(text=f"by {author}")
        self._issue_date_label.configure(text=date)

        self._issue_body.configure(state="normal")
        self._issue_body.delete("1.0", "end")
        self._issue_body.insert("1.0", body)
        self._issue_body.configure(state="disabled")

        # Load comments
        threading.Thread(target=self._load_comments, args=(issue,), daemon=True).start()

    def _refresh_detail(self):
        if self._active_issue:
            self._load_issues()

    def _load_comments(self, issue):
        owner, repo = self._owner, self._repo
        if self._platform == "github":
            api = self.app_state.get("github_api")
            num = issue.get("number")
            ok, comments = api.list_comments(owner, repo, num)
        else:
            api = self.app_state.get("gitlab_api")
            iid = issue.get("iid")
            ok, comments = api.list_comments(owner, repo, iid)

        if ok and isinstance(comments, list):
            self.after(0, lambda c=comments: self._render_comments(c))
        else:
            self.after(0, lambda: self._render_comments([]))

    def _render_comments(self, comments):
        for w in self._comments_scroll.winfo_children():
            w.destroy()

        if not comments:
            ctk.CTkLabel(self._comments_scroll, text="No comments yet.",
                         font=ctk.CTkFont(family="Inter", size=11),
                         text_color=TEXT_MUTED).pack(anchor="w", pady=4)
            return

        for c in comments:
            if self._platform == "github":
                author = c.get("user", {}).get("login", "?")
                date = _fmt_date(c.get("created_at", ""))
                body = c.get("body", "")
            else:
                author = c.get("author", {}).get("name") or c.get("author", {}).get("username", "?")
                date = _fmt_date(c.get("created_at", ""))
                body = c.get("body", "")

            cframe = ctk.CTkFrame(self._comments_scroll, fg_color=BG2, corner_radius=6)
            cframe.pack(fill="x", pady=2, padx=2)

            hrow = ctk.CTkFrame(cframe, fg_color="transparent")
            hrow.pack(fill="x", padx=PAD_SM, pady=(PAD_SM, 2))

            # Avatar
            ctk.CTkLabel(hrow, text=author[0].upper() if author else "?",
                         width=24, height=24, corner_radius=12,
                         fg_color=PRIMARY, text_color=WHITE,
                         font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
                         ).pack(side="left", padx=(0, 6))
            ctk.CTkLabel(hrow, text=author,
                         font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
                         text_color=TEXT).pack(side="left", padx=(0, 6))
            ctk.CTkLabel(hrow, text=date,
                         font=ctk.CTkFont(family="Inter", size=10),
                         text_color=TEXT_MUTED).pack(side="left")

            ctk.CTkLabel(cframe, text=body,
                         font=ctk.CTkFont(family="Inter", size=12),
                         text_color=TEXT_DIM, anchor="w", justify="left",
                         wraplength=320).pack(
                anchor="w", padx=PAD_SM, pady=(0, PAD_SM))

    def _add_comment(self):
        if not self._active_issue:
            return
        body = self._comment_box.get("1.0", "end").strip()
        if not body:
            return

        self._comment_badge.update_status("pending", "Posting…")
        self._comment_badge.pack(side="left")

        def _do():
            owner, repo = self._owner, self._repo
            if self._platform == "github":
                api = self.app_state.get("github_api")
                num = self._active_issue.get("number")
                ok, _ = api.add_comment(owner, repo, num, body)
            else:
                api = self.app_state.get("gitlab_api")
                iid = self._active_issue.get("iid")
                ok, _ = api.add_comment(owner, repo, iid, body)

            if ok:
                self.after(0, lambda: self._comment_badge.update_status("ok", "Posted!"))
                self.after(0, lambda: self._comment_box.delete("1.0", "end"))
                self.after(0, lambda: threading.Thread(
                    target=self._load_comments, args=(self._active_issue,), daemon=True).start())
            else:
                self.after(0, lambda: self._comment_badge.update_status("error", "Failed"))

        threading.Thread(target=_do, daemon=True).start()

    # ── Toggle open/closed ────────────────────────────────────────────────────

    def _toggle_issue(self):
        if not self._active_issue:
            return

        if self._platform == "github":
            current = self._active_issue.get("state", "open")
            new_state = "closed" if current == "open" else "open"
        else:
            current = self._active_issue.get("state", "opened")
            new_state = "close" if current == "opened" else "reopen"

        def _do():
            owner, repo = self._owner, self._repo
            if self._platform == "github":
                api = self.app_state.get("github_api")
                num = self._active_issue.get("number")
                ok, updated = api.update_issue(owner, repo, num, state=new_state)
            else:
                api = self.app_state.get("gitlab_api")
                iid = self._active_issue.get("iid")
                ok, updated = api.update_issue(owner, repo, iid, state_event=new_state)

            if ok:
                self._active_issue = updated
                self.after(0, lambda: self._show_detail(updated))
                self.after(0, lambda: threading.Thread(
                    target=self._do_load_issues, daemon=True).start())

        threading.Thread(target=_do, daemon=True).start()

    # ── Create issue ──────────────────────────────────────────────────────────

    def _create_issue(self):
        if not self._owner or not self._repo:
            self._create_badge.update_status("error", "Load a repo first (enter owner/repo and Load)")
            self._create_badge.pack(anchor="w")
            return

        title = self._new_title_entry.get().strip()
        if not title:
            self._create_badge.update_status("error", "Title is required")
            self._create_badge.pack(anchor="w")
            return

        desc = self._new_desc_box.get("1.0", "end").strip()
        labels_raw = self._new_labels_entry.get().strip()
        assignees_raw = self._new_assignees_entry.get().strip()

        self._create_badge.update_status("pending", "Creating…")
        self._create_badge.pack(anchor="w")

        def _do():
            owner, repo = self._owner, self._repo
            if self._platform == "github":
                api = self.app_state.get("github_api")
                labels = [l.strip() for l in labels_raw.split(",") if l.strip()] if labels_raw else None
                assignees = [a.strip() for a in assignees_raw.split(",") if a.strip()] if assignees_raw else None
                ok, data = api.create_issue(owner, repo, title, body=desc, labels=labels, assignees=assignees)
            else:
                api = self.app_state.get("gitlab_api")
                ok, data = api.create_issue(owner, repo, title, description=desc, labels=labels_raw)

            if ok:
                self.after(0, lambda: self._create_badge.update_status("ok", "Issue created!"))
                self.after(0, lambda: self._new_title_entry.delete(0, "end"))
                self.after(0, lambda: self._new_desc_box.delete("1.0", "end"))
                self.after(0, lambda: threading.Thread(
                    target=self._do_load_issues, daemon=True).start())
            else:
                msg = str(data) if data else "Failed"
                self.after(0, lambda: self._create_badge.update_status("error", msg))

        threading.Thread(target=_do, daemon=True).start()
