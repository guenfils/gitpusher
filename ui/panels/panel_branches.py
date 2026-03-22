"""Branch Manager panel."""
import threading
import customtkinter as ctk
from tkinter import filedialog
from ui.theme import *
from ui.widgets.common import Card, PrimaryButton, SecondaryButton, Label, SectionHeader, StatusBadge, LogBox
from core.git_manager import GitManager


class PanelBranches(ctk.CTkFrame):
    def __init__(self, master, app_state, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app_state = app_state
        self.git = GitManager()
        self._path_var = ctk.StringVar()
        self._new_name_var = ctk.StringVar()
        self._from_var = ctk.StringVar()
        self._base_var = ctk.StringVar()
        self._compare_var = ctk.StringVar()
        self._rename_var = ctk.StringVar()
        self._branches = []
        self._build_ui()

    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=PAD, pady=(PAD, PAD_SM))
        Label(header, text="Branch Manager", size=22, bold=True).pack(anchor="w")
        Label(header, text="Create, switch, merge and compare branches", size=12, color=TEXT_DIM).pack(anchor="w")

        # Repo + Load row
        repo_card = Card(self)
        repo_card.pack(fill="x", padx=PAD, pady=(0, PAD_SM))
        repo_row = ctk.CTkFrame(repo_card, fg_color="transparent")
        repo_row.pack(fill="x", padx=PAD_SM, pady=PAD_SM)
        ctk.CTkEntry(
            repo_row, textvariable=self._path_var, width=260,
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            state="readonly", corner_radius=8,
        ).pack(side="left", padx=(0, PAD_SM))
        SecondaryButton(repo_row, text="Browse...", width=80, height=34, command=self._browse).pack(side="left", padx=(0, 6))
        PrimaryButton(repo_row, text="Load Branches", width=120, height=34, command=self._load_branches).pack(side="left")

        # Two-column area
        cols = ctk.CTkFrame(self, fg_color="transparent")
        cols.pack(fill="both", expand=True, padx=PAD, pady=(0, PAD_SM))
        cols.columnconfigure(0, weight=1)
        cols.columnconfigure(1, weight=1)
        cols.rowconfigure(0, weight=1)

        # LEFT column
        left_col = ctk.CTkFrame(cols, fg_color="transparent")
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, PAD_SM // 2))

        branch_list_card = Card(left_col)
        branch_list_card.pack(fill="both", expand=True, pady=(0, PAD_SM))
        Label(branch_list_card, text="Local & Remote Branches", size=14, bold=True).pack(
            anchor="w", padx=PAD_SM, pady=(PAD_SM, PAD_SM))
        self._branch_scroll = ctk.CTkScrollableFrame(branch_list_card, height=350, fg_color=BG, corner_radius=8)
        self._branch_scroll.pack(fill="both", expand=True, padx=PAD_SM, pady=(0, PAD_SM))
        self._branch_empty = Label(self._branch_scroll, text="No branches loaded", size=12, color=TEXT_MUTED)
        self._branch_empty.pack(pady=PAD)

        # Create branch card
        create_card = Card(left_col)
        create_card.pack(fill="x")
        Label(create_card, text="Create Branch", size=13, bold=True).pack(
            anchor="w", padx=PAD_SM, pady=(PAD_SM, PAD_SM))
        create_row = ctk.CTkFrame(create_card, fg_color="transparent")
        create_row.pack(fill="x", padx=PAD_SM, pady=(0, PAD_SM))
        Label(create_row, text="Name:", size=12).pack(side="left", padx=(0, 6))
        ctk.CTkEntry(
            create_row, textvariable=self._new_name_var, width=160,
            placeholder_text="feature/my-feature",
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            placeholder_text_color=TEXT_MUTED, corner_radius=8,
        ).pack(side="left", padx=(0, 8))
        Label(create_row, text="From:", size=12).pack(side="left", padx=(0, 6))
        self._from_combo = ctk.CTkComboBox(
            create_row, variable=self._from_var, width=120,
            values=[], fg_color=BG3, border_color=BORDER,
            text_color=TEXT, button_color=BG3, button_hover_color=BORDER,
            dropdown_fg_color=BG2, corner_radius=8,
        )
        self._from_combo.pack(side="left", padx=(0, 8))
        PrimaryButton(create_row, text="Create & Checkout", height=36, command=self._create).pack(side="left")

        # RIGHT column
        right_col = ctk.CTkFrame(cols, fg_color="transparent")
        right_col.grid(row=0, column=1, sticky="nsew", padx=(PAD_SM // 2, 0))

        compare_card = Card(right_col)
        compare_card.pack(fill="x", pady=(0, PAD_SM))
        SectionHeader(compare_card, "~", "Compare Branches", "").pack(fill="x", padx=PAD_SM, pady=(PAD_SM, PAD_SM))
        cmp_row = ctk.CTkFrame(compare_card, fg_color="transparent")
        cmp_row.pack(fill="x", padx=PAD_SM, pady=(0, PAD_SM))
        Label(cmp_row, text="Base:", size=12).pack(side="left", padx=(0, 4))
        self._base_combo = ctk.CTkComboBox(
            cmp_row, variable=self._base_var, width=140,
            values=[], fg_color=BG3, border_color=BORDER,
            text_color=TEXT, button_color=BG3, button_hover_color=BORDER,
            dropdown_fg_color=BG2, corner_radius=8,
        )
        self._base_combo.pack(side="left", padx=(0, 6))
        Label(cmp_row, text="vs", size=12, color=TEXT_DIM).pack(side="left", padx=(0, 6))
        self._compare_combo = ctk.CTkComboBox(
            cmp_row, variable=self._compare_var, width=140,
            values=[], fg_color=BG3, border_color=BORDER,
            text_color=TEXT, button_color=BG3, button_hover_color=BORDER,
            dropdown_fg_color=BG2, corner_radius=8,
        )
        self._compare_combo.pack(side="left", padx=(0, 8))
        SecondaryButton(cmp_row, text="Compare", width=90, height=34, command=self._compare).pack(side="left")

        self._diff_stat_label = Label(compare_card, text="", size=11, color=TEXT_DIM)
        self._diff_stat_label.pack(anchor="w", padx=PAD_SM, pady=(0, 4))

        self._commit_scroll = ctk.CTkScrollableFrame(compare_card, height=180, fg_color=BG, corner_radius=8)
        self._commit_scroll.pack(fill="x", padx=PAD_SM, pady=(0, PAD_SM))

        # Rename card
        rename_card = Card(right_col)
        rename_card.pack(fill="x")
        Label(rename_card, text="Rename Branch", size=13, bold=True).pack(
            anchor="w", padx=PAD_SM, pady=(PAD_SM, PAD_SM))
        rename_row = ctk.CTkFrame(rename_card, fg_color="transparent")
        rename_row.pack(fill="x", padx=PAD_SM, pady=(0, PAD_SM))
        Label(rename_row, text="Rename current branch:", size=12).pack(side="left", padx=(0, 6))
        ctk.CTkEntry(
            rename_row, textvariable=self._rename_var, width=180,
            fg_color=BG3, border_color=BORDER, text_color=TEXT, corner_radius=8,
        ).pack(side="left", padx=(0, 8))
        SecondaryButton(rename_row, text="Rename", width=90, height=34, command=self._rename).pack(side="left")

        # LogBox
        self._log = LogBox(self, height=80)
        self._log.pack(fill="x", padx=PAD, pady=(0, PAD))

    def _browse(self):
        path = filedialog.askdirectory(title="Select Git Repository")
        if path:
            self._path_var.set(path)
            self._load_branches()

    def _load_branches(self):
        path = self._path_var.get()
        if not path:
            self._log.append("[!] No repository path selected.")
            return
        threading.Thread(target=self._bg_load, daemon=True).start()

    def _bg_load(self):
        path = self._path_var.get()
        branches = self.git.get_all_branches(path)
        self.after(0, lambda: self._render(branches))

    def _render(self, branches):
        self._branches = branches
        for w in self._branch_scroll.winfo_children():
            w.destroy()

        if not branches:
            Label(self._branch_scroll, text="No branches found", size=12, color=TEXT_MUTED).pack(pady=PAD)
            return

        local_names = [b["display"] for b in branches if not b["remote"]]
        all_names = [b["display"] for b in branches]
        self._from_combo.configure(values=local_names)
        self._base_combo.configure(values=all_names)
        self._compare_combo.configure(values=all_names)
        if local_names:
            self._from_var.set(local_names[0])

        for b in branches:
            is_current = b["current"]
            bg = BG2 if is_current else "transparent"
            row = ctk.CTkFrame(self._branch_scroll, fg_color=bg, corner_radius=6)
            row.pack(fill="x", pady=2)

            if is_current:
                indicator = ctk.CTkFrame(row, width=3, fg_color=SUCCESS, corner_radius=0)
                indicator.pack(side="left", fill="y", padx=(0, 6))

            info = ctk.CTkFrame(row, fg_color="transparent")
            info.pack(side="left", fill="x", expand=True, padx=6, pady=6)

            name_weight = "bold" if is_current else "normal"
            Label(info, text=b["display"], size=13, bold=is_current).pack(side="left", padx=(0, 6))

            if is_current:
                StatusBadge(info, status="ok", text="Current").pack(side="left", padx=4)
            if b["remote"]:
                StatusBadge(info, status="pending", text="remote").pack(side="left", padx=4)
            if b["upstream"]:
                Label(info, text=f"upstream: {b['upstream']}", size=11, color=TEXT_MUTED).pack(side="left", padx=4)

            # Actions for local non-current branches
            if not b["remote"] and not is_current:
                actions = ctk.CTkFrame(row, fg_color="transparent")
                actions.pack(side="right", padx=4, pady=6)
                branch_name = b["display"]
                SecondaryButton(actions, text="Checkout", width=80, height=26,
                                command=lambda n=branch_name: self._checkout(n)).pack(side="left", padx=2)
                SecondaryButton(actions, text="Merge->", width=70, height=26,
                                command=lambda n=branch_name: self._merge(n)).pack(side="left", padx=2)
                ctk.CTkButton(
                    actions, text="Delete", width=65, height=26,
                    fg_color="#7F1D1D", text_color=WHITE, hover_color="#991B1B",
                    corner_radius=8, font=ctk.CTkFont(family="Inter", size=12),
                    command=lambda n=branch_name: self._delete(n),
                ).pack(side="left", padx=2)

    def _checkout(self, branch):
        path = self._path_var.get()
        if not path:
            return
        threading.Thread(target=self._bg_checkout, args=(path, branch), daemon=True).start()

    def _bg_checkout(self, path, branch):
        ok, out = self.git.checkout_branch(path, branch)
        status = f"[OK] Switched to {branch}." if ok else f"[!] Checkout failed: {out.strip()}"
        self.after(0, lambda: self._log.append(status))
        if ok:
            self.after(0, self._load_branches)

    def _merge(self, branch):
        path = self._path_var.get()
        if not path:
            return
        threading.Thread(target=self._bg_merge, args=(path, branch), daemon=True).start()

    def _bg_merge(self, path, branch):
        ok, out = self.git.merge_branch(path, branch)
        status = f"[OK] Merged {branch}." if ok else f"[!] Merge failed: {out.strip()}"
        self.after(0, lambda: self._log.append(status))
        if ok:
            self.after(0, self._load_branches)

    def _delete(self, branch):
        self._confirm_dialog(
            title="Delete Branch",
            message=f"Delete branch '{branch}'?",
            on_confirm=lambda: self._do_delete(branch),
        )

    def _do_delete(self, branch):
        path = self._path_var.get()
        if not path:
            return
        threading.Thread(target=self._bg_delete, args=(path, branch), daemon=True).start()

    def _bg_delete(self, path, branch):
        ok, out = self.git.delete_branch(path, branch, force=False)
        if not ok:
            # Suggest force
            self.after(0, lambda: self._log.append(
                f"[!] Delete failed (use force if branch is unmerged): {out.strip()}"
            ))
            return
        status = f"[OK] Deleted branch {branch}."
        self.after(0, lambda: self._log.append(status))
        self.after(0, self._load_branches)

    def _create(self):
        path = self._path_var.get()
        name = self._new_name_var.get().strip()
        if not path or not name:
            self._log.append("[!] Repository path and branch name are required.")
            return
        from_branch = self._from_var.get()
        threading.Thread(target=self._bg_create, args=(path, name, from_branch), daemon=True).start()

    def _bg_create(self, path, name, from_branch):
        if from_branch:
            self.git.checkout_branch(path, from_branch)
        ok, out = self.git.create_branch(path, name)
        status = f"[OK] Created and checked out {name}." if ok else f"[!] Create failed: {out.strip()}"
        self.after(0, lambda: self._log.append(status))
        if ok:
            self.after(0, lambda: self._new_name_var.set(""))
            self.after(0, self._load_branches)

    def _compare(self):
        path = self._path_var.get()
        base = self._base_var.get()
        compare = self._compare_var.get()
        if not path or not base or not compare:
            self._log.append("[!] Select base and compare branches.")
            return
        threading.Thread(target=self._bg_compare, args=(path, base, compare), daemon=True).start()

    def _bg_compare(self, path, base, compare):
        commits = self.git.compare_branches(path, base, compare)
        stat = self.git.get_branch_diff_stat(path, base, compare)
        self.after(0, lambda: self._render_compare(commits, stat))

    def _render_compare(self, commits, stat):
        stat_summary = stat.strip().splitlines()[-1] if stat.strip() else ""
        self._diff_stat_label.configure(text=stat_summary)
        for w in self._commit_scroll.winfo_children():
            w.destroy()
        if not commits:
            Label(self._commit_scroll, text="No unique commits found", size=12, color=TEXT_MUTED).pack(pady=8)
            return
        for c in commits:
            row = ctk.CTkFrame(self._commit_scroll, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(
                row, text=c["short"],
                fg_color=BG3, text_color=TEXT, corner_radius=4, padx=6,
                font=ctk.CTkFont(family="JetBrains Mono", size=11),
            ).pack(side="left", padx=(0, 6))
            Label(row, text=c["message"][:40], size=12).pack(side="left", padx=(0, 6))
            Label(row, text=c["author"], size=11, color=TEXT_DIM).pack(side="left", padx=(0, 6))
            Label(row, text=c["when"], size=11, color=TEXT_MUTED).pack(side="left")

    def _rename(self):
        path = self._path_var.get()
        new_name = self._rename_var.get().strip()
        if not path or not new_name:
            self._log.append("[!] Repository path and new name are required.")
            return
        threading.Thread(target=self._bg_rename, args=(path, new_name), daemon=True).start()

    def _bg_rename(self, path, new_name):
        ok, out = self.git.rename_branch(path, new_name)
        status = f"[OK] Renamed branch to {new_name}." if ok else f"[!] Rename failed: {out.strip()}"
        self.after(0, lambda: self._log.append(status))
        if ok:
            self.after(0, lambda: self._rename_var.set(""))
            self.after(0, self._load_branches)

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
