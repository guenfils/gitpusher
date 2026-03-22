"""Diff Viewer panel."""
import threading
import customtkinter as ctk
from tkinter import filedialog
from ui.theme import *
from ui.widgets.common import Card, PrimaryButton, SecondaryButton, Label, LogBox
from core.git_manager import GitManager


class PanelDiff(ctk.CTkFrame):
    def __init__(self, master, app_state, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app_state = app_state
        self.git = GitManager()
        self._path_var = ctk.StringVar()
        self._mode = ctk.StringVar(value="Unstaged")
        self._selected_file = None
        self._files = []
        self._branch_base_var = ctk.StringVar()
        self._branch_compare_var = ctk.StringVar()
        self._build_ui()

    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=PAD, pady=(PAD, PAD_SM))
        Label(header, text="Diff Viewer", size=22, bold=True).pack(anchor="w")
        Label(header, text="Review changes before committing", size=12, color=TEXT_DIM).pack(anchor="w")

        # Repo + controls card
        ctrl_card = Card(self)
        ctrl_card.pack(fill="x", padx=PAD, pady=(0, PAD_SM))
        ctrl_row = ctk.CTkFrame(ctrl_card, fg_color="transparent")
        ctrl_row.pack(fill="x", padx=PAD_SM, pady=PAD_SM)

        ctk.CTkEntry(
            ctrl_row, textvariable=self._path_var, width=220,
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            state="readonly", corner_radius=8,
        ).pack(side="left", padx=(0, PAD_SM))
        SecondaryButton(ctrl_row, text="Browse...", width=80, height=34, command=self._browse).pack(side="left", padx=(0, 6))
        PrimaryButton(ctrl_row, text="Load", width=80, height=34, command=self._load).pack(side="left", padx=(0, PAD))

        # Mode toggle
        mode_frame = ctk.CTkFrame(ctrl_row, fg_color="transparent")
        mode_frame.pack(side="left")
        for mode_name in ["Unstaged", "Staged", "Between Branches"]:
            btn = ctk.CTkButton(
                mode_frame, text=mode_name, width=120, height=32,
                corner_radius=8,
                font=ctk.CTkFont(family="Inter", size=12),
                command=lambda m=mode_name: self._set_mode(m),
            )
            btn.pack(side="left", padx=2)
        self._mode_buttons = mode_frame.winfo_children()
        self._update_mode_btns()

        # Two-column content
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=PAD, pady=(0, PAD_SM))
        content.columnconfigure(0, weight=1)
        content.columnconfigure(1, weight=3)
        content.rowconfigure(0, weight=1)

        # Left: file list
        file_list_frame = ctk.CTkFrame(content, fg_color=BG2, corner_radius=RADIUS)
        file_list_frame.grid(row=0, column=0, sticky="nsew", padx=(0, PAD_SM))
        Label(file_list_frame, text="Changed Files", size=13, bold=True).pack(
            anchor="w", padx=PAD_SM, pady=(PAD_SM, PAD_SM))
        self._file_scroll = ctk.CTkScrollableFrame(file_list_frame, height=380, fg_color=BG, corner_radius=8)
        self._file_scroll.pack(fill="both", expand=True, padx=PAD_SM, pady=(0, PAD_SM))
        Label(self._file_scroll, text="No files loaded", size=12, color=TEXT_MUTED).pack(pady=PAD)

        # Right: diff viewer
        diff_frame = ctk.CTkFrame(content, fg_color=BG2, corner_radius=RADIUS)
        diff_frame.grid(row=0, column=1, sticky="nsew")
        Label(diff_frame, text="Diff", size=13, bold=True).pack(anchor="w", padx=PAD_SM, pady=(PAD_SM, PAD_SM))
        self._diff_box = ctk.CTkTextbox(
            diff_frame, height=380, state="disabled",
            fg_color=BG,
            font=ctk.CTkFont(family="JetBrains Mono", size=11),
            corner_radius=8,
        )
        self._diff_box.pack(fill="both", expand=True, padx=PAD_SM, pady=(0, PAD_SM))

        # Action buttons / branch compare row
        self._action_row = ctk.CTkFrame(self, fg_color="transparent")
        self._action_row.pack(fill="x", padx=PAD, pady=(0, PAD_SM))
        self._build_action_row()

        # LogBox
        self._log = LogBox(self, height=60)
        self._log.pack(fill="x", padx=PAD, pady=(0, PAD))

    def _build_action_row(self):
        for w in self._action_row.winfo_children():
            w.destroy()

        if self._mode.get() == "Between Branches":
            Label(self._action_row, text="Base:", size=12).pack(side="left", padx=(0, 6))
            self._bb_base_combo = ctk.CTkComboBox(
                self._action_row, variable=self._branch_base_var, width=140,
                values=[], fg_color=BG3, border_color=BORDER,
                text_color=TEXT, button_color=BG3, button_hover_color=BORDER,
                dropdown_fg_color=BG2, corner_radius=8,
            )
            self._bb_base_combo.pack(side="left", padx=(0, 8))
            Label(self._action_row, text="vs", size=12, color=TEXT_DIM).pack(side="left", padx=(0, 8))
            self._bb_cmp_combo = ctk.CTkComboBox(
                self._action_row, variable=self._branch_compare_var, width=140,
                values=[], fg_color=BG3, border_color=BORDER,
                text_color=TEXT, button_color=BG3, button_hover_color=BORDER,
                dropdown_fg_color=BG2, corner_radius=8,
            )
            self._bb_cmp_combo.pack(side="left", padx=(0, 8))
            SecondaryButton(
                self._action_row, text="Compare Branches", width=140, height=34,
                command=self._compare_branches,
            ).pack(side="left")
            # Populate branch combos
            self._populate_branch_combos()
        else:
            SecondaryButton(
                self._action_row, text="Stage File", width=110, height=34,
                command=self._stage_file,
            ).pack(side="left", padx=(0, 6))
            SecondaryButton(
                self._action_row, text="Unstage File", width=120, height=34,
                command=self._unstage_file,
            ).pack(side="left", padx=(0, 6))
            ctk.CTkButton(
                self._action_row, text="Discard Changes", width=140, height=34,
                fg_color=ERROR, text_color=WHITE, hover_color="#DC2626",
                corner_radius=8, font=ctk.CTkFont(family="Inter", size=13),
                command=self._discard_file,
            ).pack(side="left")

    def _populate_branch_combos(self):
        path = self._path_var.get()
        if not path:
            return
        threading.Thread(target=self._bg_get_branches, daemon=True).start()

    def _bg_get_branches(self):
        path = self._path_var.get()
        branches = self.git.get_branches(path)
        self.after(0, lambda: self._set_branch_combos(branches))

    def _set_branch_combos(self, branches):
        if hasattr(self, "_bb_base_combo"):
            self._bb_base_combo.configure(values=branches)
            self._bb_cmp_combo.configure(values=branches)
            if branches:
                self._branch_base_var.set(branches[0])
                if len(branches) > 1:
                    self._branch_compare_var.set(branches[1])

    def _set_mode(self, mode_name):
        self._mode.set(mode_name)
        self._update_mode_btns()
        self._build_action_row()
        self._load()

    def _update_mode_btns(self):
        mode_names = ["Unstaged", "Staged", "Between Branches"]
        for i, btn in enumerate(getattr(self, "_mode_buttons", [])):
            if mode_names[i] == self._mode.get():
                btn.configure(fg_color=PRIMARY, text_color=WHITE, hover_color=PRIMARY_H)
            else:
                btn.configure(fg_color=BG3, text_color=TEXT, hover_color=BORDER)

    # Re-collect mode buttons after build
    def _refresh_mode_buttons(self):
        ctrl_card_children = self.winfo_children()
        # Find mode buttons by traversal — skipped; buttons are rebuilt per mode change above

    def _browse(self):
        path = filedialog.askdirectory(title="Select Git Repository")
        if path:
            self._path_var.set(path)
            self._load()

    def _load(self):
        path = self._path_var.get()
        if not path:
            self._log.append("[!] No repository path selected.")
            return
        mode = self._mode.get()
        if mode == "Between Branches":
            return  # handled by compare button
        staged = (mode == "Staged")
        threading.Thread(target=self._bg_load_files, args=(path, staged), daemon=True).start()

    def _bg_load_files(self, path, staged):
        files = self.git.get_changed_files(path, staged=staged)
        self.after(0, lambda: self._render_file_list(files, staged))

    def _render_file_list(self, files, staged):
        self._files = files
        self._selected_file = None
        for w in self._file_scroll.winfo_children():
            w.destroy()
        if not files:
            Label(self._file_scroll, text="No changed files", size=12, color=TEXT_MUTED).pack(pady=PAD)
            self._render_diff("")
            return
        for f in files:
            row = ctk.CTkFrame(self._file_scroll, fg_color=BG3, corner_radius=6, cursor="hand2")
            row.pack(fill="x", pady=2)
            info = ctk.CTkFrame(row, fg_color="transparent")
            info.pack(side="left", padx=6, pady=6)
            Label(info, text=f"+{f['added']}", size=11, color=SUCCESS).pack(side="left")
            Label(info, text=f"-{f['removed']}", size=11, color=ERROR).pack(side="left", padx=(2, 6))
            Label(info, text=f["file"], size=12, color=TEXT).pack(side="left")
            filepath = f["file"]
            row.bind("<Button-1>", lambda e, fp=filepath, r=row, s=staged: self._select_file(fp, r, s))
            for child in info.winfo_children():
                child.bind("<Button-1>", lambda e, fp=filepath, r=row, s=staged: self._select_file(fp, r, s))

    def _select_file(self, filepath, row, staged):
        self._selected_file = filepath
        for w in self._file_scroll.winfo_children():
            w.configure(border_width=0, border_color="transparent")
        row.configure(border_width=2, border_color=PRIMARY)
        path = self._path_var.get()
        threading.Thread(target=self._bg_load_diff, args=(path, staged, filepath), daemon=True).start()

    def _bg_load_diff(self, path, staged, filepath):
        diff = self.git.get_diff(path, staged=staged, filepath=filepath)
        self.after(0, lambda: self._render_diff(diff))

    def _render_diff(self, diff_text):
        self._diff_box.configure(state="normal")
        self._diff_box.delete("1.0", "end")

        self._diff_box.tag_configure("add",     foreground=SUCCESS)
        self._diff_box.tag_configure("remove",  foreground=ERROR)
        self._diff_box.tag_configure("header",  foreground="#0EA5E9")
        self._diff_box.tag_configure("file",    foreground=TEXT_MUTED)
        self._diff_box.tag_configure("context", foreground=TEXT_DIM)

        if not diff_text:
            self._diff_box.insert("end", "(no diff)", "context")
            self._diff_box.configure(state="disabled")
            return

        for line in diff_text.splitlines():
            if line.startswith("+++") or line.startswith("---"):
                self._diff_box.insert("end", line + "\n", "file")
            elif line.startswith("@@"):
                self._diff_box.insert("end", line + "\n", "header")
            elif line.startswith("+"):
                self._diff_box.insert("end", line + "\n", "add")
            elif line.startswith("-"):
                self._diff_box.insert("end", line + "\n", "remove")
            else:
                self._diff_box.insert("end", line + "\n", "context")

        self._diff_box.configure(state="disabled")
        self._diff_box.see("end")

    def _stage_file(self):
        if not self._selected_file:
            self._log.append("[!] No file selected.")
            return
        path = self._path_var.get()
        threading.Thread(target=self._bg_stage, args=(path, self._selected_file), daemon=True).start()

    def _bg_stage(self, path, filepath):
        ok, out = self.git.stage_file(path, filepath)
        status = f"[OK] Staged {filepath}." if ok else f"[!] Stage failed: {out.strip()}"
        self.after(0, lambda: self._log.append(status))
        if ok:
            self.after(0, self._load)

    def _unstage_file(self):
        if not self._selected_file:
            self._log.append("[!] No file selected.")
            return
        path = self._path_var.get()
        threading.Thread(target=self._bg_unstage, args=(path, self._selected_file), daemon=True).start()

    def _bg_unstage(self, path, filepath):
        ok, out = self.git.unstage_file(path, filepath)
        status = f"[OK] Unstaged {filepath}." if ok else f"[!] Unstage failed: {out.strip()}"
        self.after(0, lambda: self._log.append(status))
        if ok:
            self.after(0, self._load)

    def _discard_file(self):
        if not self._selected_file:
            self._log.append("[!] No file selected.")
            return
        self._confirm_dialog(
            title="Discard Changes",
            message=f"Discard all changes in '{self._selected_file}'? This cannot be undone.",
            on_confirm=lambda: self._do_discard(),
        )

    def _do_discard(self):
        path = self._path_var.get()
        filepath = self._selected_file
        threading.Thread(target=self._bg_discard, args=(path, filepath), daemon=True).start()

    def _bg_discard(self, path, filepath):
        ok, out = self.git.discard_file(path, filepath)
        status = f"[OK] Discarded changes in {filepath}." if ok else f"[!] Discard failed: {out.strip()}"
        self.after(0, lambda: self._log.append(status))
        if ok:
            self.after(0, self._load)

    def _compare_branches(self):
        path = self._path_var.get()
        base = self._branch_base_var.get()
        compare = self._branch_compare_var.get()
        if not path or not base or not compare:
            self._log.append("[!] Select base and compare branches.")
            return
        threading.Thread(target=self._bg_compare_branches, args=(path, base, compare), daemon=True).start()

    def _bg_compare_branches(self, path, base, compare):
        stat = self.git.get_branch_diff_stat(path, base, compare)
        # Parse stat to get file list
        files = []
        for line in stat.strip().splitlines():
            if "|" in line:
                parts = line.split("|")
                fname = parts[0].strip()
                files.append({"file": fname, "added": 0, "removed": 0})
        diff = self.git.get_diff(path)  # full unstaged as fallback
        self.after(0, lambda: self._render_branch_compare(files, stat))

    def _render_branch_compare(self, files, stat):
        for w in self._file_scroll.winfo_children():
            w.destroy()
        if not files:
            Label(self._file_scroll, text="No differences found", size=12, color=TEXT_MUTED).pack(pady=PAD)
        else:
            for f in files:
                row = ctk.CTkFrame(self._file_scroll, fg_color=BG3, corner_radius=6)
                row.pack(fill="x", pady=2)
                Label(row, text=f["file"], size=12, color=TEXT).pack(side="left", padx=8, pady=6)
        self._render_diff(stat)

    def _confirm_dialog(self, title, message, on_confirm):
        win = ctk.CTkToplevel(self)
        win.title(title)
        win.geometry("400x160")
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
            btn_row, text="Discard", width=120, height=36,
            fg_color=ERROR, text_color=WHITE, hover_color="#DC2626",
            corner_radius=8, font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
            command=_confirm_and_close,
        ).pack(side="left")
