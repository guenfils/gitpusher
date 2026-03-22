"""Panel – Collaborator / Member Management."""
import threading
import customtkinter as ctk
from ui.theme import *
from ui.widgets.common import Card, PrimaryButton, SecondaryButton, Label, StatusBadge, SectionHeader


# Permission display mapping
_GH_PERM_LABEL = {"admin": "Admin", "push": "Developer", "pull": "Reporter", "maintain": "Maintainer", "triage": "Triage"}
_GH_PERM_COLOR = {"admin": ERROR, "maintain": WARNING, "push": PRIMARY, "triage": BG3, "pull": BG3}
_GL_LEVEL_LABEL = {10: "Guest", 20: "Reporter", 30: "Developer", 40: "Maintainer", 50: "Owner"}
_GL_LEVEL_COLOR = {50: ERROR, 40: WARNING, 30: PRIMARY, 20: BG3, 10: BG3}


def _pill(master, text, bg, fg=WHITE):
    return ctk.CTkLabel(
        master, text=text,
        fg_color=bg, text_color=fg,
        corner_radius=6, padx=6, pady=2,
        font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
    )


class _ConfirmDialog(ctk.CTkToplevel):
    def __init__(self, master, message, on_confirm):
        super().__init__(master)
        self.title("Confirm")
        self.resizable(False, False)
        self.grab_set()
        self.configure(fg_color=BG2)

        ctk.CTkLabel(
            self, text=message,
            font=ctk.CTkFont(family="Inter", size=13),
            text_color=TEXT, wraplength=320,
        ).pack(padx=PAD, pady=PAD)

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(padx=PAD, pady=(0, PAD), fill="x")
        SecondaryButton(btn_row, text="Cancel", width=110, height=36,
                        command=self.destroy).pack(side="left", padx=(0, PAD_SM))
        PrimaryButton(btn_row, text="Confirm", width=110, height=36,
                      fg_color=ERROR, hover_color="#DC2626",
                      command=lambda: (on_confirm(), self.destroy())).pack(side="left")


