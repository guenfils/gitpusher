"""Manage View – two-column repo management interface."""
import customtkinter as ctk
from ui.theme import *
from ui.widgets.common import SecondaryButton, Label
from ui.panels.panel_repos import PanelRepos
from ui.panels.panel_clone import PanelClone
from ui.panels.panel_sync import PanelSync
from ui.panels.panel_tags import PanelTags
from ui.panels.panel_commits import PanelCommits
from ui.panels.panel_ssh import PanelSSH
from ui.panels.panel_templates import PanelTemplates
from ui.panels.panel_webhooks import PanelWebhooks
from ui.panels.panel_collaborators import PanelCollaborators
from ui.panels.panel_issues import PanelIssues
from ui.panels.panel_accounts import PanelAccounts
from ui.panels.panel_scheduled import PanelScheduled
from ui.panels.panel_watch import PanelWatch
from ui.panels.panel_novadeploy import PanelNovaDeploy
from ui.panels.panel_test_debugging import PanelTestDebugging
from ui.panels.panel_stats import PanelStats
from ui.panels.panel_export import PanelExport
from ui.panels.panel_stash    import PanelStash
from ui.panels.panel_branches import PanelBranches
from ui.panels.panel_diff     import PanelDiff
from ui.panels.panel_settings import PanelSettings
from ui.panels.panel_gitflow  import PanelGitflow


TABS = [
    ("Repositories",   PanelRepos),
    ("Clone",          PanelClone),
    ("Sync",           PanelSync),
    ("Tags & Releases", PanelTags),
    ("Commit History", PanelCommits),
    ("SSH Keys",       PanelSSH),
    ("Templates",      PanelTemplates),
    ("Webhooks",       PanelWebhooks),
    ("Collaborators",  PanelCollaborators),
    ("Issues",         PanelIssues),
    ("Accounts",       PanelAccounts),
    ("Scheduled Push", PanelScheduled),
    ("Watch Mode",     PanelWatch),
    ("NovaDeploy",     PanelNovaDeploy),
    ("Test & Debugging", PanelTestDebugging),
    ("Statistics",     PanelStats),
    ("Export / Backup", PanelExport),
    ("Stash",         PanelStash),
    ("Branches",      PanelBranches),
    ("Diff Viewer",   PanelDiff),
    ("Settings",      PanelSettings),
    ("Gitflow",       PanelGitflow),
]

TAB_ICONS = [
    "  Repositories",
    "  Clone",
    "  Sync",
    "  Tags & Releases",
    "  Commit History",
    "  SSH Keys",
    "  Templates",
    "  Webhooks",
    "  Collaborators",
    "  Issues",
    "  Accounts",
    "  Scheduled Push",
    "  Watch Mode",
    "  NovaDeploy",
    "  Test & Debugging",
    "  Statistics",
    "  Export / Backup",
    "  Stash",
    "  Branches",
    "  Diff Viewer",
    "  Settings",
    "  Gitflow",
]


class ManageView(ctk.CTkFrame):
    def __init__(self, master, app_state, on_back, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app_state = app_state
        self.on_back = on_back
        self._active_index = 0
        self._current_panel = None
        self._tab_btns = []

        self._build_ui()
        self._show_panel(0)

    def _build_ui(self):
        self.columnconfigure(0, minsize=190, weight=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # Sidebar outer frame (fixed width, no propagation)
        sidebar = ctk.CTkFrame(self, fg_color=BG2, width=190, corner_radius=RADIUS)
        sidebar.grid(row=0, column=0, sticky="nsew", padx=(0, PAD_SM))
        sidebar.pack_propagate(False)
        sidebar.rowconfigure(1, weight=1)  # scrollable area expands
        sidebar.columnconfigure(0, weight=1)

        # ── Header (fixed) ────────────────────────────────────────────────
        header = ctk.CTkFrame(sidebar, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew")
        Label(header, text="Repo Manager", size=14, bold=True).pack(
            padx=PAD_SM, pady=(PAD, PAD_SM), anchor="w"
        )

        # ── Scrollable tab list ───────────────────────────────────────────
        scroll = ctk.CTkScrollableFrame(
            sidebar,
            fg_color="transparent",
            scrollbar_button_color=BG3,
            scrollbar_button_hover_color=BORDER,
        )
        scroll.grid(row=1, column=0, sticky="nsew")

        for i, (title, _panel_cls) in enumerate(TABS):
            if i == 8:  # Teams section divider
                ctk.CTkLabel(
                    scroll, text="── Teams ──",
                    font=ctk.CTkFont(family="Inter", size=10),
                    text_color=TEXT_MUTED,
                ).pack(padx=PAD_SM, pady=(PAD_SM, 2), anchor="w")
            if i == 11:  # Productivity section divider
                ctk.CTkLabel(
                    scroll, text="── Productivity ──",
                    font=ctk.CTkFont(family="Inter", size=10),
                    text_color=TEXT_MUTED,
                ).pack(padx=PAD_SM, pady=(PAD_SM, 2), anchor="w")
            if i == 17:  # Git Tools section divider
                ctk.CTkLabel(
                    scroll, text="── Git Tools ──",
                    font=ctk.CTkFont(family="Inter", size=10),
                    text_color=TEXT_MUTED,
                ).pack(padx=PAD_SM, pady=(PAD_SM, 2), anchor="w")
            icon_text = TAB_ICONS[i]
            btn = ctk.CTkButton(
                scroll,
                text=icon_text,
                width=160,
                height=32,
                anchor="w",
                corner_radius=8,
                fg_color="transparent",
                text_color=TEXT_DIM,
                hover_color=BG3,
                font=ctk.CTkFont(family="Inter", size=13),
                command=lambda idx=i: self._show_panel(idx),
            )
            btn.pack(padx=PAD_SM, pady=2)
            self._tab_btns.append(btn)

        # ── Back button (fixed at bottom) ─────────────────────────────────
        footer = ctk.CTkFrame(sidebar, fg_color="transparent")
        footer.grid(row=2, column=0, sticky="ew")
        SecondaryButton(
            footer, text="<- Push Mode", width=160, height=40,
            command=self.on_back,
        ).pack(padx=PAD_SM, pady=(4, PAD))

        # Content area
        self._content = ctk.CTkFrame(self, fg_color="transparent")
        self._content.grid(row=0, column=1, sticky="nsew")

    def _show_panel(self, index):
        self._active_index = index

        # Update tab button styles
        for i, btn in enumerate(self._tab_btns):
            if i == index:
                btn.configure(fg_color=PRIMARY, text_color=WHITE, hover_color=PRIMARY_H)
            else:
                btn.configure(fg_color="transparent", text_color=TEXT_DIM, hover_color=BG3)

        # Destroy current panel
        if self._current_panel is not None:
            self._current_panel.destroy()
            self._current_panel = None

        # Create new panel
        _panel_cls = TABS[index][1]
        self._current_panel = _panel_cls(
            master=self._content,
            app_state=self.app_state,
        )
        self._current_panel.pack(fill="both", expand=True)
