#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  release.sh  —  Build and package Git Pusher for a GitHub/GitLab release
# ─────────────────────────────────────────────────────────────────────────────
set -e
cd "$(dirname "$0")"

VERSION="2.0.0"
APP="git-pusher"
RELEASE_DIR="release/v${VERSION}"

GREEN="\033[0;32m"; YELLOW="\033[1;33m"; RED="\033[0;31m"
BOLD="\033[1m"; DIM="\033[2m"; RESET="\033[0m"

bar() { echo "  ──────────────────────────────────────────"; }

echo ""
echo -e "${BOLD}  🚀  Git Pusher v${VERSION}  —  Release${RESET}"
bar
echo ""

# ── 1. Build binary ───────────────────────────────────────────────────────────
echo -e "  ${BOLD}Step 1/4:${RESET} Building standalone binary..."
bash build.sh
echo ""

# ── 2. Prepare release dir ────────────────────────────────────────────────────
echo -e "  ${BOLD}Step 2/4:${RESET} Preparing release package..."
rm -rf "$RELEASE_DIR"
mkdir -p "$RELEASE_DIR"

# Binary
ARCH=$(uname -m)
BINARY_NAME="${APP}-linux-${ARCH}"
cp "dist/${APP}" "${RELEASE_DIR}/${BINARY_NAME}"
chmod +x "${RELEASE_DIR}/${BINARY_NAME}"

# Source tarball (without build artifacts)
SOURCE_TAR="${APP}-${VERSION}-source.tar.gz"
tar --exclude='.git' \
    --exclude='build' \
    --exclude='dist' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='release' \
    --exclude='.venv' \
    -czf "${RELEASE_DIR}/${SOURCE_TAR}" \
    -C "$(dirname "$(realpath .)")" \
    "$(basename "$(realpath .)")"

# Checksums
cd "$RELEASE_DIR"
sha256sum "${BINARY_NAME}" "${SOURCE_TAR}" > SHA256SUMS
cd - > /dev/null

echo -e "  ${GREEN}✓${RESET}  ${RELEASE_DIR}/${BINARY_NAME}"
echo -e "  ${GREEN}✓${RESET}  ${RELEASE_DIR}/${SOURCE_TAR}"
echo -e "  ${GREEN}✓${RESET}  ${RELEASE_DIR}/SHA256SUMS"

# ── 3. Release notes ─────────────────────────────────────────────────────────
echo ""
echo -e "  ${BOLD}Step 3/4:${RESET} Writing release notes..."

cat > "${RELEASE_DIR}/RELEASE_NOTES.md" << NOTES
# Git Pusher v${VERSION}

**The first major release of Git Pusher** — the free, open-source GUI for GitHub & GitLab on Linux.

## Highlights

- 🚀 6-step push wizard with .gitignore generator, secret scanner, and README generator
- 📁 20-panel Repo Manager: clone, sync, branches, gitflow, diff viewer, and more
- 👥 Multi-account support (multiple GitHub + GitLab instances)
- ⏰ Scheduled push and Watch Mode (auto-commit on file changes)
- 🔑 SSH Key Manager — generate and register keys without touching the terminal
- 🌿 Gitflow automation — feature/release/hotfix/bugfix workflows in one click

## Installation

### Linux (x86_64) — standalone binary

\`\`\`bash
wget https://github.com/guenfils/git-pusher/releases/download/v${VERSION}/${APP}-linux-x86_64
chmod +x ${APP}-linux-x86_64
./${APP}-linux-x86_64
\`\`\`

### From source

\`\`\`bash
git clone https://github.com/guenfils/git-pusher.git
cd git-pusher
./install.sh
\`\`\`

## Full Changelog

See [CHANGELOG.md](https://github.com/guenfils/git-pusher/blob/main/CHANGELOG.md)

## Checksums

See \`SHA256SUMS\` in the release assets.
NOTES

echo -e "  ${GREEN}✓${RESET}  Release notes written"

# ── 4. Summary ────────────────────────────────────────────────────────────────
echo ""
bar
echo -e "  ${GREEN}${BOLD}✅  Release v${VERSION} ready!${RESET}"
echo ""
echo -e "  ${BOLD}Files in ${RELEASE_DIR}/:${RESET}"
ls -lh "$RELEASE_DIR"
echo ""
echo -e "  ${BOLD}Next steps to publish:${RESET}"
echo "    1. git init (if not done) && git add . && git commit -m 'Initial commit'"
echo "    2. git remote add origin https://github.com/guenfils/git-pusher.git"
echo "    3. git push -u origin main"
echo "    4. git tag v${VERSION} && git push origin v${VERSION}"
echo "    5. Upload files from ${RELEASE_DIR}/ to the GitHub release page"
echo ""
echo -e "  ${DIM}Or use GitHub CLI:${RESET}"
echo "    gh release create v${VERSION} ${RELEASE_DIR}/* --notes-file ${RELEASE_DIR}/RELEASE_NOTES.md"
echo ""
