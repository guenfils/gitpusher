#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  install-dev.sh  —  Install Git Pusher dev build side by side
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail
cd "$(dirname "$0")"

APP="git-pusher-dev"
DISPLAY_NAME="Git Pusher Dev"
VERSION="2.1.0-dev"
SOURCE_DIR="$(pwd -P)"
INSTALL_ROOT="${GIT_PUSHER_DEV_INSTALL_ROOT:-$HOME/.local/share/${APP}}"
APP_ROOT="${INSTALL_ROOT}/current"
BIN_DIR="$HOME/.local/bin"
ICON_DIR="$HOME/.local/share/icons/hicolor"
DESKTOP_DIR="$HOME/.local/share/applications"
CONFIG_ROOT="${GIT_PUSHER_CONFIG_ROOT:-$HOME/.config/${APP}}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
INSTALL_DEPS="${GIT_PUSHER_DEV_INSTALL_DEPS:-1}"

GREEN="\033[0;32m"; YELLOW="\033[1;33m"; RED="\033[0;31m"
BOLD="\033[1m"; DIM="\033[2m"; RESET="\033[0m"

bar() { echo "  ──────────────────────────────────────────"; }

require_file() {
    local path="$1"
    if [ ! -e "$path" ]; then
        echo -e "  ${RED}✗${RESET}  Missing required path: ${path}"
        exit 1
    fi
}

echo ""
echo -e "${BOLD}  🚀  ${DISPLAY_NAME} ${VERSION}  —  Install${RESET}"
bar
echo ""

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    echo -e "  ${RED}✗${RESET}  ${PYTHON_BIN} not found."
    exit 1
fi

for path in assets core ui main.py README.md requirements.txt run.sh doctor.sh bootstrap-dev.sh; do
    require_file "$path"
done

mkdir -p "$INSTALL_ROOT" "$BIN_DIR" "$DESKTOP_DIR"

echo -e "  ${DIM}Copying app payload...${RESET}"
rm -rf "$APP_ROOT"
mkdir -p "$APP_ROOT"
for path in assets core ui main.py README.md LICENSE requirements.txt run.sh doctor.sh bootstrap-dev.sh install-dev.sh uninstall-dev.sh; do
    if [ -e "$path" ]; then
        cp -a "$path" "$APP_ROOT/"
    fi
done
echo -e "  ${GREEN}✓${RESET}  Payload copied to ${APP_ROOT}"

echo -e "  ${DIM}Bootstrapping local dev runtime...${RESET}"
BOOTSTRAP_ARGS=(--repo-root "$APP_ROOT" --bootstrap)
if [ "$INSTALL_DEPS" != "0" ]; then
    BOOTSTRAP_ARGS+=(--install-missing)
fi
if ! (
    cd "$APP_ROOT"
    GIT_PUSHER_CONFIG_ROOT="$CONFIG_ROOT" "$PYTHON_BIN" -m core.dev_bootstrap "${BOOTSTRAP_ARGS[@]}"
); then
    echo -e "  ${RED}✗${RESET}  Dev bootstrap failed."
    exit 1
fi
echo -e "  ${GREEN}✓${RESET}  Runtime ready"

cat > "${BIN_DIR}/${APP}" <<WRAPPER
#!/usr/bin/env bash
export GIT_PUSHER_CONFIG_ROOT="\${GIT_PUSHER_CONFIG_ROOT:-${CONFIG_ROOT}}"
cd "${APP_ROOT}"
if [ -x ".venv/bin/python" ]; then
    exec .venv/bin/python main.py "\$@"
fi
exec ${PYTHON_BIN} main.py "\$@"
WRAPPER
chmod +x "${BIN_DIR}/${APP}"
echo -e "  ${GREEN}✓${RESET}  Launcher installed  →  ${BIN_DIR}/${APP}"

for SIZE in 48 128 256; do
    ICON_PATH="${ICON_DIR}/${SIZE}x${SIZE}/apps"
    mkdir -p "$ICON_PATH"
    SRC="${APP_ROOT}/assets/icon_${SIZE}.png"
    [ -f "$SRC" ] || SRC="${APP_ROOT}/assets/icon.png"
    [ -f "$SRC" ] && cp "$SRC" "${ICON_PATH}/${APP}.png"
done
echo -e "  ${GREEN}✓${RESET}  Icons installed"

ICON_256="${ICON_DIR}/256x256/apps/${APP}.png"
ICON_KEY="${APP}"
[ -f "$ICON_256" ] && ICON_KEY="$ICON_256"

cat > "${DESKTOP_DIR}/${APP}.desktop" <<DESKTOP
[Desktop Entry]
Version=1.0
Type=Application
Name=${DISPLAY_NAME}
GenericName=GitHub & GitLab Manager
Comment=Source-based dev install of Git Pusher
Exec=${BIN_DIR}/${APP}
Icon=${ICON_KEY}
Terminal=false
StartupNotify=true
Categories=Development;RevisionControl;
Keywords=git;github;gitlab;dev;push;clone;repository;
StartupWMClass=${APP}
DESKTOP
chmod +x "${DESKTOP_DIR}/${APP}.desktop"
echo -e "  ${GREEN}✓${RESET}  Desktop entry installed"

update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
gtk-update-icon-cache -f -t "$ICON_DIR" 2>/dev/null || true
xdg-desktop-menu forceupdate 2>/dev/null || true

if [[ ":$PATH:" != *":${BIN_DIR}:"* ]]; then
    echo ""
    echo -e "  ${YELLOW}⚠${RESET}  ${BIN_DIR} is not in PATH."
    echo "     Add: export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

echo ""
bar
echo -e "  ${GREEN}${BOLD}✅  ${DISPLAY_NAME} installed.${RESET}"
echo ""
echo "  Launch:        ${APP}"
echo "  App root:      ${APP_ROOT}"
echo "  Config root:   ${CONFIG_ROOT}"
echo "  Uninstall:     ${APP_ROOT}/uninstall-dev.sh"
echo ""
