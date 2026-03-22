#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  uninstall.sh  —  Remove Git Pusher from the system
# ─────────────────────────────────────────────────────────────────────────────
set -e

APP="git-pusher"
INSTALL_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons/hicolor"

GREEN="\033[0;32m"; YELLOW="\033[1;33m"; BOLD="\033[1m"; DIM="\033[2m"; RESET="\033[0m"

bar() { echo "  ──────────────────────────────────────────"; }

echo ""
echo -e "${BOLD}  🗑️   Git Pusher  —  Uninstall${RESET}"
bar
echo ""

# Confirm
read -rp "  Remove Git Pusher from the system? [y/N] " CONFIRM
if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    echo "  Cancelled."; exit 0
fi
echo ""

# Executable
if [ -f "${INSTALL_DIR}/${APP}" ]; then
    rm -f "${INSTALL_DIR}/${APP}"
    echo -e "  ${GREEN}✓${RESET}  Executable removed"
else
    echo -e "  ${DIM}  (no executable found)${RESET}"
fi

# Desktop entry
if [ -f "${DESKTOP_DIR}/${APP}.desktop" ]; then
    rm -f "${DESKTOP_DIR}/${APP}.desktop"
    echo -e "  ${GREEN}✓${RESET}  Desktop entry removed"
fi

# Icons
for SIZE in 48 128 256; do
    rm -f "${ICON_DIR}/${SIZE}x${SIZE}/apps/${APP}.png"
done
echo -e "  ${GREEN}✓${RESET}  Icons removed"

# Update caches
update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
gtk-update-icon-cache -f -t "$ICON_DIR" 2>/dev/null || true
xdg-desktop-menu forceupdate 2>/dev/null || true

echo ""
bar
echo -e "  ${GREEN}${BOLD}✅  Git Pusher uninstalled.${RESET}"
echo ""
echo -e "  ${DIM}Your config at ~/.config/git-pusher/ was kept."
echo -e "  Remove it with:  rm -rf ~/.config/git-pusher${RESET}"
echo ""
