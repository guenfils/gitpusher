"""Panel – Tags & Releases."""
import re
import threading
from tkinter import filedialog
import customtkinter as ctk
from ui.theme import *
from ui.widgets.common import Card, PrimaryButton, SecondaryButton, Label, StatusBadge, LogBox
from core.git_manager import GitManager


def _bump_version(tag_name, part):
    """Increment a version tag. part: 'major', 'minor', 'patch'."""
    clean = tag_name.lstrip("v").lstrip("V")
    parts = clean.split(".")
    while len(parts) < 3:
        parts.append("0")
    try:
        major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
    except ValueError:
        return tag_name
    if part == "major":
        major += 1
        minor = 0
        patch = 0
    elif part == "minor":
        minor += 1
        patch = 0
    else:
        patch += 1
    prefix = "v" if tag_name.startswith(("v", "V")) else ""
    return f"{prefix}{major}.{minor}.{patch}"


class PanelTags(ctk.CTkFrame):
    def __init__(self, master, app_state, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app_state = app_state
        self._git = GitManager()
        self._repo_path = None
        self._tags = []

        self._build_ui()

    def _build_ui(self):
        # Title
        Label(self, text="Tags & Releases", size=18, bold=True).pack(anchor="w", pady=(0, 4))
        Label(self, text="Version your project and publish releases", size=12, color=TEXT_DIM).pack(anchor="w", pady=(0, PAD))

        # Card: Repository source
        repo_card = Card(self)
        repo_card.pack(fill="x", pady=(0, PAD_SM))

        Label(repo_card, text="Local Repository", size=13, bold=True).pack(anchor="w", padx=PAD, pady=(PAD_SM, 8))

        picker_row = ctk.CTkFrame(repo_card, fg_color="transparent")
        picker_row.pack(fill="x", padx=PAD, pady=(0, PAD_SM))

        self._path_var = ctk.StringVar()
        ctk.CTkEntry(
            picker_row, textvariable=self._path_var,
            placeholder_text="/path/to/your/repo",
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            placeholder_text_color=TEXT_MUTED, corner_radius=8, height=38,
            font=ctk.CTkFont(family="Inter", size=12),
        ).pack(side="left", fill="x", expand=True, padx=(0, 8))

        SecondaryButton(picker_row, text="Browse", width=90, height=38, command=self._browse_repo).pack(side="left", padx=(0, 8))
        SecondaryButton(picker_row, text="Load", width=80, height=38, command=self._load_repo).pack(side="left")

        self._repo_status = StatusBadge(repo_card, status="pending", text="")
        self._repo_status.pack(anchor="w", padx=PAD, pady=(0, PAD_SM))

        # Card: Existing tags
        tags_card = Card(self)
        tags_card.pack(fill="x", pady=(0, PAD_SM))

        tags_header = ctk.CTkFrame(tags_card, fg_color="transparent")
        tags_header.pack(fill="x", padx=PAD, pady=(PAD_SM, 8))
        Label(tags_header, text="Existing Tags", size=13, bold=True).pack(side="left")
        SecondaryButton(tags_header, text="Refresh", width=80, height=30, command=self._refresh_tags).pack(side="right")

        self._tags_list = ctk.CTkScrollableFrame(
            tags_card, fg_color=BG3, corner_radius=8, height=160,
            scrollbar_button_color=BG3, scrollbar_button_hover_color=BORDER,
        )
        self._tags_list.pack(fill="x", padx=PAD, pady=(0, PAD_SM))

        self._no_tags_label = Label(self._tags_list, text="No tags yet", size=11, color=TEXT_DIM)
        self._no_tags_label.pack(pady=PAD_SM)

        # Card: Create Tag
        create_card = Card(self)
        create_card.pack(fill="x", pady=(0, PAD_SM))

        Label(create_card, text="Create Tag", size=13, bold=True).pack(anchor="w", padx=PAD, pady=(PAD_SM, 8))

        # Tag name + bump buttons
        tag_row = ctk.CTkFrame(create_card, fg_color="transparent")
        tag_row.pack(fill="x", padx=PAD, pady=(0, 6))

        self._tag_name_var = ctk.StringVar(value="v1.0.0")
        ctk.CTkEntry(
            tag_row, textvariable=self._tag_name_var,
            placeholder_text="v1.0.0",
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            placeholder_text_color=TEXT_MUTED, corner_radius=8, height=38,
            font=ctk.CTkFont(family="Inter", size=12),
        ).pack(side="left", fill="x", expand=True, padx=(0, 8))

        for label, part in (("+Major", "major"), ("+Minor", "minor"), ("+Patch", "patch")):
            _part = part
            SecondaryButton(
                tag_row, text=label, width=75, height=38,
                command=lambda p=_part: self._bump(p),
            ).pack(side="left", padx=(0, 4))

        # Reference
        Label(create_card, text="Reference (branch or commit)", size=11, color=TEXT_DIM).pack(anchor="w", padx=PAD)
        self._ref_var = ctk.StringVar(value="HEAD")
        ctk.CTkEntry(
            create_card, textvariable=self._ref_var,
            placeholder_text="HEAD or branch name",
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            placeholder_text_color=TEXT_MUTED, corner_radius=8, height=36,
            font=ctk.CTkFont(family="Inter", size=12),
        ).pack(fill="x", padx=PAD, pady=(4, 6))

        # Message
        Label(create_card, text="Message (optional)", size=11, color=TEXT_DIM).pack(anchor="w", padx=PAD)
        self._tag_msg_var = ctk.StringVar()
        ctk.CTkEntry(
            create_card, textvariable=self._tag_msg_var,
            placeholder_text="Release notes...",
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            placeholder_text_color=TEXT_MUTED, corner_radius=8, height=36,
            font=ctk.CTkFont(family="Inter", size=12),
        ).pack(fill="x", padx=PAD, pady=(4, 8))

        # Tag action buttons
        tag_actions = ctk.CTkFrame(create_card, fg_color="transparent")
        tag_actions.pack(fill="x", padx=PAD, pady=(0, 8))

        SecondaryButton(tag_actions, text="Create Tag Locally", command=self._create_tag_local).pack(side="left", padx=(0, 8))

        push_row = ctk.CTkFrame(create_card, fg_color="transparent")
        push_row.pack(fill="x", padx=PAD, pady=(0, 8))

        SecondaryButton(push_row, text="Push Tags", command=self._push_tags).pack(side="left", padx=(0, 12))

        self._push_github = ctk.BooleanVar(value=bool(self.app_state.get("github_api")))
        self._push_gitlab = ctk.BooleanVar(value=bool(self.app_state.get("gitlab_api")))

        if self.app_state.get("github_api"):
            ctk.CTkCheckBox(
                push_row, text="GitHub", variable=self._push_github,
                fg_color=PRIMARY, hover_color=PRIMARY_H,
                text_color=TEXT, font=ctk.CTkFont(family="Inter", size=12),
            ).pack(side="left", padx=(0, 8))

        if self.app_state.get("gitlab_api"):
            ctk.CTkCheckBox(
                push_row, text="GitLab", variable=self._push_gitlab,
                fg_color=PRIMARY, hover_color=PRIMARY_H,
                text_color=TEXT, font=ctk.CTkFont(family="Inter", size=12),
            ).pack(side="left")

        self._tag_badge = StatusBadge(create_card, status="pending", text="")
        self._tag_badge.pack(anchor="w", padx=PAD, pady=(0, PAD_SM))

        # Card: Create Release
        rel_card = Card(self)
        rel_card.pack(fill="x", pady=(0, PAD_SM))

        Label(rel_card, text="Create Release", size=13, bold=True).pack(anchor="w", padx=PAD, pady=(PAD_SM, 8))

        Label(rel_card, text="Tag", size=11, color=TEXT_DIM).pack(anchor="w", padx=PAD)
        self._rel_tag_var = ctk.StringVar()
        self._rel_tag_combo = ctk.CTkComboBox(
            rel_card, variable=self._rel_tag_var, values=["(load a repo first)"],
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            button_color=BG3, button_hover_color=BORDER,
            dropdown_fg_color=BG2, dropdown_text_color=TEXT,
            corner_radius=8, height=36,
            font=ctk.CTkFont(family="Inter", size=12),
            command=self._on_tag_selected,
        )
        self._rel_tag_combo.pack(fill="x", padx=PAD, pady=(4, 6))

        Label(rel_card, text="Release title", size=11, color=TEXT_DIM).pack(anchor="w", padx=PAD)
        self._rel_title_var = ctk.StringVar()
        ctk.CTkEntry(
            rel_card, textvariable=self._rel_title_var,
            placeholder_text="Release title",
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            placeholder_text_color=TEXT_MUTED, corner_radius=8, height=36,
            font=ctk.CTkFont(family="Inter", size=12),
        ).pack(fill="x", padx=PAD, pady=(4, 6))

        Label(rel_card, text="Release notes", size=11, color=TEXT_DIM).pack(anchor="w", padx=PAD)
        self._rel_notes = ctk.CTkTextbox(
            rel_card, fg_color=BG3, text_color=TEXT, border_color=BORDER,
            border_width=1, corner_radius=8, height=80,
            font=ctk.CTkFont(family="Inter", size=12),
        )
        self._rel_notes.pack(fill="x", padx=PAD, pady=(4, 8))

        prerel_row = ctk.CTkFrame(rel_card, fg_color="transparent")
        prerel_row.pack(fill="x", padx=PAD, pady=(0, 8))
        self._prerelease_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            prerel_row, text="Pre-release", variable=self._prerelease_var,
            fg_color=PRIMARY, hover_color=PRIMARY_H,
            text_color=TEXT, font=ctk.CTkFont(family="Inter", size=12),
        ).pack(side="left")

        PrimaryButton(rel_card, text="Publish Release", command=self._publish_release).pack(fill="x", padx=PAD, pady=(0, 8))

        rel_badges = ctk.CTkFrame(rel_card, fg_color="transparent")
        rel_badges.pack(fill="x", padx=PAD, pady=(0, PAD_SM))
        self._gh_rel_badge = StatusBadge(rel_badges, status="pending", text="")
        self._gh_rel_badge.pack(side="left", padx=(0, 8))
        self._gl_rel_badge = StatusBadge(rel_badges, status="pending", text="")
        self._gl_rel_badge.pack(side="left")

        # Log
        self._log = LogBox(self, height=100)
        self._log.pack(fill="x", pady=(0, PAD_SM))

    def _browse_repo(self):
        folder = filedialog.askdirectory(title="Select local repository")
        if folder:
            self._path_var.set(folder)

    def _load_repo(self):
        path = self._path_var.get().strip()
        if not path:
            self._repo_status.update_status("error", "Select a folder first")
            return
        if not self._git.is_git_repo(path):
            self._repo_status.update_status("error", "Not a git repository")
            return
        self._repo_path = path
        self._repo_status.update_status("ok", f"Loaded")
        self._refresh_tags()

    def _refresh_tags(self):
        if not self._repo_path:
            return
        self._tags = self._git.get_tags(self._repo_path)
        self._render_tags()
        # Update release combo
        names = [t["name"] for t in self._tags]
        self._rel_tag_combo.configure(values=names if names else ["(no tags)"])
        if names:
            self._rel_tag_var.set(names[0])
            self._rel_title_var.set(names[0])
        # Suggest next version in tag entry
        if self._tags:
            latest = self._tags[0]["name"]
            self._tag_name_var.set(_bump_version(latest, "patch"))

    def _render_tags(self):
        for w in self._tags_list.winfo_children():
            w.destroy()
        if not self._tags:
            Label(self._tags_list, text="No tags yet", size=11, color=TEXT_DIM).pack(pady=PAD_SM)
            return
        for tag in self._tags:
            row = ctk.CTkFrame(self._tags_list, fg_color="transparent")
            row.pack(fill="x", pady=2)
            Label(row, text=tag["name"], size=12, bold=True).pack(side="left", padx=(PAD_SM, PAD_SM))
            if tag["date"]:
                Label(row, text=tag["date"], size=10, color=TEXT_DIM).pack(side="left", padx=(0, PAD_SM))
            if tag["message"]:
                msg = tag["message"][:50] + "..." if len(tag["message"]) > 50 else tag["message"]
                Label(row, text=msg, size=10, color=TEXT_MUTED).pack(side="left")

    def _bump(self, part):
        current = self._tag_name_var.get().strip()
        if not current:
            current = "v0.0.0"
        self._tag_name_var.set(_bump_version(current, part))

    def _create_tag_local(self):
        if not self._repo_path:
            self._tag_badge.update_status("error", "Load a repository first")
            return
        tag_name = self._tag_name_var.get().strip()
        if not tag_name:
            self._tag_badge.update_status("error", "Enter a tag name")
            return
        message = self._tag_msg_var.get().strip() or None
        ok, output = self._git.create_tag(self._repo_path, tag_name, message=message)
        self._log.append(output if output.strip() else f"Tag {tag_name} created")
        if ok:
            self._tag_badge.update_status("ok", f"Tag {tag_name} created locally")
            self._refresh_tags()
        else:
            self._tag_badge.update_status("error", "Failed to create tag")

    def _push_tags(self):
        if not self._repo_path:
            self._tag_badge.update_status("error", "Load a repository first")
            return

        self._tag_badge.update_status("pending", "Pushing tags...")
        self._log.clear()

        def _run():
            any_ok = False
            errors = []
            if self._push_github.get() and self.app_state.get("github_api"):
                token = self.app_state.get("github_token", "")
                env = {"GIT_ASKPASS": "echo", "GIT_USERNAME": "x-token", "GIT_PASSWORD": token} if token else None
                ok, out = self._git.push_tags(self._repo_path, "origin", env=env)
                self.after(0, lambda o=out: self._log.append(f"GitHub tags: {o}"))
                if ok:
                    any_ok = True
                else:
                    errors.append("GitHub")

            if self._push_gitlab.get() and self.app_state.get("gitlab_api"):
                token = self.app_state.get("gitlab_token", "")
                env = {"GIT_ASKPASS": "echo", "GIT_USERNAME": "oauth2", "GIT_PASSWORD": token} if token else None
                ok, out = self._git.push_tags(self._repo_path, "gitlab", env=env)
                self.after(0, lambda o=out: self._log.append(f"GitLab tags: {o}"))
                if ok:
                    any_ok = True
                else:
                    errors.append("GitLab")

            def _update():
                if any_ok and not errors:
                    self._tag_badge.update_status("ok", "Tags pushed")
                elif any_ok:
                    self._tag_badge.update_status("warning", "Partial: " + ", ".join(errors) + " failed")
                else:
                    self._tag_badge.update_status("error", "Push failed")
            self.after(0, _update)

        threading.Thread(target=_run, daemon=True).start()

    def _on_tag_selected(self, choice):
        self._rel_title_var.set(choice)

    def _publish_release(self):
        tag_name = self._rel_tag_var.get().strip()
        title = self._rel_title_var.get().strip() or tag_name
        notes = self._rel_notes.get("1.0", "end").strip()
        prerelease = self._prerelease_var.get()

        if not tag_name or tag_name in ("(load a repo first)", "(no tags)"):
            self._gh_rel_badge.update_status("error", "Select a tag")
            return

        self._gh_rel_badge.update_status("pending", "Publishing...")
        self._gl_rel_badge.update_status("pending", "")
        self._log.clear()
        self._log.append(f"Publishing release {tag_name}...")

        def _run():
            gh_api = self.app_state.get("github_api")
            gl_api = self.app_state.get("gitlab_api")
            gh_user = self.app_state.get("github_user", {})
            gl_user = self.app_state.get("gitlab_user", {})

            if gh_api and self._push_github.get():
                owner = gh_user.get("login", "") if isinstance(gh_user, dict) else ""
                # Try to get repo name from remote URL
                remote_url = self._git.get_remote_url(self._repo_path) if self._repo_path else ""
                repo_name = _extract_repo_name(remote_url) if remote_url else ""
                if owner and repo_name:
                    ok, result = gh_api.create_release(owner, repo_name, tag_name, title, body=notes, prerelease=prerelease)
                    def _gh_update(o=ok, r=result):
                        if o:
                            self._gh_rel_badge.update_status("ok", "GitHub: Published")
                            self._log.append(f"GitHub release: {r.get('html_url', '')}")
                        else:
                            self._gh_rel_badge.update_status("error", f"GitHub: {r}")
                    self.after(0, _gh_update)
                else:
                    self.after(0, lambda: self._gh_rel_badge.update_status("error", "GitHub: owner/repo unknown"))
            else:
                self.after(0, lambda: self._gh_rel_badge.update_status("pending", ""))

            if gl_api and self._push_gitlab.get():
                owner = gl_user.get("username", "") if isinstance(gl_user, dict) else ""
                remote_url = self._git.get_remote_url(self._repo_path) if self._repo_path else ""
                repo_name = _extract_repo_name(remote_url) if remote_url else ""
                if owner and repo_name:
                    ok, result = gl_api.create_release(owner, repo_name, tag_name, title, description=notes)
                    def _gl_update(o=ok, r=result):
                        if o:
                            self._gl_rel_badge.update_status("ok", "GitLab: Published")
                        else:
                            self._gl_rel_badge.update_status("error", f"GitLab: {r}")
                    self.after(0, _gl_update)
                else:
                    self.after(0, lambda: self._gl_rel_badge.update_status("error", "GitLab: owner/repo unknown"))

        threading.Thread(target=_run, daemon=True).start()


def _extract_repo_name(url):
    """Extract repo name from a git remote URL."""
    url = url.rstrip("/").rstrip(".git")
    parts = url.replace(":", "/").split("/")
    if len(parts) >= 1:
        return parts[-1]
    return ""
