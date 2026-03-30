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

# ── Bootstrap dev environment ────────────────────────────────────────────────
echo -e "  ${DIM}Running dev bootstrap...${RESET}"
if ! python3 -m core.dev_bootstrap --bootstrap --install-missing; then
    echo ""
    echo -e "${RED}  ✗  Dev bootstrap failed.${RESET}"
    echo -e "  ${DIM}Run ./doctor.sh for a detailed report.${RESET}"
    exit 1
fi
echo -e "  ${GREEN}✓${RESET}  Dev environment ready"

# ── Launch ────────────────────────────────────────────────────────────────────
echo -e "  ${DIM}Starting...${RESET}"
echo ""
if [ -x ".venv/bin/python" ]; then
    exec .venv/bin/python main.py "$@"
fi
exec python3 main.py "$@"
