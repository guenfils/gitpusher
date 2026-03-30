#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  build.sh  —  Build Git Pusher as a standalone Linux executable
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail
cd "$(dirname "$0")"

APP="git-pusher"
VERSION="2.1.0"
VENV_DIR=".venv"
VENV_PY="${VENV_DIR}/bin/python"
VENV_PIP="${VENV_DIR}/bin/pip"

GREEN="\033[0;32m"; YELLOW="\033[1;33m"; RED="\033[0;31m"
BOLD="\033[1m"; DIM="\033[2m"; RESET="\033[0m"

bar() { echo "  ──────────────────────────────────────────"; }

echo ""
echo -e "${BOLD}  🚀  Git Pusher v${VERSION}  —  Build${RESET}"
bar
echo ""

# ── 1. Python 3.10+ ───────────────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    echo -e "${RED}  ✗  python3 not found. Install Python 3.10+${RESET}"; exit 1
fi
PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$(python3 -c "import sys; print(sys.version_info.major)")
PY_MINOR=$(python3 -c "import sys; print(sys.version_info.minor)")
if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]; }; then
    echo -e "${RED}  ✗  Python ${PY_VER} is too old. Need 3.10+${RESET}"; exit 1
fi
echo -e "  ${GREEN}✓${RESET}  Python ${PY_VER}"

# ── 2. Local build environment ───────────────────────────────────────────────
if [ ! -x "$VENV_PY" ]; then
    echo -e "  ${DIM}Creating local build environment in ${VENV_DIR}/...${RESET}"
    python3 -m venv "$VENV_DIR"
fi
echo -e "  ${GREEN}✓${RESET}  Build environment ready"

# ── 3. pip dependencies ───────────────────────────────────────────────────────
echo -e "  ${DIM}Installing dependencies into ${VENV_DIR}/...${RESET}"
"$VENV_PIP" install -q --upgrade pip
"$VENV_PIP" install -q -r requirements.txt
echo -e "  ${GREEN}✓${RESET}  Dependencies installed"

# ── 4. Verify key imports ─────────────────────────────────────────────────────
"$VENV_PY" -c "
import customtkinter, PIL, requests, paramiko, cryptography, darkdetect
" || { echo -e "${RED}  ✗  Missing dependency. Run: pip3 install -r requirements.txt${RESET}"; exit 1; }
echo -e "  ${GREEN}✓${RESET}  All imports verified"

# ── 5. Regenerate icons ───────────────────────────────────────────────────────
echo -e "  Generating icon sizes..."
"$VENV_PY" - << 'PYEOF'
from PIL import Image
img = Image.open("assets/icon.png").convert("RGBA")
for sz in [48, 128]:
    img.resize((sz, sz), Image.LANCZOS).save(f"assets/icon_{sz}.png")
img.resize((256, 256), Image.LANCZOS).save("assets/icon_256.png")
print("  icons: 48 128 256 px")
PYEOF
echo -e "  ${GREEN}✓${RESET}  Icons ready"

# ── 6. Clean ──────────────────────────────────────────────────────────────────
echo -e "  Cleaning previous build..."
rm -rf build/ dist/ __pycache__
find . -name "*.pyc" -delete 2>/dev/null || true
echo -e "  ${GREEN}✓${RESET}  Clean"

# ── 7. Build with PyInstaller ─────────────────────────────────────────────────
echo ""
echo -e "${BOLD}  Building executable...${RESET}"
echo ""

"$VENV_PY" -m PyInstaller git-pusher.spec \
    --noconfirm \
    --clean \
    --log-level WARN

# ── 8. Result ─────────────────────────────────────────────────────────────────
if [ -f "dist/${APP}" ]; then
    SIZE=$(du -sh "dist/${APP}" | cut -f1)
    chmod +x "dist/${APP}"
    echo ""
    bar
    echo -e "  ${GREEN}${BOLD}✅  Build successful!${RESET}"
    echo -e "  📦  dist/${APP}  (${SIZE})"
    echo ""
    echo -e "  ${BOLD}Next steps:${RESET}"
    echo "    Test:            ./dist/${APP}"
    echo "    Install system:  ./install.sh"
    echo "    Dev run:         ./run.sh"
    echo ""
else
    echo ""
    echo -e "  ${RED}${BOLD}✗  Build failed. See output above.${RESET}"
    echo ""
    exit 1
fi