class PanelCollaborators(ctk.CTkFrame):
    def __init__(self, master, app_state, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app_state = app_state
        self._platform = None
        self._owner = ""
        self._repo = ""
        self._collaborators = []
        self._invitations = []
        self._found_gl_user = None  # for GitLab user search result

        self._build_ui()

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build_ui(self):
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True)
        self._scroll = scroll

        # ── Title ──────────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(scroll, fg_color="transparent")
        hdr.pack(fill="x", padx=PAD, pady=(PAD, 0))
        Label(hdr, text="Collaborators", size=22, bold=True).pack(anchor="w")
        Label(hdr, text="Manage who has access to your repositories",
              size=12, color=TEXT_DIM).pack(anchor="w")

        # ── Check if any platform is connected ─────────────────────────────
        has_gh = bool(self.app_state.get("github_api"))
        has_gl = bool(self.app_state.get("gitlab_api"))

        if not has_gh and not has_gl:
            warn = Card(scroll)
            warn.pack(fill="x", padx=PAD, pady=PAD)
            Label(warn, text="Connect a platform first (Push Mode -> Platform Auth)",
                  size=13, color=WARNING).pack(padx=PAD, pady=PAD)
            return

        # ── Platform selector card ──────────────────────────────────────────
        plat_card = Card(scroll)
        plat_card.pack(fill="x", padx=PAD, pady=(PAD_SM, 0))
        plat_inner = ctk.CTkFrame(plat_card, fg_color="transparent")
        plat_inner.pack(padx=PAD, pady=PAD, fill="x")

        Label(plat_inner, text="Platform:", size=12, bold=True).pack(side="left", padx=(0, PAD_SM))

        self._plat_btns = {}
        for p in ([("GitHub", "github")] if has_gh else []) + ([("GitLab", "gitlab")] if has_gl else []):
            label, key = p
            b = ctk.CTkButton(
                plat_inner, text=label, width=90, height=32,
                corner_radius=8,
                fg_color=BG3, text_color=TEXT_DIM,
                hover_color=BG3,
                font=ctk.CTkFont(family="Inter", size=12),
                command=lambda k=key: self._set_platform(k),
            )
            b.pack(side="left", padx=(0, PAD_SM))
            self._plat_btns[key] = b

        # ── Repo entry row ──────────────────────────────────────────────────
        repo_row = ctk.CTkFrame(plat_card, fg_color="transparent")
        repo_row.pack(padx=PAD, pady=(0, PAD), fill="x")
        Label(repo_row, text="Repository (owner/repo):", size=12).pack(side="left", padx=(0, PAD_SM))
        self._repo_entry = ctk.CTkEntry(
            repo_row, width=280, placeholder_text="owner/repo-name",
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            placeholder_text_color=TEXT_MUTED, corner_radius=8, height=36,
            font=ctk.CTkFont(family="Inter", size=12),
        )
        self._repo_entry.pack(side="left", padx=(0, PAD_SM))
        PrimaryButton(repo_row, text="Load", width=100, height=36,
                      command=self._on_load).pack(side="left")

        self._load_badge = StatusBadge(plat_card, status="pending", text="")
        self._load_badge.pack(padx=PAD, pady=(0, PAD_SM), anchor="w")

        # ── Collaborators list card (hidden initially) ─────────────────────
        self._collab_card = Card(scroll)
        self._collab_card.pack(fill="x", padx=PAD, pady=(PAD_SM, 0))
        self._collab_card.pack_forget()

        SectionHeader(self._collab_card, number="👥", title="Current Collaborators").pack(
            padx=PAD, pady=(PAD, PAD_SM), fill="x")

        self._collab_list = ctk.CTkScrollableFrame(self._collab_card, height=200, fg_color=BG)
        self._collab_list.pack(padx=PAD, pady=(0, PAD), fill="x")

        # ── Pending Invitations card (GitHub only, hidden initially) ────────
        self._inv_card = Card(scroll)
        self._inv_card.pack(fill="x", padx=PAD, pady=(PAD_SM, 0))
        self._inv_card.pack_forget()

        SectionHeader(self._inv_card, number="✉", title="Pending Invitations",
                      subtitle="(not yet accepted)").pack(padx=PAD, pady=(PAD, PAD_SM), fill="x")
        self._inv_list = ctk.CTkScrollableFrame(self._inv_card, height=100, fg_color=BG)
        self._inv_list.pack(padx=PAD, pady=(0, PAD), fill="x")

        # ── Add Collaborator card ───────────────────────────────────────────
        add_card = Card(scroll)
        add_card.pack(fill="x", padx=PAD, pady=(PAD_SM, PAD))
        SectionHeader(add_card, number="+", title="Add Collaborator / Member").pack(
            padx=PAD, pady=(PAD, PAD_SM), fill="x")

        add_inner = ctk.CTkFrame(add_card, fg_color="transparent")
        add_inner.pack(padx=PAD, pady=(0, PAD), fill="x")

        # Username row
        usr_row = ctk.CTkFrame(add_inner, fg_color="transparent")
        usr_row.pack(fill="x", pady=(0, PAD_SM))
        Label(usr_row, text="Username:", size=12).pack(side="left", padx=(0, PAD_SM))
        self._new_user_entry = ctk.CTkEntry(
            usr_row, width=220, placeholder_text="github-username",
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            placeholder_text_color=TEXT_MUTED, corner_radius=8, height=36,
            font=ctk.CTkFont(family="Inter", size=12),
        )
        self._new_user_entry.pack(side="left", padx=(0, PAD_SM))
        self._find_user_btn = PrimaryButton(
            usr_row, text="Find User", width=100, height=36,
            command=self._find_gl_user,
        )
        # Only shown for GitLab

        # Found user result label (GitLab)
        self._gl_user_result = Label(add_inner, text="", size=11, color=TEXT_DIM)
        self._gl_user_result.pack(anchor="w")
        self._gl_user_result.pack_forget()

        # Permission row
        perm_row = ctk.CTkFrame(add_inner, fg_color="transparent")
        perm_row.pack(fill="x", pady=(0, PAD_SM))
        Label(perm_row, text="Permission:", size=12).pack(side="left", padx=(0, PAD_SM))
        self._perm_label_widget = Label(perm_row, text="Permission:", size=12)

        self._gh_perm_menu = ctk.CTkOptionMenu(
            perm_row, values=["pull", "push", "admin"], width=160,
            fg_color=BG3, button_color=BG3, button_hover_color=BORDER,
            text_color=TEXT, font=ctk.CTkFont(family="Inter", size=12),
        )
        self._gh_perm_menu.pack(side="left")

        self._gl_access_menu = ctk.CTkOptionMenu(
            perm_row, values=["Reporter (20)", "Developer (30)", "Maintainer (40)"], width=180,
            fg_color=BG3, button_color=BG3, button_hover_color=BORDER,
            text_color=TEXT, font=ctk.CTkFont(family="Inter", size=12),
        )

        # Add button
        PrimaryButton(add_inner, text="Invite / Add", height=40,
                      command=self._add).pack(fill="x", pady=(PAD_SM, 0))
        self._add_badge = StatusBadge(add_inner, status="pending", text="")
        self._add_badge.pack(anchor="w", pady=(PAD_SM, 0))
        self._add_badge.pack_forget()

        # Select default platform
        default = "github" if has_gh else "gitlab"
        self._set_platform(default)

    # ── Platform switching ─────────────────────────────────────────────────

    def _set_platform(self, p):
        self._platform = p
        for key, btn in self._plat_btns.items():
            if key == p:
                btn.configure(fg_color=PRIMARY, text_color=WHITE, hover_color=PRIMARY_H)
            else:
                btn.configure(fg_color=BG3, text_color=TEXT_DIM, hover_color=BG3)

        # Clear lists
        self._collaborators = []
        self._invitations = []
        self._collab_card.pack_forget()
        self._inv_card.pack_forget()
        self._load_badge.configure(text="")

        # Toggle UI elements
        if p == "github":
            self._find_user_btn.pack_forget()
            self._gl_user_result.pack_forget()
            self._gl_access_menu.pack_forget()
            self._gh_perm_menu.pack(side="left")
        else:
            self._gh_perm_menu.pack_forget()
            self._find_user_btn.pack(side="left")
            self._gl_access_menu.pack(side="left")

    # ── Load collaborators ─────────────────────────────────────────────────

    def _on_load(self):
        raw = self._repo_entry.get().strip()
        if "/" not in raw:
            self._load_badge.update_status("error", "Format: owner/repo")
            return
        parts = raw.split("/", 1)
        self._owner, self._repo = parts[0].strip(), parts[1].strip()
        self._load_badge.update_status("pending", "Loading…")
        threading.Thread(target=self._load, daemon=True).start()

    def _load(self):
        owner, repo = self._owner, self._repo
        if self._platform == "github":
            api = self.app_state.get("github_api")
            ok, data = api.list_collaborators(owner, repo)
            invs = []
            if ok:
                ok_inv, invs = api.list_invitations(owner, repo)
            self.after(0, lambda o=ok, d=data, iv=invs: self._on_loaded_gh(o, d, iv))
        else:
            api = self.app_state.get("gitlab_api")
            ok, data = api.list_members(owner, repo)
            self.after(0, lambda o=ok, d=data: self._on_loaded_gl(o, d))

    def _on_loaded_gh(self, ok, data, invitations):
        if ok:
            self._collaborators = data
            self._invitations = invitations if isinstance(invitations, list) else []
            self._load_badge.update_status("ok", f"Loaded {len(data)} collaborator(s)")
            self._render_list(data)
            self._render_invitations(self._invitations)
        else:
            self._load_badge.update_status("error", str(data))

    def _on_loaded_gl(self, ok, data):
        if ok:
            self._collaborators = data
            self._load_badge.update_status("ok", f"Loaded {len(data)} member(s)")
            self._render_list(data)
        else:
            self._load_badge.update_status("error", str(data))

    # ── Render list ────────────────────────────────────────────────────────

    def _render_list(self, items):
        for w in self._collab_list.winfo_children():
            w.destroy()

        self._collab_card.pack(fill="x", padx=PAD, pady=(PAD_SM, 0))

        for item in items:
            if self._platform == "github":
                username = item.get("login", "?")
                perm_key = item.get("role_name") or item.get("permissions", {})
                if isinstance(perm_key, dict):
                    if perm_key.get("admin"):
                        perm_key = "admin"
                    elif perm_key.get("push"):
                        perm_key = "push"
                    else:
                        perm_key = "pull"
                perm_label = _GH_PERM_LABEL.get(perm_key, str(perm_key))
                perm_color = _GH_PERM_COLOR.get(perm_key, BG3)
                remove_id = username
            else:
                username = item.get("username") or item.get("name", "?")
                level = item.get("access_level", 30)
                perm_label = _GL_LEVEL_LABEL.get(level, str(level))
                perm_color = _GL_LEVEL_COLOR.get(level, BG3)
                remove_id = item.get("id", username)

            row = ctk.CTkFrame(self._collab_list, fg_color="transparent")
            row.pack(fill="x", pady=2)

            # Avatar
            ctk.CTkLabel(
                row, text=username[0].upper(),
                width=32, height=32, corner_radius=16,
                fg_color=PRIMARY, text_color=WHITE,
                font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
            ).pack(side="left", padx=(0, PAD_SM))

            # Name + badge
            info = ctk.CTkFrame(row, fg_color="transparent")
            info.pack(side="left", fill="x", expand=True)
            Label(info, text=username, size=13, bold=True).pack(anchor="w")
            _pill(info, perm_label, perm_color).pack(anchor="w")

            # Remove button
            SecondaryButton(
                row, text="Remove", width=80, height=28,
                fg_color="#7F1D1D", text_color=WHITE, hover_color=ERROR,
                command=lambda uid=remove_id, un=username: self._remove(uid, un),
            ).pack(side="right", padx=(PAD_SM, 0))

    def _render_invitations(self, invitations):
        for w in self._inv_list.winfo_children():
            w.destroy()

        if not invitations:
            self._inv_card.pack_forget()
            return

        self._inv_card.pack(fill="x", padx=PAD, pady=(PAD_SM, 0))
        for inv in invitations:
            invitee = inv.get("invitee") or {}
            login = invitee.get("login", "?")
            inv_id = inv.get("id")
            row = ctk.CTkFrame(self._inv_list, fg_color="transparent")
            row.pack(fill="x", pady=2)
            Label(row, text=login, size=12, bold=True).pack(side="left")
            SecondaryButton(
                row, text="Cancel", width=80, height=28,
                command=lambda iid=inv_id: self._cancel_invitation(iid),
            ).pack(side="right")

    # ── Remove ─────────────────────────────────────────────────────────────

    def _remove(self, uid, username):
        _ConfirmDialog(
            self,
            message=f"Remove {username}? This cannot be undone.",
            on_confirm=lambda: threading.Thread(
                target=self._do_remove, args=(uid, username), daemon=True
            ).start(),
        )

    def _do_remove(self, uid, username):
        owner, repo = self._owner, self._repo
        if self._platform == "github":
            api = self.app_state.get("github_api")
            ok, _ = api.remove_collaborator(owner, repo, uid)
        else:
            api = self.app_state.get("gitlab_api")
            ok, _ = api.remove_member(owner, repo, uid)

        if ok:
            self.after(0, lambda: self._load_badge.update_status("ok", f"Removed {username}"))
            self.after(0, lambda: threading.Thread(target=self._load, daemon=True).start())
        else:
            self.after(0, lambda: self._load_badge.update_status("error", f"Failed to remove {username}"))

    def _cancel_invitation(self, inv_id):
        def _do():
            api = self.app_state.get("github_api")
            ok, _ = api.cancel_invitation(self._owner, self._repo, inv_id)
            self.after(0, lambda: threading.Thread(target=self._load, daemon=True).start())
        threading.Thread(target=_do, daemon=True).start()

    # ── GitLab user search ─────────────────────────────────────────────────

    def _find_gl_user(self):
        username = self._new_user_entry.get().strip()
        if not username:
            return
        self._gl_user_result.configure(text="Searching…")
        self._gl_user_result.pack(anchor="w")
        self._found_gl_user = None

        def _do():
            api = self.app_state.get("gitlab_api")
            ok, results = api.search_user(username)
            if ok and results:
                u = results[0]
                name = u.get("username", "?")
                uid = u.get("id")
                self._found_gl_user = u
                self.after(0, lambda: self._gl_user_result.configure(
                    text=f"Found: {name} (ID: {uid}) — will be used for Add"))
            else:
                self.after(0, lambda: self._gl_user_result.configure(text="No user found"))

        threading.Thread(target=_do, daemon=True).start()

    # ── Add ────────────────────────────────────────────────────────────────

    def _add(self):
        if not self._owner or not self._repo:
            self._add_badge.update_status("error", "Load a repository first")
            self._add_badge.pack(anchor="w", pady=(PAD_SM, 0))
            return

        username = self._new_user_entry.get().strip()
        if not username:
            self._add_badge.update_status("error", "Enter a username")
            self._add_badge.pack(anchor="w", pady=(PAD_SM, 0))
            return

        self._add_badge.update_status("pending", "Adding…")
        self._add_badge.pack(anchor="w", pady=(PAD_SM, 0))

        if self._platform == "github":
            perm = self._gh_perm_menu.get()
            threading.Thread(target=self._do_add_gh, args=(username, perm), daemon=True).start()
        else:
            sel = self._gl_access_menu.get()
            level_map = {"Reporter (20)": 20, "Developer (30)": 30, "Maintainer (40)": 40}
            level = level_map.get(sel, 30)
            user_id = None
            if self._found_gl_user:
                user_id = self._found_gl_user.get("id")
            if not user_id:
                self._add_badge.update_status("error", "Use 'Find User' to locate the GitLab user first")
                return
            threading.Thread(target=self._do_add_gl, args=(user_id, level, username), daemon=True).start()

    def _do_add_gh(self, username, permission):
        api = self.app_state.get("github_api")
        ok, data = api.add_collaborator(self._owner, self._repo, username, permission)
        if ok:
            self.after(0, lambda: self._add_badge.update_status("ok", f"Invited {username}"))
            self.after(0, lambda: threading.Thread(target=self._load, daemon=True).start())
        else:
            msg = str(data) if data else "Failed"
            self.after(0, lambda: self._add_badge.update_status("error", msg))

    def _do_add_gl(self, user_id, access_level, username):
        api = self.app_state.get("gitlab_api")
        ok, data = api.add_member(self._owner, self._repo, user_id, access_level)
        if ok:
            self.after(0, lambda: self._add_badge.update_status("ok", f"Added {username}"))
            self.after(0, lambda: threading.Thread(target=self._load, daemon=True).start())
        else:
            msg = str(data) if data else "Failed"
            self.after(0, lambda: self._add_badge.update_status("error", msg))
