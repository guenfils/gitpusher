#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  bootstrap-dev.sh  —  Prepare the local dev environment for Git Pusher
# ─────────────────────────────────────────────────────────────────────────────
set -e
cd "$(dirname "$0")"

GREEN="\033[0;32m"; YELLOW="\033[1;33m"; RED="\033[0;31m"
BOLD="\033[1m"; DIM="\033[2m"; RESET="\033[0m"

echo ""
echo -e "${BOLD}  🧰  Git Pusher  —  Dev Bootstrap${RESET}"
echo ""

if ! command -v python3 >/dev/null 2>&1; then
    echo -e "${RED}  ✗  python3 not found.${RESET}"
    exit 1
fi

echo -e "  ${DIM}Preparing local .venv and config directories...${RESET}"
python3 -m core.dev_bootstrap --bootstrap --install-missing "$@"
echo ""
echo -e "  ${GREEN}✓${RESET}  Dev bootstrap ready"
echo -e "  ${DIM}Next: ./run.sh${RESET}"
echo ""
