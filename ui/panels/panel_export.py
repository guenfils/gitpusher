"""Panel – Export / ZIP Backup."""
import os
import threading
import zipfile
import tarfile
import fnmatch
from pathlib import Path
from datetime import datetime
from tkinter import filedialog
import customtkinter as ctk
from ui.theme import *
from ui.widgets.common import Card, PrimaryButton, SecondaryButton, Label, StatusBadge, SectionHeader, LogBox, ProgressCard


class PanelExport(ctk.CTkFrame):
    def __init__(self, master, app_state, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app_state = app_state
        self._src_var = ctk.StringVar()
        self._dest_var = ctk.StringVar()
        self._filename_var = ctk.StringVar()
        self._exclude_var = ctk.StringVar(
            value=".git,node_modules,__pycache__,.venv,dist,build,*.pyc,*.pyo,.DS_Store"
        )
        self._format_var = ctk.StringVar(value="ZIP")
        self._include_git_var = ctk.BooleanVar(value=False)
        self._include_hidden_var = ctk.BooleanVar(value=True)

        self._export_btn = None
        self._progress_card = None
        self._success_frame = None
        self._file_count_lbl = None

        self._build_ui()

    def _build_ui(self):
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True)
        self._scroll = scroll

        # Header
        Label(scroll, text="Export / Backup", size=22, bold=True).pack(anchor="w", pady=(0, 4))
        Label(scroll, text="Create a ZIP or TAR.GZ archive of your repository",
              size=12, color=TEXT_DIM).pack(anchor="w", pady=(0, PAD))

        # Source card
        src_card = Card(scroll)
        src_card.pack(fill="x", pady=(0, PAD_SM))
        SectionHeader(src_card, "📂", "Source Repository", "").pack(
            fill="x", padx=PAD, pady=(PAD_SM, PAD_SM)
        )
        src_row = ctk.CTkFrame(src_card, fg_color="transparent")
        src_row.pack(fill="x", padx=PAD, pady=(0, 4))

        self._src_entry = ctk.CTkEntry(
            src_row, textvariable=self._src_var, width=300, state="readonly",
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            placeholder_text="/path/to/repo",
            placeholder_text_color=TEXT_MUTED, corner_radius=8, height=36,
            font=ctk.CTkFont(family="Inter", size=12),
        )
        self._src_entry.pack(side="left", padx=(0, 8))
        SecondaryButton(src_row, text="Browse…", width=100, height=36,
                        command=self._browse_src).pack(side="left")

        self._file_count_lbl = Label(src_card, text="", size=11, color=TEXT_DIM)
        self._file_count_lbl.pack(anchor="w", padx=PAD, pady=(0, PAD_SM))

        # Options card
        opt_card = Card(scroll)
        opt_card.pack(fill="x", pady=(0, PAD_SM))
        SectionHeader(opt_card, "⚙", "Export Options", "").pack(
            fill="x", padx=PAD, pady=(PAD_SM, PAD_SM)
        )

        # Format
        fmt_row = ctk.CTkFrame(opt_card, fg_color="transparent")
        fmt_row.pack(fill="x", padx=PAD, pady=(0, 8))
        Label(fmt_row, text="Format:", size=12, color=TEXT_DIM).pack(side="left", padx=(0, 8))
        ctk.CTkSegmentedButton(
            fmt_row, values=["ZIP", "TAR.GZ"],
            variable=self._format_var,
            fg_color=BG3, selected_color=PRIMARY, selected_hover_color=PRIMARY_H,
            unselected_color=BG3, unselected_hover_color=BORDER,
            text_color=TEXT,
            font=ctk.CTkFont(family="Inter", size=12),
        ).pack(side="left")

        # Exclude patterns
        excl_row = ctk.CTkFrame(opt_card, fg_color="transparent")
        excl_row.pack(fill="x", padx=PAD, pady=(0, 4))
        Label(excl_row, text="Exclude patterns:", size=12, color=TEXT_DIM).pack(side="left", padx=(0, 8))
        ctk.CTkEntry(
            excl_row, textvariable=self._exclude_var, width=360,
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            corner_radius=8, height=34,
            font=ctk.CTkFont(family="Inter", size=12),
        ).pack(side="left")
        Label(opt_card, text="Comma-separated glob patterns to skip",
              size=10, color=TEXT_MUTED).pack(anchor="w", padx=PAD, pady=(0, 8))

        # Switches
        sw_row = ctk.CTkFrame(opt_card, fg_color="transparent")
        sw_row.pack(fill="x", padx=PAD, pady=(0, 8))
        ctk.CTkSwitch(
            sw_row, text="Include .git folder",
            variable=self._include_git_var,
            progress_color=PRIMARY, button_color=WHITE,
            text_color=TEXT, font=ctk.CTkFont(family="Inter", size=12),
        ).pack(side="left", padx=(0, PAD))
        ctk.CTkSwitch(
            sw_row, text="Include hidden files (dotfiles)",
            variable=self._include_hidden_var,
            progress_color=PRIMARY, button_color=WHITE,
            text_color=TEXT, font=ctk.CTkFont(family="Inter", size=12),
        ).pack(side="left")
        # spacer
        ctk.CTkFrame(opt_card, fg_color="transparent", height=4).pack()

        # Destination card
        dest_card = Card(scroll)
        dest_card.pack(fill="x", pady=(0, PAD_SM))
        SectionHeader(dest_card, "💾", "Save To", "").pack(
            fill="x", padx=PAD, pady=(PAD_SM, PAD_SM)
        )
        dest_row = ctk.CTkFrame(dest_card, fg_color="transparent")
        dest_row.pack(fill="x", padx=PAD, pady=(0, 8))
        self._dest_entry = ctk.CTkEntry(
            dest_row, textvariable=self._dest_var, width=280, state="readonly",
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            placeholder_text="/output/folder",
            placeholder_text_color=TEXT_MUTED, corner_radius=8, height=36,
            font=ctk.CTkFont(family="Inter", size=12),
        )
        self._dest_entry.pack(side="left", padx=(0, 8))
        SecondaryButton(dest_row, text="Choose Folder…", width=130, height=36,
                        command=self._browse_dest).pack(side="left")

        fname_row = ctk.CTkFrame(dest_card, fg_color="transparent")
        fname_row.pack(fill="x", padx=PAD, pady=(0, PAD_SM))
        Label(fname_row, text="Filename:", size=12, color=TEXT_DIM).pack(side="left", padx=(0, 8))
        ctk.CTkEntry(
            fname_row, textvariable=self._filename_var, width=280,
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            placeholder_text="repo-2025-01-01.zip",
            placeholder_text_color=TEXT_MUTED, corner_radius=8, height=34,
            font=ctk.CTkFont(family="Inter", size=12),
        ).pack(side="left")

        # Export button
        self._export_btn = PrimaryButton(
            scroll, text="Export Now", height=46,
            command=self._export,
        )
        self._export_btn.pack(fill="x", pady=(0, PAD_SM))

        # Progress card (hidden until export starts)
        self._progress_card = ProgressCard(scroll, label="Ready to export")
        self._progress_card.pack(fill="x", pady=(0, PAD_SM))

        # Success frame (hidden initially)
        self._success_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        self._success_frame.pack(fill="x", pady=(0, PAD_SM))

        # Log card
        log_card = Card(scroll)
        log_card.pack(fill="x", pady=(0, PAD_SM))
        Label(log_card, text="Export Log", size=13, bold=True).pack(
            anchor="w", padx=PAD, pady=(PAD_SM, 4)
        )
        self._logbox = LogBox(log_card, height=150)
        self._logbox.pack(fill="x", padx=PAD, pady=(0, PAD_SM))

    # ---------- Browse ----------

    def _browse_src(self):
        folder = filedialog.askdirectory(title="Select source repository")
        if not folder:
            return
        self._src_entry.configure(state="normal")
        self._src_var.set(folder)
        self._src_entry.configure(state="readonly")

        # Auto-fill filename
        repo_name = Path(folder).name
        date_str = datetime.now().strftime("%Y-%m-%d")
        ext = ".zip" if self._format_var.get() == "ZIP" else ".tar.gz"
        self._filename_var.set(f"{repo_name}-{date_str}{ext}")

        # Count files in thread
        def _count():
            try:
                patterns = [p.strip() for p in self._exclude_var.get().split(",") if p.strip()]
                total_files = 0
                total_size = 0
                for root, dirs, files in os.walk(folder):
                    dirs[:] = [d for d in dirs if not self._should_exclude(
                        str(Path(root, d).relative_to(folder)), patterns
                    )]
                    for f in files:
                        rel = str(Path(root, f).relative_to(folder))
                        if not self._should_exclude(rel, patterns):
                            total_files += 1
                            try:
                                total_size += os.path.getsize(os.path.join(root, f))
                            except Exception:
                                pass
                size_mb = total_size / (1024 * 1024)
                self.after(0, lambda: self._file_count_lbl.configure(
                    text=f"{total_files} files  ·  {size_mb:.1f} MB"
                ))
            except Exception as e:
                self.after(0, lambda: self._file_count_lbl.configure(text=f"Error counting: {e}"))

        threading.Thread(target=_count, daemon=True).start()

    def _browse_dest(self):
        folder = filedialog.askdirectory(title="Choose destination folder")
        if folder:
            self._dest_entry.configure(state="normal")
            self._dest_var.set(folder)
            self._dest_entry.configure(state="readonly")

    # ---------- Export ----------

    @staticmethod
    def _should_exclude(rel_path, patterns):
        parts = Path(rel_path).parts
        for pat in patterns:
            for part in parts:
                if fnmatch.fnmatch(part, pat):
                    return True
            if fnmatch.fnmatch(rel_path, pat):
                return True
        return False

    def _export(self):
        src = self._src_var.get().strip()
        dest = self._dest_var.get().strip()
        if not src:
            self._log("Error: Please select a source repository.")
            return
        if not dest:
            self._log("Error: Please choose a destination folder.")
            return

        fname = self._filename_var.get().strip()
        if not fname:
            repo_name = Path(src).name
            date_str = datetime.now().strftime("%Y-%m-%d")
            ext = ".zip" if self._format_var.get() == "ZIP" else ".tar.gz"
            fname = f"{repo_name}-{date_str}{ext}"
            self._filename_var.set(fname)

        self._export_btn.configure(state="disabled", text="Exporting…")

        # Clear success frame
        for w in self._success_frame.winfo_children():
            w.destroy()

        self._progress_card.set_label("Starting export…")
        self._progress_card.set_value(0)

        threading.Thread(target=self._do_export, daemon=True).start()

    def _do_export(self):
        src = self._src_var.get().strip()
        dest = self._dest_var.get().strip()
        fname = self._filename_var.get().strip()
        fmt = self._format_var.get()
        output_path = os.path.join(dest, fname)

        patterns = [p.strip() for p in self._exclude_var.get().split(",") if p.strip()]

        if not self._include_git_var.get():
            if ".git" not in patterns:
                patterns.append(".git")

        include_hidden = self._include_hidden_var.get()

        # Collect all files
        all_files = []
        try:
            for root, dirs, files in os.walk(src):
                rel_root = str(Path(root).relative_to(src)) if root != src else ""

                # Filter dirs in place
                filtered_dirs = []
                for d in dirs:
                    rel_d = str(Path(rel_root, d)) if rel_root else d
                    if self._should_exclude(rel_d, patterns):
                        continue
                    if not include_hidden and d.startswith("."):
                        continue
                    filtered_dirs.append(d)
                dirs[:] = filtered_dirs

                for f in files:
                    rel_f = str(Path(rel_root, f)) if rel_root else f
                    if self._should_exclude(rel_f, patterns):
                        continue
                    if not include_hidden and f.startswith("."):
                        continue
                    all_files.append((os.path.join(root, f), rel_f))
        except Exception as e:
            self._log(f"Error walking directory: {e}")
            self.after(0, lambda: self._export_btn.configure(state="normal", text="Export Now"))
            return

        total = len(all_files)
        self._log(f"Found {total} files to archive.")
        self.after(0, lambda: self._progress_card.set_label(f"Archiving {total} files…"))

        try:
            if fmt == "ZIP":
                with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
                    for i, (fpath, rel_path) in enumerate(all_files):
                        zf.write(fpath, arcname=rel_path)
                        if i % 20 == 0 or i == total - 1:
                            self._log(f"  + {rel_path}")
                            progress = (i + 1) / total if total > 0 else 1
                            self.after(0, lambda p=progress: self._progress_card.set_value(p))
            else:
                with tarfile.open(output_path, "w:gz") as tf:
                    for i, (fpath, rel_path) in enumerate(all_files):
                        tf.add(fpath, arcname=rel_path)
                        if i % 20 == 0 or i == total - 1:
                            self._log(f"  + {rel_path}")
                            progress = (i + 1) / total if total > 0 else 1
                            self.after(0, lambda p=progress: self._progress_card.set_value(p))

            size_mb = os.path.getsize(output_path) / (1024 * 1024)
            self._log(f"✓ Export complete: {output_path} ({size_mb:.1f} MB)")
            self.after(0, lambda: self._on_export_done(output_path, size_mb))

        except Exception as e:
            self._log(f"Export failed: {e}")
            self.after(0, lambda: self._export_btn.configure(state="normal", text="Export Now"))

    def _on_export_done(self, path, size_mb):
        self._export_btn.configure(state="normal", text="Export Now")
        self._progress_card.set_value(1.0)
        self._progress_card.set_label(f"Done — {size_mb:.1f} MB")

        # Clear and rebuild success frame
        for w in self._success_frame.winfo_children():
            w.destroy()

        StatusBadge(self._success_frame, status="ok", text="✓ Export complete").pack(side="left", padx=(0, 8))
        Label(self._success_frame, text=path, size=11, color=TEXT_DIM).pack(side="left", padx=(0, 8))

        dest_folder = str(Path(path).parent)
        SecondaryButton(
            self._success_frame, text="Open Folder", width=120, height=30,
            command=lambda: os.system(f'xdg-open "{dest_folder}"'),
        ).pack(side="left")

    def _log(self, msg):
        self.after(0, lambda: self._logbox.append(
            f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
        ))
