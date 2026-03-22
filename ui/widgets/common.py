"""Reusable UI widgets."""
import customtkinter as ctk
from ui.theme import *


class Card(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(
            master,
            fg_color=BG2,
            corner_radius=RADIUS,
            **kwargs
        )


class PrimaryButton(ctk.CTkButton):
    def __init__(self, master, **kwargs):
        kwargs.setdefault("fg_color", PRIMARY)
        kwargs.setdefault("hover_color", PRIMARY_H)
        kwargs.setdefault("text_color", WHITE)
        kwargs.setdefault("corner_radius", 8)
        kwargs.setdefault("height", 42)
        kwargs.setdefault("font", ctk.CTkFont(family="Inter", size=13, weight="bold"))
        super().__init__(master, **kwargs)


class SecondaryButton(ctk.CTkButton):
    def __init__(self, master, **kwargs):
        kwargs.setdefault("fg_color", BG3)
        kwargs.setdefault("hover_color", BORDER)
        kwargs.setdefault("text_color", TEXT)
        kwargs.setdefault("corner_radius", 8)
        kwargs.setdefault("height", 42)
        kwargs.setdefault("font", ctk.CTkFont(family="Inter", size=13))
        super().__init__(master, **kwargs)


class DangerButton(ctk.CTkButton):
    def __init__(self, master, **kwargs):
        kwargs.setdefault("fg_color", ERROR)
        kwargs.setdefault("hover_color", "#DC2626")
        kwargs.setdefault("text_color", WHITE)
        kwargs.setdefault("corner_radius", 8)
        kwargs.setdefault("height", 42)
        kwargs.setdefault("font", ctk.CTkFont(family="Inter", size=13, weight="bold"))
        super().__init__(master, **kwargs)


class Label(ctk.CTkLabel):
    def __init__(self, master, size=12, bold=False, color=None, **kwargs):
        weight = "bold" if bold else "normal"
        super().__init__(
            master,
            text_color=color or TEXT,
            font=ctk.CTkFont(family="Inter", size=size, weight=weight),
            **kwargs
        )


class Entry(ctk.CTkEntry):
    def __init__(self, master, **kwargs):
        super().__init__(
            master,
            fg_color=BG3,
            border_color=BORDER,
            text_color=TEXT,
            placeholder_text_color=TEXT_MUTED,
            corner_radius=8,
            height=42,
            font=ctk.CTkFont(family="Inter", size=12),
            **kwargs
        )


class StatusBadge(ctk.CTkLabel):
    COLORS = {
        "ok":      ("#D1FAE5", "#065F46"),
        "error":   ("#FEE2E2", "#991B1B"),
        "warning": ("#FEF3C7", "#92400E"),
        "info":    ("#DBEAFE", "#1E40AF"),
        "pending": (BG3, TEXT_DIM),
    }

    def __init__(self, master, status="pending", text="", **kwargs):
        bg, fg = self.COLORS.get(status, self.COLORS["pending"])
        super().__init__(
            master,
            text=text,
            fg_color=bg,
            text_color=fg,
            corner_radius=6,
            padx=10,
            pady=4,
            font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
            **kwargs
        )

    def update_status(self, status, text):
        bg, fg = self.COLORS.get(status, self.COLORS["pending"])
        self.configure(text=text, fg_color=bg, text_color=fg)


class SectionHeader(ctk.CTkFrame):
    def __init__(self, master, number, title, subtitle="", **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        # Number badge
        badge = ctk.CTkLabel(
            self,
            text=str(number),
            width=32, height=32,
            fg_color=PRIMARY,
            text_color=WHITE,
            corner_radius=16,
            font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
        )
        badge.pack(side="left", padx=(0, 12))
        # Titles
        txt_frame = ctk.CTkFrame(self, fg_color="transparent")
        txt_frame.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(
            txt_frame, text=title,
            font=ctk.CTkFont(family="Inter", size=15, weight="bold"),
            text_color=TEXT, anchor="w",
        ).pack(anchor="w")
        if subtitle:
            ctk.CTkLabel(
                txt_frame, text=subtitle,
                font=ctk.CTkFont(family="Inter", size=11),
                text_color=TEXT_DIM, anchor="w",
            ).pack(anchor="w")


class LogBox(ctk.CTkTextbox):
    def __init__(self, master, **kwargs):
        super().__init__(
            master,
            fg_color=BG,
            text_color=TEXT,
            font=ctk.CTkFont(family="JetBrains Mono", size=11),
            corner_radius=8,
            border_color=BORDER,
            border_width=1,
            **kwargs
        )
        self.configure(state="disabled")

    def append(self, text, tag=None):
        self.configure(state="normal")
        self.insert("end", text + "\n")
        self.see("end")
        self.configure(state="disabled")

    def clear(self):
        self.configure(state="normal")
        self.delete("1.0", "end")
        self.configure(state="disabled")


class Divider(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, height=1, fg_color=BORDER, **kwargs)


class ProgressCard(ctk.CTkFrame):
    def __init__(self, master, label="", **kwargs):
        super().__init__(master, fg_color=BG2, corner_radius=RADIUS, **kwargs)
        self.label_var = ctk.StringVar(value=label)
        ctk.CTkLabel(
            self,
            textvariable=self.label_var,
            font=ctk.CTkFont(family="Inter", size=12),
            text_color=TEXT_DIM,
            anchor="w",
        ).pack(fill="x", padx=PAD_SM, pady=(PAD_SM, 4))
        self.bar = ctk.CTkProgressBar(
            self,
            fg_color=BG3,
            progress_color=PRIMARY,
            corner_radius=4,
        )
        self.bar.set(0)
        self.bar.pack(fill="x", padx=PAD_SM, pady=(0, PAD_SM))

    def set_label(self, text):
        self.label_var.set(text)

    def set_value(self, v):
        self.bar.set(v)

    def start_indeterminate(self):
        self.bar.configure(mode="indeterminate")
        self.bar.start()

    def stop_indeterminate(self):
        self.bar.stop()
        self.bar.configure(mode="determinate")
        self.bar.set(1)
