#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  uninstall-dev.sh  —  Remove Git Pusher dev install
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

APP="git-pusher-dev"
DISPLAY_NAME="Git Pusher Dev"
INSTALL_ROOT="${GIT_PUSHER_DEV_INSTALL_ROOT:-$HOME/.local/share/${APP}}"
APP_ROOT="${INSTALL_ROOT}/current"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons/hicolor"
CONFIG_ROOT="${GIT_PUSHER_CONFIG_ROOT:-$HOME/.config/${APP}}"

GREEN="\033[0;32m"; YELLOW="\033[1;33m"; BOLD="\033[1m"; DIM="\033[2m"; RESET="\033[0m"

bar() { echo "  ──────────────────────────────────────────"; }

echo ""
echo -e "${BOLD}  🗑️   ${DISPLAY_NAME}  —  Uninstall${RESET}"
bar
echo ""

read -rp "  Remove ${DISPLAY_NAME} from the system? [y/N] " CONFIRM
if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    echo "  Cancelled."
    exit 0
fi
echo ""

rm -f "${BIN_DIR}/${APP}"
rm -f "${DESKTOP_DIR}/${APP}.desktop"
rm -rf "$APP_ROOT"

for SIZE in 48 128 256; do
    rm -f "${ICON_DIR}/${SIZE}x${SIZE}/apps/${APP}.png"
done

update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
gtk-update-icon-cache -f -t "$ICON_DIR" 2>/dev/null || true
xdg-desktop-menu forceupdate 2>/dev/null || true

echo -e "  ${GREEN}✓${RESET}  Launcher, desktop entry, icons, and app root removed"
echo ""
echo -e "  ${DIM}Config kept at ${CONFIG_ROOT}${RESET}"
echo ""
