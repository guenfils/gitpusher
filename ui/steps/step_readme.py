"""Step 4 – README Generator."""
import os
import datetime
import customtkinter as ctk
from ui.theme import *
from ui.widgets.common import (
    Card, PrimaryButton, SecondaryButton, Label, SectionHeader, LogBox
)


LICENSE_MAP = {
    "MIT":          "MIT",
    "Apache 2.0":   "Apache--2.0",
    "GPL-3.0":      "GPL--3.0",
    "BSD-3-Clause": "BSD--3--Clause",
    "None":         None,
}

LICENSES = list(LICENSE_MAP.keys())


def _badge_url(license_name):
    slug = LICENSE_MAP.get(license_name)
    if slug:
        return f"![License](https://img.shields.io/badge/license-{slug}-blue.svg)"
    return ""


def _build_readme(name, tagline, license_name, sections, python_badge, node_badge):
    year = datetime.datetime.now().year
    lines = []

    lines.append(f"# {name}")
    lines.append("")
    if tagline:
        lines.append(f"> {tagline}")
        lines.append("")

    badges = []
    lb = _badge_url(license_name)
    if lb:
        badges.append(lb)
    if python_badge:
        badges.append("![Python](https://img.shields.io/badge/python-3.x-blue.svg)")
    if node_badge:
        badges.append("![Node](https://img.shields.io/badge/node-%3E%3D14-green.svg)")
    if badges:
        lines.append("  ".join(badges))
        lines.append("")

    lines.append("## Description")
    lines.append("")
    lines.append(tagline if tagline else "_Add a detailed description of your project here._")
    lines.append("")

    if "Installation" in sections:
        lines.append("## Installation")
        lines.append("")
        lines.append("```bash")
        lines.append("# Clone the repository")
        lines.append(f"git clone https://github.com/your-username/{name}.git")
        lines.append(f"cd {name}")
        lines.append("")
        lines.append("# Install dependencies")
        lines.append("# (add your installation steps here)")
        lines.append("```")
        lines.append("")

    if "Usage" in sections:
        lines.append("## Usage")
        lines.append("")
        lines.append("```bash")
        lines.append("# Add usage examples here")
        lines.append("```")
        lines.append("")

    if "Contributing" in sections:
        lines.append("## Contributing")
        lines.append("")
        lines.append("Contributions are welcome! Please feel free to submit a Pull Request.")
        lines.append("")
        lines.append("1. Fork the repository")
        lines.append("2. Create your feature branch (`git checkout -b feature/AmazingFeature`)")
        lines.append("3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)")
        lines.append("4. Push to the branch (`git push origin feature/AmazingFeature`)")
        lines.append("5. Open a Pull Request")
        lines.append("")

    if "Changelog" in sections:
        lines.append("## Changelog")
        lines.append("")
        lines.append(f"### [{year}]")
        lines.append("- Initial release")
        lines.append("")

    if license_name and license_name != "None":
        lines.append("## License")
        lines.append("")
        lines.append(f"{license_name} © {year}")
        lines.append("")

    return "\n".join(lines)


