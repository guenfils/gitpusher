#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  install.sh  —  Install Git Pusher as a desktop application
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail
cd "$(dirname "$0")"

APP="git-pusher"
VERSION="2.1.0"
SCRIPT_DIR="$(realpath .)"
INSTALL_DIR="$HOME/.local/bin"
ICON_DIR="$HOME/.local/share/icons/hicolor"
DESKTOP_DIR="$HOME/.local/share/applications"

GREEN="\033[0;32m"; YELLOW="\033[1;33m"; RED="\033[0;31m"
BOLD="\033[1m"; DIM="\033[2m"; RESET="\033[0m"

bar() { echo "  ──────────────────────────────────────────"; }

echo ""
echo -e "${BOLD}  🚀  Git Pusher v${VERSION}  —  Install${RESET}"
bar
echo ""

# ── 1. Executable ─────────────────────────────────────────────────────────────
mkdir -p "$INSTALL_DIR"

if [ -f "dist/${APP}" ]; then
    # PyInstaller binary (standalone, no Python needed)
    cp "dist/${APP}" "$INSTALL_DIR/${APP}"
    chmod +x "$INSTALL_DIR/${APP}"
    EXEC_TYPE="standalone binary"
else
    # Fallback: Python wrapper (requires Python + deps installed)
    echo -e "  ${YELLOW}⚠  No compiled binary found. Installing Python wrapper.${RESET}"
    echo -e "  ${DIM}   Run ./build.sh first to create a standalone binary.${RESET}"
    echo ""

    cat > "$INSTALL_DIR/${APP}" << WRAPPER
#!/usr/bin/env bash
cd "${SCRIPT_DIR}"
if [ -x ".venv/bin/python" ]; then
    exec .venv/bin/python main.py "\$@"
fi
exec python3 main.py "\$@"
WRAPPER
    chmod +x "$INSTALL_DIR/${APP}"
    EXEC_TYPE="Python wrapper"
fi
echo -e "  ${GREEN}✓${RESET}  Executable (${EXEC_TYPE})  →  ${INSTALL_DIR}/${APP}"

# ── 2. Icons ──────────────────────────────────────────────────────────────────
for SIZE in 48 128 256; do
    ICON_PATH="${ICON_DIR}/${SIZE}x${SIZE}/apps"
    mkdir -p "$ICON_PATH"
    SRC="assets/icon_${SIZE}.png"
    [ -f "$SRC" ] || SRC="assets/icon.png"
    [ -f "$SRC" ] && cp "$SRC" "${ICON_PATH}/${APP}.png"
done
echo -e "  ${GREEN}✓${RESET}  Icons installed  (48 / 128 / 256 px)"

# ── 3. Desktop entry ──────────────────────────────────────────────────────────
mkdir -p "$DESKTOP_DIR"

ICON_256="${ICON_DIR}/256x256/apps/${APP}.png"
ICON_KEY="${APP}"
[ -f "$ICON_256" ] && ICON_KEY="$ICON_256"

cat > "${DESKTOP_DIR}/${APP}.desktop" << DESKTOP
[Desktop Entry]
Version=1.0
Type=Application
Name=Git Pusher
GenericName=GitHub & GitLab Manager
Comment=Push, clone and manage GitHub & GitLab repos in one click
Exec=${INSTALL_DIR}/${APP}
Icon=${ICON_KEY}
Terminal=false
StartupNotify=true
Categories=Development;RevisionControl;
Keywords=git;github;gitlab;push;clone;repository;branches;tags;
StartupWMClass=${APP}
DESKTOP

chmod +x "${DESKTOP_DIR}/${APP}.desktop"
echo -e "  ${GREEN}✓${RESET}  Desktop entry  →  ${DESKTOP_DIR}/${APP}.desktop"

# ── 4. Update caches ─────────────────────────────────────────────────────────
update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
gtk-update-icon-cache -f -t "$ICON_DIR" 2>/dev/null || true
xdg-desktop-menu forceupdate 2>/dev/null || true
echo -e "  ${GREEN}✓${RESET}  Desktop database updated"

# ── 5. PATH check ─────────────────────────────────────────────────────────────
if [[ ":$PATH:" != *":${INSTALL_DIR}:"* ]]; then
    echo ""
    echo -e "  ${YELLOW}⚠  ${INSTALL_DIR} is not in PATH.${RESET}"
    echo    "     Add this line to your ~/.bashrc or ~/.zshrc:"
    echo -e "     ${BOLD}export PATH=\"\$HOME/.local/bin:\$PATH\"${RESET}"
    echo    "     Then run:  source ~/.bashrc"
fi

echo ""
bar
echo -e "  ${GREEN}${BOLD}✅  Git Pusher v${VERSION} installed!${RESET}"
echo ""
echo -e "  ${BOLD}Launch with:${RESET}"
echo    "    • App menu    →  search 'Git Pusher'"
echo    "    • Terminal    →  git-pusher"
echo    "    • Dev mode    →  ./run.sh"
echo ""
echo -e "  ${DIM}Uninstall: ./uninstall.sh${RESET}"
echo ""
