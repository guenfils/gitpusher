"""Main application window with step wizard."""
import customtkinter as ctk
from PIL import Image
from pathlib import Path
from ui.theme import *

ASSETS = Path(__file__).parent.parent / "assets"
from ui.steps.step_check    import StepCheck
from ui.steps.step_platform import StepPlatform
from ui.steps.step_project  import StepProject
from ui.steps.step_readme   import StepReadme
from ui.steps.step_branch   import StepBranch
from ui.steps.step_upload   import StepUpload
from ui.manage_view         import ManageView


STEPS = [
    ("System",   "Check"),
    ("Platform", "Auth"),
    ("Project",  "Select"),
    ("README",   "Generate"),   # index 3
    ("Branch",   "Configure"),  # index 4
    ("Upload",   "Push"),       # index 5
]


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Git Pusher  —  GitHub & GitLab")
        self.geometry("780x700")
        self.minsize(700, 580)
        self.configure(fg_color=BG)

        self.app_state   = {}
        self._step_index = 0
        self._step_frame = None

        self._build_chrome()
        self._show_step(0)

    # ── Chrome ────────────────────────────────────────────────────────────────
    def _build_chrome(self):
        # Window icon
        try:
            icon_img = Image.open(ASSETS / "icon.png")
            self._icon_ctk = ctk.CTkImage(icon_img, size=(32, 32))
            icon_photo = ctk.CTkImage(icon_img, size=(64, 64))
            # Set taskbar/titlebar icon via tk iconphoto
            from PIL import ImageTk
            self._tk_icon = ImageTk.PhotoImage(icon_img.resize((64, 64), Image.LANCZOS))
            self.iconphoto(True, self._tk_icon)
        except Exception:
            self._icon_ctk = None

        # Top bar
        topbar = ctk.CTkFrame(self, fg_color=BG2, height=64, corner_radius=0)
        topbar.pack(fill="x")
        topbar.pack_propagate(False)

        # Logo icon + title
        logo_frame = ctk.CTkFrame(topbar, fg_color="transparent")
        logo_frame.pack(side="left", padx=(PAD, 0))

        if self._icon_ctk:
            ctk.CTkLabel(
                logo_frame,
                image=self._icon_ctk,
                text="",
            ).pack(side="left", padx=(0, 10))

        title_col = ctk.CTkFrame(logo_frame, fg_color="transparent")
        title_col.pack(side="left")

        ctk.CTkLabel(
            title_col,
            text="Git Pusher",
            font=ctk.CTkFont(family="Inter", size=17, weight="bold"),
            text_color=TEXT,
            anchor="w",
        ).pack(anchor="w")

        ctk.CTkLabel(
            title_col,
            text="GitHub & GitLab in one click",
            font=ctk.CTkFont(family="Inter", size=11),
            text_color=TEXT_DIM,
            anchor="w",
        ).pack(anchor="w")

        from ui.widgets.common import SecondaryButton
        SecondaryButton(topbar, text="Manage Repos", command=self._show_manage, width=140, height=36).pack(side="right", padx=PAD)

        # Step indicator
        self._step_bar = ctk.CTkFrame(self, fg_color=BG2, height=56, corner_radius=0)
        self._step_bar.pack(fill="x")
        self._step_bar.pack_propagate(False)

        self._step_indicators = []
        for i, (title, subtitle) in enumerate(STEPS):
            col = ctk.CTkFrame(self._step_bar, fg_color="transparent")
            col.pack(side="left", padx=(PAD_SM, 0), pady=8)

            num_lbl = ctk.CTkLabel(
                col,
                text=str(i + 1),
                width=28, height=28,
                fg_color=BG3,
                text_color=TEXT_DIM,
                corner_radius=14,
                font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
            )
            num_lbl.pack(side="left", padx=(0, 6))

            txt = ctk.CTkFrame(col, fg_color="transparent")
            txt.pack(side="left")
            title_lbl = ctk.CTkLabel(
                txt, text=title,
                font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
                text_color=TEXT_DIM, anchor="w",
            )
            title_lbl.pack(anchor="w")
            sub_lbl = ctk.CTkLabel(
                txt, text=subtitle,
                font=ctk.CTkFont(family="Inter", size=9),
                text_color=TEXT_MUTED, anchor="w",
            )
            sub_lbl.pack(anchor="w")

            self._step_indicators.append((num_lbl, title_lbl, sub_lbl))

            if i < len(STEPS) - 1:
                ctk.CTkLabel(
                    self._step_bar, text="›",
                    font=ctk.CTkFont(size=18), text_color=BG3,
                ).pack(side="left", padx=4)

        # Separator
        self._separator = ctk.CTkFrame(self, height=1, fg_color=BORDER, corner_radius=0)
        self._separator.pack(fill="x")

        # Scrollable content area
        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color=BG, scrollbar_button_color=BG3,
            scrollbar_button_hover_color=BORDER,
        )
        self._scroll.pack(fill="both", expand=True, padx=PAD, pady=PAD)

    def _update_step_bar(self, current):
        for i, (num_lbl, title_lbl, sub_lbl) in enumerate(self._step_indicators):
            if i < current:
                # done
                num_lbl.configure(fg_color=SUCCESS, text_color=WHITE, text="✓")
                title_lbl.configure(text_color=TEXT)
                sub_lbl.configure(text_color=TEXT_DIM)
            elif i == current:
                # active
                num_lbl.configure(fg_color=PRIMARY, text_color=WHITE, text=str(i + 1))
                title_lbl.configure(text_color=TEXT)
                sub_lbl.configure(text_color=TEXT_DIM)
            else:
                # future
                num_lbl.configure(fg_color=BG3, text_color=TEXT_MUTED, text=str(i + 1))
                title_lbl.configure(text_color=TEXT_MUTED)
                sub_lbl.configure(text_color=TEXT_MUTED)

    # ── Step navigation ───────────────────────────────────────────────────────
    def _show_step(self, index):
        self._step_index = index
        self._update_step_bar(index)

        if self._step_frame:
            self._step_frame.destroy()

        kwargs = dict(master=self._scroll)

        if index == 0:
            self._step_frame = StepCheck(
                **kwargs,
                app_state=self.app_state,
                on_next=lambda: self._show_step(1),
            )
        elif index == 1:
            self._step_frame = StepPlatform(
                **kwargs,
                app_state=self.app_state,
                on_next=lambda: self._show_step(2),
                on_back=lambda: self._show_step(0),
            )
        elif index == 2:
            self._step_frame = StepProject(
                **kwargs,
                app_state=self.app_state,
                on_next=lambda: self._show_step(3),
                on_back=lambda: self._show_step(1),
            )
        elif index == 3:
            self._step_frame = StepReadme(
                **kwargs,
                app_state=self.app_state,
                on_next=lambda: self._show_step(4),
                on_back=lambda: self._show_step(2),
            )
        elif index == 4:
            self._step_frame = StepBranch(
                **kwargs,
                app_state=self.app_state,
                on_next=lambda: self._show_step(5),
                on_back=lambda: self._show_step(3),
            )
        elif index == 5:
            self._step_frame = StepUpload(
                **kwargs,
                app_state=self.app_state,
                on_restart=self._restart,
                on_back=lambda: self._show_step(4),
            )

        if self._step_frame:
            self._step_frame.pack(fill="both", expand=True)

        # Scroll to top
        try:
            self._scroll._parent_canvas.yview_moveto(0)
        except Exception:
            pass

    def _show_manage(self):
        self._step_bar.pack_forget()
        self._separator.pack_forget()
        self._scroll.pack_forget()
        if self._step_frame:
            self._step_frame.destroy()
            self._step_frame = None
        self._manage_frame = ManageView(
            master=self,
            app_state=self.app_state,
            on_back=self._back_to_wizard,
        )
        self._manage_frame.pack(fill="both", expand=True)

    def _back_to_wizard(self):
        if hasattr(self, "_manage_frame") and self._manage_frame:
            self._manage_frame.destroy()
            self._manage_frame = None
        self._step_bar.pack(fill="x")
        self._separator.pack(fill="x")
        self._scroll.pack(fill="both", expand=True, padx=PAD, pady=PAD)
        self._show_step(self._step_index)

    def _restart(self):
        """Start a new upload while preserving auth state."""
        preserved = {
            k: v for k, v in self.app_state.items()
            if k in ("github_token", "github_user", "github_api",
                     "gitlab_token", "gitlab_user", "gitlab_api",
                     "git_name", "git_email", "ssh_key", "auth_method")
        }
        self.app_state = preserved
        self._show_step(2)  # Jump straight to project selection
