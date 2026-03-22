<div align="center">

<img src="assets/icon.png" width="120" alt="Git Pusher Logo"/>

# Git Pusher

**GitHub & GitLab in one click — the all-in-one GUI for developers**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://python.org)
[![Platform](https://img.shields.io/badge/Platform-Linux-orange?logo=linux&logoColor=white)](https://kernel.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Release](https://img.shields.io/badge/Release-v2.0.0-indigo)](https://github.com/guenfils/git-pusher/releases)
[![Stars](https://img.shields.io/github/stars/guenfils/git-pusher?style=social)](https://github.com/guenfils/git-pusher)

Push, clone, branch, sync, and manage your repositories on **GitHub and GitLab** from a single beautiful desktop app — no terminal required.

[Download](#installation) · [Features](#features) · [Screenshots](#screenshots) · [Contributing](#contributing)

</div>

---

## Why Git Pusher?

| Tool | GitHub | GitLab | Free | Linux |
|---|:---:|:---:|:---:|:---:|
| **Git Pusher** | ✅ | ✅ | ✅ | ✅ |
| GitHub Desktop | ✅ | ❌ | ✅ | ❌ |
| GitKraken | ✅ | ✅ | ⚠️ | ✅ |
| SourceTree | ✅ | ✅ | ✅ | ❌ |

Git Pusher is the **only free, Linux-native GUI** that manages both GitHub and GitLab with a full feature set — from the first push to gitflow automation.

---

## Features

### 🚀 Push Wizard
Step-by-step guided workflow to push any project in minutes:
- **System check** — verifies git, SSH, and per-platform identity (GitHub vs GitLab)
- **.gitignore generator** — auto-detects your stack (Python, Node, Go, Rust, etc.)
- **Secret scanner** — blocks accidental commits of `.env`, `.pem`, tokens, and credentials
- **README generator** — creates a professional `README.md` with badges and sections
- **Branch configurator** — first push, re-push to same branch, or new branch for PR/MR
- **Multi-repo upload** — push multiple projects in one batch operation

### 📁 Repo Manager (20 panels)

| Category | Features |
|---|---|
| **Repos** | Browse, search, and open your GitHub/GitLab repos |
| **Clone** | Clone any repo with folder picker and branch selection |
| **Sync** | Pull, push, and full sync with conflict detection |
| **Tags & Releases** | Create semantic tags, publish GitHub/GitLab releases |
| **Commit History** | Visual log with branch pills, author, and stats |
| **SSH Keys** | Generate, copy, and add SSH keys to GitHub/GitLab |
| **Templates** | Start projects from FastAPI, React, Django, Go, Rust... |
| **Webhooks** | Configure CI/CD webhooks with preset templates |
| **Collaborators** | Add/remove team members with role management |
| **Issues** | Create, view, comment, and close issues in-app |
| **Accounts** | Manage multiple GitHub/GitLab accounts simultaneously |
| **Scheduled Push** | Commit+push at a specific date/time automatically |
| **Watch Mode** | Auto-commit on file changes (autosave to git) |
| **Statistics** | Commits by month, contributors, most active files |
| **Export / Backup** | Download repo as ZIP or TAR.GZ |
| **Stash** | Create, apply, pop, and drop git stashes visually |
| **Branches** | Checkout, merge, delete, and compare branches |
| **Diff Viewer** | Syntax-colored diff with stage/unstage/discard actions |
| **Settings** | Persistent preferences, credentials, gitflow defaults |
| **Gitflow** | Feature/Release/Hotfix/Bugfix branch automation |

---

## Installation

### Option 1 — Download binary (recommended)

```bash
# Download the latest release
wget https://github.com/guenfils/git-pusher/releases/latest/download/git-pusher-linux-x86_64

# Make executable and run
chmod +x git-pusher-linux-x86_64
./git-pusher-linux-x86_64
```

### Option 2 — Install from source

```bash
# Clone the repo
git clone https://github.com/guenfils/git-pusher.git
cd git-pusher

# Install system-wide (creates desktop entry + app menu shortcut)
./install.sh
```

### Option 3 — Dev / run directly

```bash
git clone https://github.com/guenfils/git-pusher.git
cd git-pusher
./run.sh        # auto-installs dependencies and launches
```

### Build standalone binary

```bash
./build.sh      # produces dist/git-pusher (~50MB, no Python needed)
./install.sh    # installs it system-wide
```

**Requirements:** Python 3.10+, Linux (X11/Wayland)

---

## Screenshots

> _Screenshots coming soon. Run the app to explore!_

---

## Quick Start

1. Launch the app → **System Check** verifies your git setup
2. **Platform** tab → enter your GitHub/GitLab personal access token
3. **Project** tab → select your local folder, auto-generates `.gitignore`
4. **README** tab → fill in project details, preview your README
5. **Branch** tab → choose `main`, or a new branch for a PR/MR
6. **Upload** → one click pushes to GitHub and/or GitLab simultaneously

For repo management: click **Manage Repos** in the top bar.

---

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

```bash
# Fork → clone → create branch
git checkout -b feature/my-feature

# Make changes, then run
./run.sh

# Submit a Pull Request
```

**Ways to contribute:**
- 🐛 Report bugs via [Issues](https://github.com/guenfils/git-pusher/issues)
- 💡 Request features via [Issues](https://github.com/guenfils/git-pusher/issues)
- 🌍 Add translations
- ⭐ Star the repo if you find it useful!

---

## Roadmap

- [ ] Windows support
- [ ] macOS support
- [ ] Dark/Light theme toggle
- [ ] Notification system (push completed, watch mode alert)
- [ ] Plugin system for custom panels

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

Made with ❤️ by **[Guenson](https://github.com/guenfils)** for the developer community

**[⭐ Star on GitHub](https://github.com/guenfils/git-pusher)** to support the project

</div>
