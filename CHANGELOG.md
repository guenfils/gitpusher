# Changelog

**Developed by [Guenson](https://github.com/guenfils)**
All notable changes to Git Pusher are documented here.

---

## [2.0.0] — 2026-03-22

### Major release — Full Repo Manager with 20 panels

#### Push Wizard
- Per-platform git identity (different name/email for GitHub vs GitLab)
- Second push support: re-push to same branch or new branch for PR/MR
- `.gitignore` generator with auto-detection of project stack
- Sensitive file scanner (blocks `.env`, `.pem`, tokens before commit)
- `README.md` generator with live markdown preview
- Multi-repo batch push (push multiple projects at once)
- Automatic PR/MR creation after branch push

#### Repo Manager — 20 panels
- **Repositories** — browse, search, open repos on GitHub & GitLab
- **Clone** — graphical clone with folder picker and branch selection
- **Sync** — bidirectional pull/push/sync with status display
- **Tags & Releases** — semantic versioning, GitHub/GitLab release publishing
- **Commit History** — visual log with branch pills and author stats
- **SSH Keys** — generate, copy, and register SSH keys in-app
- **Templates** — project starters (FastAPI, Flask, Express, Go, Rust, Docker...)
- **Webhooks** — CI/CD webhook configuration with preset templates
- **Collaborators** — add/remove team members with role/access-level management
- **Issues** — full issue tracker (create, comment, close, reopen)
- **Accounts** — multi-account support (multiple GitHub + GitLab instances)
- **Scheduled Push** — time-based commit+push automation
- **Watch Mode** — folder monitoring with auto-commit on changes
- **Statistics** — commits by month chart, contributors, active files
- **Export / Backup** — download repo as ZIP or TAR.GZ
- **Stash** — visual stash manager (create, apply, pop, drop, preview)
- **Branches** — checkout, merge, delete, compare branches visually
- **Diff Viewer** — syntax-colored diff with stage/unstage/discard
- **Settings** — persistent preferences via ConfigManager
- **Gitflow** — Feature/Release/Hotfix/Bugfix workflow automation

#### App
- Professional logo (indigo gradient, rocket + git nodes)
- Logo displayed in titlebar and app window icon
- Scrollable sidebar in Repo Manager (supports all 20 tabs without clipping)
- Sidebar button height/width override fixed (CTkButton kwargs conflict resolved)

---

## [1.0.0] — 2025-01-01

### Initial release
- 5-step push wizard (System Check → Platform → Project → Branch → Upload)
- GitHub and GitLab support via personal access tokens
- SSH authentication support
- Single-project push to existing or new repository
- Dark theme UI with customtkinter
