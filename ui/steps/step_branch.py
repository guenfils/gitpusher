"""Step 4 – Branch and target selection."""
import customtkinter as ctk
from ui.theme import *
from ui.widgets.common import (
    Card, PrimaryButton, SecondaryButton, Label, SectionHeader
)
from core.git_manager import GitManager


BRANCH_PRESETS = [
    ("main",    "Default branch for modern projects"),
    ("master",  "Traditional default branch name"),
    ("develop", "Development integration branch"),
    ("staging", "Pre-production staging branch"),
]


class StepBranch(ctk.CTkFrame):
    def __init__(self, master, app_state, on_next, on_back, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app_state = app_state
        self.on_next   = on_next
        self.on_back   = on_back
        self._selected_preset = ctk.StringVar(value="main")
        self._push_mode = ctk.StringVar(value="same")
        self._build()

    def _build(self):
        Label(self, text="Branch & Targets", size=22, bold=True).pack(anchor="w", pady=(0, 4))
        Label(self, text="Choose the branch name and which platforms to push to",
              size=13, color=TEXT_DIM).pack(anchor="w", pady=(0, PAD))

        is_repo = self.app_state.get("is_git_repo", False)
        path    = self.app_state.get("project_path", "")

        # Determine whether there are existing commits (for a git repo)
        has_commits = False
        if is_repo and path:
            has_commits = GitManager().has_commits(path)

        # ── Push Mode card (only for repos with commits) ───────────────────
        if is_repo and has_commits:
            self.app_state["push_mode"] = "same"  # default
            self._push_mode.set("same")
            self._build_push_mode_card()
        else:
            self.app_state["push_mode"] = "init"

        # ── Branch selector card ───────────────────────────────────────────
        self._branch_selector_frame = ctk.CTkFrame(self, fg_color="transparent")

        branch_card = Card(self._branch_selector_frame)
        branch_card.pack(fill="x", pady=(0, PAD_SM))
        SectionHeader(branch_card, "⑃", "Branch Name", "").pack(
            fill="x", padx=PAD, pady=(PAD, PAD_SM))

        preset_grid = ctk.CTkFrame(branch_card, fg_color="transparent")
        preset_grid.pack(fill="x", padx=PAD, pady=(0, PAD_SM))
        preset_grid.columnconfigure((0, 1), weight=1)

        self._preset_btns = {}
        for idx, (name, desc) in enumerate(BRANCH_PRESETS):
            row, col = divmod(idx, 2)
            btn_frame = ctk.CTkFrame(
                preset_grid,
                fg_color=BG3, corner_radius=8,
                border_width=2, border_color=BG3,
            )
            btn_frame.grid(row=row, column=col, padx=(0 if col == 0 else PAD_SM, 0),
                           pady=(0, PAD_SM), sticky="ew")
            btn_frame.bind("<Button-1>", lambda e, n=name: self._select_preset(n))

            Label(btn_frame, text=name, size=13, bold=True).pack(
                anchor="w", padx=PAD_SM, pady=(PAD_SM, 2))
            Label(btn_frame, text=desc, size=11, color=TEXT_DIM).pack(
                anchor="w", padx=PAD_SM, pady=(0, PAD_SM))

            for child in btn_frame.winfo_children():
                child.bind("<Button-1>", lambda e, n=name: self._select_preset(n))
            self._preset_btns[name] = btn_frame

        # Custom branch
        custom_row = ctk.CTkFrame(branch_card, fg_color="transparent")
        custom_row.pack(fill="x", padx=PAD, pady=(0, PAD))
        Label(custom_row, text="Custom:", size=12, color=TEXT_DIM).pack(side="left", padx=(0, 8))
        self._custom_var = ctk.StringVar()
        self._custom_entry = ctk.CTkEntry(
            custom_row, textvariable=self._custom_var,
            placeholder_text="feature/my-feature",
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            font=ctk.CTkFont(family="Inter", size=12), height=38, corner_radius=8, width=220,
        )
        self._custom_entry.pack(side="left")
        self._custom_entry.bind("<KeyRelease>", self._on_custom_type)

        # Select default preset
        self._select_preset("main")

        # Show or hide branch selector based on initial push mode
        if is_repo and has_commits:
            # "same" mode is default: hide branch selector
            pass  # _on_mode_change will handle visibility after targets/commit cards are packed
        else:
            self._branch_selector_frame.pack(fill="x")

        # ── Target platforms card ──────────────────────────────────────────
        self._target_card = Card(self)
        self._target_card.pack(fill="x", pady=(0, PAD_SM))
        SectionHeader(self._target_card, "☁", "Push Targets",
                      "Where to push — you can pick one or both").pack(
            fill="x", padx=PAD, pady=(PAD, PAD_SM))

        targets_row = ctk.CTkFrame(self._target_card, fg_color="transparent")
        targets_row.pack(fill="x", padx=PAD, pady=(0, PAD))

        self._push_github = ctk.BooleanVar(value=True)
        self._push_gitlab = ctk.BooleanVar(value=True)

        gh_available = "github_api" in self.app_state
        gl_available = "gitlab_api" in self.app_state

        self._gh_chk = ctk.CTkCheckBox(
            targets_row, text=f"GitHub  {'(' + self.app_state.get('github_user', '') + ')' if gh_available else '(not connected)'}",
            variable=self._push_github,
            state="normal" if gh_available else "disabled",
            font=ctk.CTkFont(family="Inter", size=13),
            text_color=TEXT if gh_available else TEXT_MUTED,
            fg_color=PRIMARY, hover_color=PRIMARY_H,
        )
        self._gh_chk.pack(side="left", padx=(0, PAD))
        if not gh_available:
            self._push_github.set(False)

        self._gl_chk = ctk.CTkCheckBox(
            targets_row, text=f"GitLab  {'(' + self.app_state.get('gitlab_user', '') + ')' if gl_available else '(not connected)'}",
            variable=self._push_gitlab,
            state="normal" if gl_available else "disabled",
            font=ctk.CTkFont(family="Inter", size=13),
            text_color=TEXT if gl_available else TEXT_MUTED,
            fg_color=PRIMARY, hover_color=PRIMARY_H,
        )
        self._gl_chk.pack(side="left")
        if not gl_available:
            self._push_gitlab.set(False)

        # ── Commit message card ────────────────────────────────────────────
        commit_card = Card(self)
        commit_card.pack(fill="x", pady=(0, PAD_SM))

        commit_label = "Commit Message" if (is_repo and has_commits) else "Commit Message"
        Label(commit_card, text=commit_label, size=13, bold=True).pack(
            anchor="w", padx=PAD, pady=(PAD, PAD_SM))

        default_msg = "Update" if (is_repo and has_commits) else "Initial commit"
        self._commit_var = ctk.StringVar(value=default_msg)
        ctk.CTkEntry(
            commit_card, textvariable=self._commit_var,
            placeholder_text=default_msg,
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            font=ctk.CTkFont(family="Inter", size=12), height=42, corner_radius=8,
        ).pack(fill="x", padx=PAD, pady=(0, PAD))

        # Now that all widgets are packed, apply initial mode visibility
        if is_repo and has_commits:
            self._on_mode_change()

        # ── Navigation ────────────────────────────────────────────────────
        nav = ctk.CTkFrame(self, fg_color="transparent")
        nav.pack(fill="x", pady=(PAD, 0))
        SecondaryButton(nav, text="← Back", command=self.on_back, width=120).pack(side="left")
        PrimaryButton(nav, text="Continue  →", command=self._next, width=180).pack(side="right")

    # ── Push Mode card ─────────────────────────────────────────────────────
    def _build_push_mode_card(self):
        current_branch = self.app_state.get("current_branch", "current branch")

        mode_card = Card(self)
        mode_card.pack(fill="x", pady=(0, PAD_SM))
        SectionHeader(mode_card, "⑂", "Push Mode", "").pack(
            fill="x", padx=PAD, pady=(PAD, PAD_SM))

        options_row = ctk.CTkFrame(mode_card, fg_color="transparent")
        options_row.pack(fill="x", padx=PAD, pady=(0, PAD))
        options_row.columnconfigure((0, 1), weight=1)

        # Option A — push to existing branch
        self._mode_frame_same = ctk.CTkFrame(
            options_row,
            fg_color=BG3, corner_radius=8,
            border_width=2, border_color=PRIMARY,   # selected by default
        )
        self._mode_frame_same.grid(row=0, column=0, padx=(0, PAD_SM // 2), sticky="ew")
        self._mode_frame_same.bind("<Button-1>", lambda e: self._set_mode("same"))

        self._radio_same = ctk.CTkRadioButton(
            self._mode_frame_same,
            text=f"Push to existing branch ({current_branch})",
            variable=self._push_mode, value="same",
            command=lambda: self._set_mode("same"),
            font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
            text_color=TEXT,
            fg_color=PRIMARY, hover_color=PRIMARY_H,
        )
        self._radio_same.pack(anchor="w", padx=PAD_SM, pady=(PAD_SM, 2))
        Label(self._mode_frame_same,
              text="Add new commits to the existing branch",
              size=11, color=TEXT_DIM).pack(anchor="w", padx=PAD_SM, pady=(0, PAD_SM))

        for child in self._mode_frame_same.winfo_children():
            child.bind("<Button-1>", lambda e: self._set_mode("same"))

        # Option B — push to a new branch
        self._mode_frame_new = ctk.CTkFrame(
            options_row,
            fg_color=BG3, corner_radius=8,
            border_width=2, border_color=BG3,       # not selected
        )
        self._mode_frame_new.grid(row=0, column=1, padx=(PAD_SM // 2, 0), sticky="ew")
        self._mode_frame_new.bind("<Button-1>", lambda e: self._set_mode("new_branch"))

        self._radio_new = ctk.CTkRadioButton(
            self._mode_frame_new,
            text="Push to a new branch (for PR / MR)",
            variable=self._push_mode, value="new_branch",
            command=lambda: self._set_mode("new_branch"),
            font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
            text_color=TEXT,
            fg_color=PRIMARY, hover_color=PRIMARY_H,
        )
        self._radio_new.pack(anchor="w", padx=PAD_SM, pady=(PAD_SM, 2))
        Label(self._mode_frame_new,
              text="Creates a separate branch — open a Pull Request / Merge Request later",
              size=11, color=TEXT_DIM).pack(anchor="w", padx=PAD_SM, pady=(0, PAD_SM))

        for child in self._mode_frame_new.winfo_children():
            child.bind("<Button-1>", lambda e: self._set_mode("new_branch"))

    def _set_mode(self, mode):
        self._push_mode.set(mode)
        self._on_mode_change()

    def _on_mode_change(self):
        mode = self._push_mode.get()

        # Update border colors
        if hasattr(self, "_mode_frame_same"):
            self._mode_frame_same.configure(
                border_color=PRIMARY if mode == "same" else BG3
            )
        if hasattr(self, "_mode_frame_new"):
            self._mode_frame_new.configure(
                border_color=PRIMARY if mode == "new_branch" else BG3
            )

        # Show/hide branch selector
        if mode == "new_branch":
            # Insert branch selector before target card
            self._branch_selector_frame.pack(fill="x", before=self._target_card)
        else:
            self._branch_selector_frame.pack_forget()

    # ── Preset / custom helpers ────────────────────────────────────────────
    def _select_preset(self, name):
        self._selected_preset.set(name)
        self._custom_var.set("")
        for n, frame in self._preset_btns.items():
            frame.configure(border_color=PRIMARY if n == name else BG3)

    def _on_custom_type(self, event=None):
        val = self._custom_var.get().strip()
        if val:
            for frame in self._preset_btns.values():
                frame.configure(border_color=BG3)
            self._selected_preset.set("")

    def _get_branch(self):
        mode = self._push_mode.get()
        if mode == "same":
            return self.app_state.get("current_branch", "main")
        custom = self._custom_var.get().strip()
        return custom if custom else self._selected_preset.get() or "main"

    # ── Next ──────────────────────────────────────────────────────────────
    def _next(self):
        mode = self._push_mode.get()
        self.app_state["push_mode"]    = mode
        self.app_state["branch"]       = self._get_branch()
        self.app_state["push_github"]  = self._push_github.get()
        self.app_state["push_gitlab"]  = self._push_gitlab.get()
        default_msg = "Update" if mode in ("same", "new_branch") else "Initial commit"
        self.app_state["commit_msg"]   = self._commit_var.get().strip() or default_msg
        self.on_next()
