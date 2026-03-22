# Contributing to Git Pusher

Thank you for your interest in contributing! Every contribution helps make Git Pusher better for the entire developer community.

---

## Ways to Contribute

- **Bug reports** — found something broken? Open an issue
- **Feature requests** — have an idea? Open an issue with the `enhancement` label
- **Code** — fix a bug or add a feature via Pull Request
- **Translations** — help make the app accessible in more languages
- **Documentation** — improve the README or add examples

---

## Development Setup

```bash
# Fork the repo on GitHub, then:
git clone https://github.com/YOUR_USERNAME/git-pusher.git
cd git-pusher

# Run directly (auto-installs dependencies)
./run.sh
```

No virtualenv required — the app uses standard pip packages.

**Dependencies:**
```
customtkinter, requests, paramiko, Pillow, cryptography, darkdetect
```

---

## Project Structure

```
git-pusher/
├── main.py                  # Entry point
├── core/
│   ├── git_manager.py       # Git operations (subprocess wrapper)
│   ├── github_api.py        # GitHub REST API client
│   ├── gitlab_api.py        # GitLab REST API client
│   ├── config_manager.py    # Persistent config (~/.config/git-pusher/)
│   ├── ssh_manager.py       # SSH key management
│   ├── gitignore_manager.py # .gitignore generation
│   └── secret_scanner.py    # Sensitive file detection
├── ui/
│   ├── app.py               # Main window + wizard
│   ├── theme.py             # Color constants
│   ├── manage_view.py       # Repo Manager sidebar layout
│   ├── steps/               # 6-step push wizard
│   ├── panels/              # 20 Repo Manager panels
│   └── widgets/             # Reusable UI components
└── assets/
    └── icon.png             # App logo
```

---

## Adding a New Panel

1. Create `ui/panels/panel_yourfeature.py`:

```python
import customtkinter as ctk
from ui.theme import *
from ui.widgets.common import Card, Label, PrimaryButton

class PanelYourFeature(ctk.CTkFrame):
    def __init__(self, master, app_state, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app_state = app_state
        self._build_ui()

    def _build_ui(self):
        Label(self, text="Your Feature", size=22, bold=True).pack(
            anchor="w", padx=20, pady=(20, 8)
        )
        # ... your UI here
```

2. Register it in `ui/manage_view.py`:

```python
from ui.panels.panel_yourfeature import PanelYourFeature

TABS = [
    ...
    ("Your Feature", PanelYourFeature),
]
TAB_ICONS = [
    ...
    "  Your Feature",
]
```

3. Add to `git-pusher.spec` hiddenimports:
```python
"ui.panels.panel_yourfeature",
```

---

## Code Style

- **Python 3.10+** syntax
- 4-space indentation
- Threading: all network/git operations in `threading.Thread(daemon=True)`
- UI updates from threads: always use `self.after(0, lambda: ...)`
- Widget defaults: use `PrimaryButton`, `SecondaryButton`, `Card`, `Label` from `ui/widgets/common.py`

---

## Pull Request Process

1. Fork the repo and create a feature branch: `git checkout -b feature/my-feature`
2. Make your changes
3. Run a syntax check: `python3 -m py_compile **/*.py`
4. Test the app: `./run.sh`
5. Open a PR with a clear description of what you changed and why

---

## Reporting Bugs

Please include:
- OS and Python version
- Steps to reproduce
- Expected vs actual behavior
- Any error messages from the terminal (`./run.sh` shows errors)

---

## Code of Conduct

Be respectful and constructive. See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
