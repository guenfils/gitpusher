#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  run.sh  —  Development launcher for Git Pusher
# ─────────────────────────────────────────────────────────────────────────────
set -e
cd "$(dirname "$0")"

GREEN="\033[0;32m"; YELLOW="\033[1;33m"; RED="\033[0;31m"
BOLD="\033[1m"; DIM="\033[2m"; RESET="\033[0m"

echo ""
echo -e "${BOLD}  🚀  Git Pusher  —  Dev Run${RESET}"
echo ""

# ── Python check ──────────────────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    echo -e "${RED}  ✗  python3 not found.${RESET}"; exit 1
fi
PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo -e "  ${GREEN}✓${RESET}  Python ${PY_VER}"

# ── Dependency check (fast, no install) ───────────────────────────────────────
MISSING=()
for pkg in customtkinter PIL requests paramiko cryptography darkdetect; do
    python3 -c "import $pkg" 2>/dev/null || MISSING+=("$pkg")
done

if [ ${#MISSING[@]} -gt 0 ]; then
    echo -e "  ${YELLOW}⚠  Missing packages: ${MISSING[*]}${RESET}"
    echo -e "  ${DIM}Installing...${RESET}"
    pip3 install -q -r requirements.txt
    echo -e "  ${GREEN}✓${RESET}  Dependencies installed"
else
    echo -e "  ${GREEN}✓${RESET}  Dependencies OK"
fi

# ── Launch ────────────────────────────────────────────────────────────────────
echo -e "  ${DIM}Starting...${RESET}"
echo ""
exec python3 main.py "$@"