class StepReadme(ctk.CTkFrame):
    def __init__(self, master, app_state, on_next, on_back, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app_state = app_state
        self.on_next   = on_next
        self.on_back   = on_back
        self._build()

    def _build(self):
        Label(self, text="README Generator", size=22, bold=True).pack(anchor="w", pady=(0, 4))
        Label(self, text="Create a professional README for your project",
              size=13, color=TEXT_DIM).pack(anchor="w", pady=(0, PAD))

        project_path = self.app_state.get("project_path", "")
        readme_path  = os.path.join(project_path, "README.md") if project_path else ""
        readme_exists = bool(readme_path and os.path.exists(readme_path))

        self._overwrite_allowed = not readme_exists

        # ── Existing README warning ───────────────────────────────────────
        if readme_exists:
            warn_card = Card(self)
            warn_card.pack(fill="x", pady=(0, PAD_SM))
            warn_row = ctk.CTkFrame(warn_card, fg_color="transparent")
            warn_row.pack(fill="x", padx=PAD, pady=PAD)
            ctk.CTkLabel(
                warn_row, text="⚠",
                font=ctk.CTkFont(size=20), text_color=WARNING,
            ).pack(side="left", padx=(0, PAD_SM))
            txt_col = ctk.CTkFrame(warn_row, fg_color="transparent")
            txt_col.pack(side="left", fill="x", expand=True)
            Label(txt_col, text="README.md already exists",
                  size=13, bold=True, color=WARNING).pack(anchor="w")
            Label(txt_col, text="Choose to skip or overwrite the existing file.",
                  size=12, color=TEXT_DIM).pack(anchor="w")

            action_row = ctk.CTkFrame(warn_card, fg_color="transparent")
            action_row.pack(fill="x", padx=PAD, pady=(0, PAD))

            self._overwrite_var = ctk.BooleanVar(value=False)

            def _toggle_overwrite():
                self._overwrite_allowed = self._overwrite_var.get()
                self._form_card.configure(
                    fg_color=BG2 if self._overwrite_allowed else BG3)

            ctk.CTkCheckBox(
                action_row,
                text="Overwrite existing README.md",
                variable=self._overwrite_var,
                command=_toggle_overwrite,
                font=ctk.CTkFont(family="Inter", size=12),
                text_color=TEXT, fg_color=PRIMARY, hover_color=PRIMARY_H,
            ).pack(side="left")

            SecondaryButton(
                action_row,
                text="Skip  →",
                command=self._skip,
                width=100, height=36,
            ).pack(side="right")

        # ── Form card ─────────────────────────────────────────────────────
        self._form_card = Card(self)
        self._form_card.pack(fill="x", pady=(0, PAD_SM))

        Label(self._form_card, text="README Details", size=13, bold=True).pack(
            anchor="w", padx=PAD, pady=(PAD, PAD_SM))

        form_inner = ctk.CTkFrame(self._form_card, fg_color="transparent")
        form_inner.pack(fill="x", padx=PAD, pady=(0, PAD_SM))
        form_inner.columnconfigure(1, weight=1)

        # Project name
        Label(form_inner, text="Project Name:", size=12, color=TEXT_DIM).grid(
            row=0, column=0, sticky="w", pady=(0, PAD_SM), padx=(0, PAD_SM))
        self._name_var = ctk.StringVar(
            value=self.app_state.get("repo_name", "my-project"))
        ctk.CTkEntry(
            form_inner, textvariable=self._name_var,
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            font=ctk.CTkFont(family="Inter", size=12), height=38, corner_radius=8,
        ).grid(row=0, column=1, sticky="ew", pady=(0, PAD_SM))

        # Tagline
        Label(form_inner, text="Tagline:", size=12, color=TEXT_DIM).grid(
            row=1, column=0, sticky="w", pady=(0, PAD_SM), padx=(0, PAD_SM))
        self._tagline_var = ctk.StringVar(
            value=self.app_state.get("description", ""))
        self._tagline_entry = ctk.CTkEntry(
            form_inner, textvariable=self._tagline_var,
            placeholder_text="A short catchy description",
            fg_color=BG3, border_color=BORDER, text_color=TEXT,
            font=ctk.CTkFont(family="Inter", size=12), height=38, corner_radius=8,
        )
        self._tagline_entry.grid(row=1, column=1, sticky="ew", pady=(0, PAD_SM))

        # License
        Label(form_inner, text="License:", size=12, color=TEXT_DIM).grid(
            row=2, column=0, sticky="w", pady=(0, PAD_SM), padx=(0, PAD_SM))
        self._license_var = ctk.StringVar(value="MIT")
        ctk.CTkOptionMenu(
            form_inner,
            variable=self._license_var,
            values=LICENSES,
            fg_color=BG3, button_color=BORDER, button_hover_color=PRIMARY,
            text_color=TEXT,
            font=ctk.CTkFont(family="Inter", size=12),
            command=lambda _: self._update_preview(),
        ).grid(row=2, column=1, sticky="w", pady=(0, PAD_SM))

        # Bind name/tagline for live preview
        self._name_var.trace_add("write", lambda *a: self._update_preview())
        self._tagline_var.trace_add("write", lambda *a: self._update_preview())
        self._license_var.trace_add("write", lambda *a: self._update_preview())

        # Sections checkboxes
        Label(self._form_card, text="Sections to include:", size=12, bold=True).pack(
            anchor="w", padx=PAD, pady=(0, PAD_SM))
        sections_row = ctk.CTkFrame(self._form_card, fg_color="transparent")
        sections_row.pack(fill="x", padx=PAD, pady=(0, PAD_SM))

        self._section_vars = {}
        defaults = {"Installation": True, "Usage": True,
                    "Contributing": False, "Changelog": False}
        for sec, default in defaults.items():
            var = ctk.BooleanVar(value=default)
            self._section_vars[sec] = var
            ctk.CTkCheckBox(
                sections_row, text=sec, variable=var,
                command=self._update_preview,
                font=ctk.CTkFont(family="Inter", size=12),
                text_color=TEXT, fg_color=PRIMARY, hover_color=PRIMARY_H,
            ).pack(side="left", padx=(0, PAD_SM))

        # Badge toggles
        badge_row = ctk.CTkFrame(self._form_card, fg_color="transparent")
        badge_row.pack(fill="x", padx=PAD, pady=(0, PAD_SM))
        Label(badge_row, text="Badges:", size=12, color=TEXT_DIM).pack(
            side="left", padx=(0, PAD_SM))
        self._python_badge_var = ctk.BooleanVar(value=False)
        self._node_badge_var   = ctk.BooleanVar(value=False)
        for text, var in [("Python", self._python_badge_var),
                          ("Node.js", self._node_badge_var)]:
            ctk.CTkCheckBox(
                badge_row, text=text, variable=var,
                command=self._update_preview,
                font=ctk.CTkFont(family="Inter", size=12),
                text_color=TEXT, fg_color=PRIMARY, hover_color=PRIMARY_H,
            ).pack(side="left", padx=(0, PAD_SM))

        # Preview
        Label(self._form_card, text="Preview (Markdown):", size=12, bold=True).pack(
            anchor="w", padx=PAD, pady=(0, PAD_SM))
        self._preview = LogBox(self._form_card, height=200)
        self._preview.pack(fill="x", padx=PAD, pady=(0, PAD_SM))

        # Generate button
        gen_row = ctk.CTkFrame(self._form_card, fg_color="transparent")
        gen_row.pack(fill="x", padx=PAD, pady=(0, PAD))
        self._gen_btn = PrimaryButton(
            gen_row, text="Generate README",
            command=self._generate_readme, width=180, height=38)
        self._gen_btn.pack(side="left")
        self._gen_confirm = Label(gen_row, text="", size=12, color=SUCCESS)
        self._gen_confirm.pack(side="left", padx=(PAD_SM, 0))

        # ── Navigation ────────────────────────────────────────────────────
        nav = ctk.CTkFrame(self, fg_color="transparent")
        nav.pack(fill="x", pady=(PAD, 0))
        SecondaryButton(nav, text="← Back", command=self.on_back, width=120).pack(side="left")
        SecondaryButton(nav, text="Skip", command=self._skip, width=100).pack(
            side="left", padx=(PAD_SM, 0))
        PrimaryButton(nav, text="Continue  →", command=self.on_next, width=180).pack(side="right")

        # Initial preview
        self._update_preview()

    def _get_selected_sections(self):
        return [s for s, v in self._section_vars.items() if v.get()]

    def _update_preview(self):
        content = _build_readme(
            name=self._name_var.get().strip() or "my-project",
            tagline=self._tagline_var.get().strip(),
            license_name=self._license_var.get(),
            sections=self._get_selected_sections(),
            python_badge=self._python_badge_var.get(),
            node_badge=self._node_badge_var.get(),
        )
        self._preview.clear()
        self._preview.configure(state="normal")
        self._preview.delete("1.0", "end")
        self._preview.insert("end", content)
        self._preview.configure(state="disabled")

    def _generate_readme(self):
        if not self._overwrite_allowed:
            self._gen_confirm.configure(
                text="Enable overwrite first", text_color=WARNING)
            return
        project_path = self.app_state.get("project_path", "")
        if not project_path:
            return
        content = _build_readme(
            name=self._name_var.get().strip() or "my-project",
            tagline=self._tagline_var.get().strip(),
            license_name=self._license_var.get(),
            sections=self._get_selected_sections(),
            python_badge=self._python_badge_var.get(),
            node_badge=self._node_badge_var.get(),
        )
        readme_path = os.path.join(project_path, "README.md")
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(content)
        self.app_state["readme_generated"] = True
        self._gen_confirm.configure(text="✓ README.md created", text_color=SUCCESS)
        self._gen_btn.configure(state="disabled")

    def _skip(self):
        self.app_state["readme_generated"] = False
        self.on_next()
