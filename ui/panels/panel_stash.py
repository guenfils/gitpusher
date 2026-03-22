"""Stash Manager panel."""
import threading
import customtkinter as ctk
from tkinter import filedialog
from ui.theme import *
from ui.widgets.common import Card, PrimaryButton, SecondaryButton, Label, SectionHeader, LogBox
from core.git_manager import GitManager


class PanelStash(ctk.CTkFrame):
    def __init__(self, master, app_state, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app_state = app_state
        self.git = GitManager()
        self._path_var = ctk.StringVar()
        self._msg_var = ctk.StringVar()
        self._untracked_var = ctk.BooleanVar(value=False)
        self._stashes = []
        self._build_ui()

    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=PAD, pady=(PAD, PAD_SM))
        Label(header, text="Stash Manager", size=22, bold=True).pack(anchor="w")
        Label(header, text="Save and restore work in progress", size=12, color=TEXT_DIM).pack(anchor="w")

        # Repo selector card
        repo_card = Card(self)
        repo_card.pack(fill="x", padx=PAD, pady=(0, PAD_SM))
        repo_row = ctk.CTkFrame(repo_card, fg_color="transparent")
        repo_row.pack(fill="x", padx=PAD_SM, pady=PAD_SM)
        Label(repo_row, text="Repository:", size=12).pack(side="left", padx=(0, PAD_SM))
        ctk.CTkEntry(
            repo_row, textvariable=self._path_var, width=280,
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            state="readonly", corner_radius=8,
        ).pack(side="left", padx=(0, PAD_SM))
        SecondaryButton(repo_row, text="Browse...", width=80, height=34, command=self._browse).pack(side="left", padx=(0, 6))
        PrimaryButton(repo_row, text="Refresh", width=90, height=34, command=self._load_stashes).pack(side="left")

        # Create stash card
        create_card = Card(self)
        create_card.pack(fill="x", padx=PAD, pady=(0, PAD_SM))
        SectionHeader(create_card, "+", "Save Current Changes", "").pack(fill="x", padx=PAD_SM, pady=(PAD_SM, PAD_SM))
        row1 = ctk.CTkFrame(create_card, fg_color="transparent")
        row1.pack(fill="x", padx=PAD_SM, pady=(0, PAD_SM))
        Label(row1, text="Message (optional):", size=12).pack(side="left", padx=(0, PAD_SM))
        ctk.CTkEntry(
            row1, textvariable=self._msg_var, width=280,
            placeholder_text="Work in progress...",
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            placeholder_text_color=TEXT_MUTED, corner_radius=8,
        ).pack(side="left")
        row2 = ctk.CTkFrame(create_card, fg_color="transparent")
        row2.pack(fill="x", padx=PAD_SM, pady=(0, PAD_SM))
        ctk.CTkCheckBox(
            row2, text="Include untracked files", variable=self._untracked_var,
            text_color=TEXT, fg_color=PRIMARY, hover_color=PRIMARY_H,
            checkmark_color=WHITE, font=ctk.CTkFont(family="Inter", size=12),
        ).pack(side="left")
        PrimaryButton(
            create_card, text="Stash Changes", height=40,
            command=self._stash_push,
        ).pack(fill="x", padx=PAD_SM, pady=(0, PAD_SM))

        # Stash list card
        list_card = Card(self)
        list_card.pack(fill="x", padx=PAD, pady=(0, PAD_SM))
        SectionHeader(list_card, "S", "Saved Stashes", "").pack(fill="x", padx=PAD_SM, pady=(PAD_SM, PAD_SM))
        self._stash_scroll = ctk.CTkScrollableFrame(list_card, height=320, fg_color=BG, corner_radius=8)
        self._stash_scroll.pack(fill="x", padx=PAD_SM, pady=(0, PAD_SM))
        self._empty_label = Label(self._stash_scroll, text="No stashes saved", size=12, color=TEXT_MUTED)
        self._empty_label.pack(pady=PAD)

        # Status log
        self._log = LogBox(self, height=80)
        self._log.pack(fill="x", padx=PAD, pady=(0, PAD))

    def _browse(self):
        path = filedialog.askdirectory(title="Select Git Repository")
        if path:
            self._path_var.set(path)
            self._load_stashes()

    def _load_stashes(self):
        path = self._path_var.get()
        if not path:
            self._log.append("[!] No repository path selected.")
            return
        threading.Thread(target=self._bg_load_stashes, daemon=True).start()

    def _bg_load_stashes(self):
        path = self._path_var.get()
        stashes = self.git.stash_list(path)
        self.after(0, lambda: self._render_stashes(stashes))

    def _render_stashes(self, stashes):
        self._stashes = stashes
        for widget in self._stash_scroll.winfo_children():
            widget.destroy()

        if not stashes:
            Label(self._stash_scroll, text="No stashes saved", size=12, color=TEXT_MUTED).pack(pady=PAD)
            return

        for stash in stashes:
            row = ctk.CTkFrame(self._stash_scroll, fg_color=BG3, corner_radius=8)
            row.pack(fill="x", pady=3, padx=4)

            # Left section
            left = ctk.CTkFrame(row, fg_color="transparent")
            left.pack(side="left", fill="x", expand=True, padx=6, pady=6)
            ctk.CTkLabel(
                left, text=stash["ref"],
                fg_color=PRIMARY, text_color=WHITE, corner_radius=6,
                padx=8, font=ctk.CTkFont(family="JetBrains Mono", size=11),
            ).pack(side="left", padx=(0, 6))
            msg = stash["message"][:50] + "..." if len(stash["message"]) > 50 else stash["message"]
            Label(left, text=msg, size=13, color=TEXT).pack(side="left", padx=6)
            Label(left, text=stash["when"], size=11, color=TEXT_MUTED).pack(side="left", padx=4)

            # Right section
            right = ctk.CTkFrame(row, fg_color="transparent")
            right.pack(side="right", padx=4, pady=6)
            ref = stash["ref"]
            SecondaryButton(right, text="Show", width=60, height=28,
                            command=lambda r=ref: self._show_diff(r)).pack(side="left", padx=2)
            SecondaryButton(right, text="Apply", width=65, height=28,
                            command=lambda r=ref: self._stash_apply(r)).pack(side="left", padx=2)
            PrimaryButton(right, text="Pop", width=60, height=28,
                          command=lambda r=ref: self._stash_pop(r)).pack(side="left", padx=2)
            ctk.CTkButton(
                right, text="Drop", width=60, height=28,
                fg_color="#7F1D1D", text_color=WHITE, hover_color="#991B1B",
                corner_radius=8, font=ctk.CTkFont(family="Inter", size=12),
                command=lambda r=ref: self._stash_drop(r),
            ).pack(side="left", padx=2)

    def _stash_push(self):
        path = self._path_var.get()
        if not path:
            self._log.append("[!] No repository path selected.")
            return
        msg = self._msg_var.get().strip() or None
        untracked = self._untracked_var.get()
        threading.Thread(target=self._bg_stash_push, args=(path, msg, untracked), daemon=True).start()

    def _bg_stash_push(self, path, msg, untracked):
        ok, out = self.git.stash_push(path, msg, untracked)
        status = "[OK] Stash saved." if ok else "[!] Stash failed."
        self.after(0, lambda: self._log.append(status + " " + out.strip()))
        if ok:
            self.after(0, lambda: self._msg_var.set(""))
            self.after(0, self._load_stashes)

    def _stash_apply(self, ref):
        path = self._path_var.get()
        if not path:
            return
        threading.Thread(target=self._bg_stash_apply, args=(path, ref), daemon=True).start()

    def _bg_stash_apply(self, path, ref):
        ok, out = self.git.stash_apply(path, ref)
        status = f"[OK] Applied {ref}." if ok else f"[!] Apply failed: {out.strip()}"
        self.after(0, lambda: self._log.append(status))

    def _stash_pop(self, ref):
        path = self._path_var.get()
        if not path:
            return
        threading.Thread(target=self._bg_stash_pop, args=(path, ref), daemon=True).start()

    def _bg_stash_pop(self, path, ref):
        ok, out = self.git.stash_pop(path, ref)
        status = f"[OK] Popped {ref}." if ok else f"[!] Pop failed: {out.strip()}"
        self.after(0, lambda: self._log.append(status))
        if ok:
            self.after(0, self._load_stashes)

    def _stash_drop(self, ref):
        self._confirm_dialog(
            title="Drop Stash",
            message=f"Drop {ref}? This cannot be undone.",
            on_confirm=lambda: self._do_drop(ref),
        )

    def _do_drop(self, ref):
        path = self._path_var.get()
        if not path:
            return
        threading.Thread(target=self._bg_stash_drop, args=(path, ref), daemon=True).start()

    def _bg_stash_drop(self, path, ref):
        ok, out = self.git.stash_drop(path, ref)
        status = f"[OK] Dropped {ref}." if ok else f"[!] Drop failed: {out.strip()}"
        self.after(0, lambda: self._log.append(status))
        if ok:
            self.after(0, self._load_stashes)

    def _show_diff(self, ref):
        path = self._path_var.get()
        if not path:
            self._log.append("[!] No repository path selected.")
            return
        diff = self.git.stash_show(path, ref)
        win = ctk.CTkToplevel(self)
        win.title(f"Diff: {ref}")
        win.geometry("600x500")
        win.configure(fg_color=BG)
        win.grab_set()
        Label(win, text=f"Stash diff: {ref}", size=14, bold=True).pack(padx=PAD, pady=(PAD, PAD_SM), anchor="w")
        tb = ctk.CTkTextbox(
            win, fg_color=BG2, text_color=TEXT,
            font=ctk.CTkFont(family="JetBrains Mono", size=11),
            corner_radius=8,
        )
        tb.pack(fill="both", expand=True, padx=PAD, pady=(0, PAD))
        tb.insert("1.0", diff if diff else "(no diff available)")
        tb.configure(state="disabled")

    def _confirm_dialog(self, title, message, on_confirm):
        win = ctk.CTkToplevel(self)
        win.title(title)
        win.geometry("360x160")
        win.configure(fg_color=BG)
        win.grab_set()
        Label(win, text=message, size=13).pack(padx=PAD, pady=(PAD, PAD_SM))
        btn_row = ctk.CTkFrame(win, fg_color="transparent")
        btn_row.pack(padx=PAD, pady=PAD_SM)
        SecondaryButton(btn_row, text="Cancel", width=120, height=36,
                        command=win.destroy).pack(side="left", padx=(0, PAD_SM))

        def _confirm_and_close():
            win.destroy()
            on_confirm()

        ctk.CTkButton(
            btn_row, text="Confirm", width=120, height=36,
            fg_color="#7F1D1D", text_color=WHITE, hover_color="#991B1B",
            corner_radius=8, font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
            command=_confirm_and_close,
        ).pack(side="left")
