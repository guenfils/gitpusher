#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  doctor.sh  —  Check the local Git Pusher dev environment
# ─────────────────────────────────────────────────────────────────────────────
set -e
cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 not found."
    exit 1
fi

python3 -m core.dev_bootstrap "$@"
