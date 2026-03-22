"""Panel – SSH Key Manager."""
import threading
import subprocess
from tkinter import messagebox
import customtkinter as ctk
from ui.theme import *
from ui.widgets.common import Card, PrimaryButton, SecondaryButton, Label, StatusBadge, SectionHeader
from core.ssh_manager import SSHManager


class PanelSSH(ctk.CTkFrame):
    def __init__(self, master, app_state, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app_state = app_state
        self.ssh = SSHManager()
        self._gen_status = None
        self._pub_key_box = None
        self._deploy_key_combo = None
        self._github_status = None
        self._gitlab_status = None
        self._keys_frame = None
        self._build_ui()

    def _build_ui(self):
        outer = ctk.CTkScrollableFrame(self, fg_color="transparent")
        outer.pack(fill="both", expand=True, padx=PAD, pady=PAD)

        # Title
        Label(outer, text="SSH Key Manager", size=22, bold=True).pack(anchor="w")
        Label(outer, text="Generate, manage and deploy SSH keys to GitHub & GitLab",
              size=13, color=TEXT_DIM).pack(anchor="w", pady=(2, PAD_SM))

        # --- Card: Existing Keys ---
        keys_card = Card(outer)
        keys_card.pack(fill="x", pady=(0, PAD_SM))

        keys_header = ctk.CTkFrame(keys_card, fg_color="transparent")
        keys_header.pack(fill="x", padx=PAD_SM, pady=(PAD_SM, 4))
        Label(keys_header, text="Existing Keys", size=14, bold=True).pack(side="left")
        SecondaryButton(keys_header, text="Refresh", width=90, height=30,
                        command=self._refresh_keys).pack(side="right")

        self._keys_frame = ctk.CTkFrame(keys_card, fg_color="transparent")
        self._keys_frame.pack(fill="x", padx=PAD_SM, pady=(0, PAD_SM))
        self._refresh_keys()

        # --- Card: Generate New Key ---
        gen_card = Card(outer)
        gen_card.pack(fill="x", pady=(0, PAD_SM))

        SectionHeader(gen_card, "+", "Generate New Key", "").pack(
            fill="x", padx=PAD_SM, pady=(PAD_SM, PAD_SM))

        # Form row 1
        self._email_var = ctk.StringVar(value=self.app_state.get("git_email", ""))
        self._name_var = ctk.StringVar(value="id_ed25519")
        form1 = ctk.CTkFrame(gen_card, fg_color="transparent")
        form1.pack(fill="x", padx=PAD_SM, pady=(0, 6))
        Label(form1, text="Email:", size=12, color=TEXT_DIM).pack(side="left", padx=(0, 4))
        ctk.CTkEntry(
            form1, textvariable=self._email_var, width=200,
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            placeholder_text_color=TEXT_MUTED, corner_radius=8, height=34,
            font=ctk.CTkFont(family="Inter", size=12),
        ).pack(side="left", padx=(0, PAD_SM))
        Label(form1, text="Key name:", size=12, color=TEXT_DIM).pack(side="left", padx=(0, 4))
        ctk.CTkEntry(
            form1, textvariable=self._name_var, width=140,
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            placeholder_text_color=TEXT_MUTED, corner_radius=8, height=34,
            font=ctk.CTkFont(family="Inter", size=12),
        ).pack(side="left")

        # Form row 2
        self._passphrase_var = ctk.StringVar()
        form2 = ctk.CTkFrame(gen_card, fg_color="transparent")
        form2.pack(fill="x", padx=PAD_SM, pady=(0, PAD_SM))
        Label(form2, text="Passphrase (optional):", size=12, color=TEXT_DIM).pack(side="left", padx=(0, 4))
        ctk.CTkEntry(
            form2, textvariable=self._passphrase_var, show="*", width=220,
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            placeholder_text="Leave empty for no passphrase",
            placeholder_text_color=TEXT_MUTED, corner_radius=8, height=34,
            font=ctk.CTkFont(family="Inter", size=12),
        ).pack(side="left")

        # Generate button + status
        btn_row = ctk.CTkFrame(gen_card, fg_color="transparent")
        btn_row.pack(fill="x", padx=PAD_SM, pady=(0, PAD_SM))
        PrimaryButton(btn_row, text="Generate Key", width=150, height=36,
                      command=self._generate_key).pack(side="left")
        self._gen_status = StatusBadge(btn_row, status="pending", text="")
        self._gen_status.pack(side="left", padx=(PAD_SM, 0))

        # Public key display
        self._pub_key_box = ctk.CTkTextbox(
            gen_card,
            height=70,
            fg_color=BG,
            text_color=TEXT_DIM,
            font=ctk.CTkFont(family="JetBrains Mono", size=10),
            border_color=BORDER,
            border_width=1,
            corner_radius=8,
        )
        self._pub_key_box.pack(fill="x", padx=PAD_SM, pady=(0, PAD_SM))
        self._pub_key_box.configure(state="disabled")

        # --- Card: Deploy to Platforms ---
        deploy_card = Card(outer)
        deploy_card.pack(fill="x", pady=(0, PAD_SM))

        Label(deploy_card, text="Deploy to Platforms", size=14, bold=True).pack(
            anchor="w", padx=PAD_SM, pady=(PAD_SM, 2))
        Label(deploy_card, text="Add your public key to GitHub and GitLab",
              size=12, color=TEXT_DIM).pack(anchor="w", padx=PAD_SM, pady=(0, PAD_SM))

        # Key selector
        key_row = ctk.CTkFrame(deploy_card, fg_color="transparent")
        key_row.pack(fill="x", padx=PAD_SM, pady=(0, PAD_SM))
        Label(key_row, text="Key:", size=12, color=TEXT_DIM).pack(side="left", padx=(0, 6))
        self._deploy_key_var = ctk.StringVar()
        key_names = [k["name"] for k in self.ssh.get_existing_keys()]
        self._deploy_key_combo = ctk.CTkComboBox(
            key_row,
            variable=self._deploy_key_var,
            values=key_names if key_names else ["(none)"],
            width=200,
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            button_color=BG3, button_hover_color=BORDER,
            dropdown_fg_color=BG2, dropdown_text_color=TEXT,
            corner_radius=8, height=34,
            font=ctk.CTkFont(family="Inter", size=12),
        )
        self._deploy_key_combo.pack(side="left")
        if key_names:
            self._deploy_key_var.set(key_names[0])

        # Platform buttons
        plat_row = ctk.CTkFrame(deploy_card, fg_color="transparent")
        plat_row.pack(fill="x", padx=PAD_SM, pady=(0, PAD_SM))

        PrimaryButton(plat_row, text="Add to GitHub", width=130, height=34,
                      command=self._add_github).pack(side="left", padx=(0, 6))
        PrimaryButton(plat_row, text="Add to GitLab", width=130, height=34,
                      command=self._add_gitlab).pack(side="left", padx=(0, 6))
        SecondaryButton(plat_row, text="Test GitHub", width=110, height=34,
                        command=lambda: self._test_host("github.com")).pack(side="left", padx=(0, 6))
        SecondaryButton(plat_row, text="Test GitLab", width=110, height=34,
                        command=lambda: self._test_host("gitlab.com")).pack(side="left")

        # Platform status labels
        status_row = ctk.CTkFrame(deploy_card, fg_color="transparent")
        status_row.pack(fill="x", padx=PAD_SM, pady=(0, PAD_SM))
        Label(status_row, text="GitHub:", size=11, color=TEXT_DIM).pack(side="left", padx=(0, 4))
        self._github_status = StatusBadge(status_row, status="pending", text="—")
        self._github_status.pack(side="left", padx=(0, PAD_SM))
        Label(status_row, text="GitLab:", size=11, color=TEXT_DIM).pack(side="left", padx=(0, 4))
        self._gitlab_status = StatusBadge(status_row, status="pending", text="—")
        self._gitlab_status.pack(side="left")

    def _refresh_keys(self):
        for w in self._keys_frame.winfo_children():
            w.destroy()

        keys = self.ssh.get_existing_keys()
        if not keys:
            Label(self._keys_frame, text="No SSH keys found in ~/.ssh",
                  size=12, color=TEXT_MUTED).pack(anchor="w", pady=4)
            return

        for key in keys:
            row = ctk.CTkFrame(self._keys_frame, fg_color=BG3, corner_radius=8)
            row.pack(fill="x", pady=3)

            info = ctk.CTkFrame(row, fg_color="transparent")
            info.pack(side="left", fill="x", expand=True, padx=PAD_SM, pady=8)
            Label(info, text=key["name"], size=13, bold=True).pack(anchor="w")
            Label(info, text=key["public"], size=11, color=TEXT_MUTED).pack(anchor="w")

            btn_frame = ctk.CTkFrame(row, fg_color="transparent")
            btn_frame.pack(side="right", padx=PAD_SM, pady=6)

            # Copy badge (state holder)
            copy_badge = StatusBadge(btn_frame, status="pending", text="")
            copy_badge.pack(side="right", padx=(4, 0))

            key_name = key["name"]

            def make_copy_cmd(kname, badge):
                def _copy():
                    pub = self.ssh.get_public_key(kname)
                    if pub:
                        self.clipboard_clear()
                        self.clipboard_append(pub)
                        badge.update_status("ok", "Copied!")
                        self.after(2000, lambda: badge.update_status("pending", ""))
                return _copy

            def make_test_cmd(kname, badge):
                def _test():
                    badge.update_status("pending", "Testing...")

                    def worker():
                        ok_gh, msg_gh = self.ssh.test_connection("github.com")
                        ok_gl, msg_gl = self.ssh.test_connection("gitlab.com")
                        result_text = ("github: OK" if ok_gh else "github: FAIL") + \
                                      "  " + ("gitlab: OK" if ok_gl else "gitlab: FAIL")
                        status = "ok" if ok_gh or ok_gl else "error"
                        self.after(0, lambda: badge.update_status(status, result_text))

                    threading.Thread(target=worker, daemon=True).start()
                return _test

            SecondaryButton(btn_frame, text="Test", width=70, height=30,
                            command=make_test_cmd(key_name, copy_badge)).pack(side="right", padx=(4, 0))
            SecondaryButton(btn_frame, text="Copy Key", width=90, height=30,
                            command=make_copy_cmd(key_name, copy_badge)).pack(side="right", padx=(4, 0))

        # Update deploy key combo
        if self._deploy_key_combo is not None:
            key_names = [k["name"] for k in keys]
            self._deploy_key_combo.configure(values=key_names)
            if key_names:
                self._deploy_key_var.set(key_names[0])

    def _generate_key(self):
        email = self._email_var.get().strip()
        name = self._name_var.get().strip() or "id_ed25519"
        passphrase = self._passphrase_var.get()

        if not email:
            self._gen_status.update_status("error", "Email required")
            return

        self._gen_status.update_status("pending", "Generating...")

        def worker():
            ok, result, key_path = self.ssh.generate_key(email, name, passphrase)
            if ok:
                pub_key = result if result and result.startswith("ssh-") else self.ssh.get_public_key(name) or ""

                def update():
                    self._gen_status.update_status("ok", "Key generated!")
                    self._pub_key_box.configure(state="normal")
                    self._pub_key_box.delete("1.0", "end")
                    self._pub_key_box.insert("end", pub_key)
                    self._pub_key_box.configure(state="disabled")
                    self._refresh_keys()

                self.after(0, update)
            else:
                self.after(0, lambda: self._gen_status.update_status("error", f"Failed: {result[:50]}"))

        threading.Thread(target=worker, daemon=True).start()

    def _get_selected_pub_key(self):
        key_name = self._deploy_key_var.get()
        if not key_name or key_name == "(none)":
            return None, None
        pub = self.ssh.get_public_key(key_name)
        return key_name, pub

    def _add_github(self):
        key_name, pub = self._get_selected_pub_key()
        if not pub:
            self._github_status.update_status("error", "No key selected")
            return
        github_api = self.app_state.get("github_api")
        if not github_api:
            self._github_status.update_status("warning", "Connect GitHub first")
            return
        self._github_status.update_status("pending", "Adding...")

        def worker():
            ok, msg = github_api.add_ssh_key(f"git-pusher-{key_name}", pub)
            status = "ok" if ok else "error"
            text = "Added!" if ok else str(msg)[:40]
            self.after(0, lambda: self._github_status.update_status(status, text))

        threading.Thread(target=worker, daemon=True).start()

    def _add_gitlab(self):
        key_name, pub = self._get_selected_pub_key()
        if not pub:
            self._gitlab_status.update_status("error", "No key selected")
            return
        gitlab_api = self.app_state.get("gitlab_api")
        if not gitlab_api:
            self._gitlab_status.update_status("warning", "Connect GitLab first")
            return
        self._gitlab_status.update_status("pending", "Adding...")

        def worker():
            ok, msg = gitlab_api.add_ssh_key(f"git-pusher-{key_name}", pub)
            status = "ok" if ok else "error"
            text = "Added!" if ok else str(msg)[:40]
            self.after(0, lambda: self._gitlab_status.update_status(status, text))

        threading.Thread(target=worker, daemon=True).start()

    def _test_host(self, host):
        target_badge = self._github_status if "github" in host else self._gitlab_status
        target_badge.update_status("pending", "Testing...")

        def worker():
            ok, msg = self.ssh.test_connection(host)
            status = "ok" if ok else "error"
            text = "Connected!" if ok else "Failed"
            self.after(0, lambda: target_badge.update_status(status, text))

        threading.Thread(target=worker, daemon=True).start()
