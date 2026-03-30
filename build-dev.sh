#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  build-dev.sh  —  Build a source-based installable dev bundle
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail
cd "$(dirname "$0")"

APP="git-pusher-dev"
VERSION="2.1.0-dev"
DIST_DIR="dist"
STAGING_DIR="${DIST_DIR}/${APP}"
ARCHIVE="${DIST_DIR}/${APP}-linux-x86_64.tar.gz"

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

copy_payload() {
    local src="$1"
    local dest="${STAGING_DIR}/$(basename "$src")"
    cp -a "$src" "$dest"
}

echo ""
echo -e "${BOLD}  🚀  Git Pusher ${VERSION}  —  Dev Bundle Build${RESET}"
bar
echo ""

if ! command -v tar >/dev/null 2>&1; then
    echo -e "  ${RED}✗${RESET}  tar not found."
    exit 1
fi

for path in assets core ui main.py README.md LICENSE requirements.txt run.sh doctor.sh bootstrap-dev.sh install-dev.sh uninstall-dev.sh; do
    require_file "$path"
done

echo -e "  ${DIM}Preparing dist staging...${RESET}"
rm -rf "$STAGING_DIR" "$ARCHIVE"
mkdir -p "$STAGING_DIR"

for path in assets core ui main.py README.md LICENSE requirements.txt run.sh doctor.sh bootstrap-dev.sh install-dev.sh uninstall-dev.sh; do
    copy_payload "$path"
done

cat > "${STAGING_DIR}/DEV_BUNDLE.txt" <<EOF
Git Pusher Dev Bundle
Version: ${VERSION}

Install:
  ./install-dev.sh

Launch after install:
  git-pusher-dev
EOF

tar -C "$DIST_DIR" -czf "$ARCHIVE" "$APP"

SIZE=$(du -sh "$ARCHIVE" | cut -f1)
echo -e "  ${GREEN}✓${RESET}  Bundle ready: ${ARCHIVE} (${SIZE})"
echo ""
echo -e "  ${BOLD}Next steps:${RESET}"
echo "    Install here:    ./install-dev.sh"
echo "    Extract bundle:  tar -xzf ${ARCHIVE}"
echo "    Install bundle:  cd ${APP} && ./install-dev.sh"
echo ""
