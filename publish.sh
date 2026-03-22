#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  publish.sh  —  Full automated publish: git init → build → release
#  Supports GitHub (via gh CLI) and GitLab (via API)
# ─────────────────────────────────────────────────────────────────────────────
set -e
cd "$(dirname "$0")"

VERSION="2.0.0"
APP="git-pusher"

# ── Colors ────────────────────────────────────────────────────────────────────
GREEN="\033[0;32m"; YELLOW="\033[1;33m"; RED="\033[0;31m"
BOLD="\033[1m"; DIM="\033[2m"; CYAN="\033[0;36m"; RESET="\033[0m"

ok()   { echo -e "  ${GREEN}✓${RESET}  $*"; }
warn() { echo -e "  ${YELLOW}⚠${RESET}  $*"; }
err()  { echo -e "  ${RED}✗${RESET}  $*"; }
step() { echo -e "\n  ${BOLD}${CYAN}[$1]${RESET}  $2"; }
bar()  { echo "  ──────────────────────────────────────────"; }
ask()  { echo -e "  ${BOLD}$1${RESET}"; }

echo ""
echo -e "${BOLD}  🚀  Git Pusher v${VERSION}  —  Auto Publish${RESET}"
bar
echo ""

# ─────────────────────────────────────────────────────────────────────────────
#  STEP 0 — Prerequisites
# ─────────────────────────────────────────────────────────────────────────────
step "0/7" "Checking prerequisites"

# Python
if ! command -v python3 &>/dev/null; then
    err "python3 not found. Install Python 3.10+"; exit 1
fi
PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
ok "Python ${PY_VER}"

# git
if ! command -v git &>/dev/null; then
    err "git not found. Install git."; exit 1
fi
ok "git $(git --version | awk '{print $3}')"

# gh CLI (optional but recommended)
HAS_GH=false
if command -v gh &>/dev/null; then
    if gh auth status &>/dev/null 2>&1; then
        HAS_GH=true
        ok "gh CLI $(gh --version | head -1 | awk '{print $3}') (authenticated)"
    else
        warn "gh CLI found but not authenticated — will use git + curl instead"
        echo -e "    ${DIM}Run: gh auth login${RESET}"
    fi
else
    warn "gh CLI not found — will use git + curl instead"
    echo -e "    ${DIM}Install gh CLI for a better experience: https://cli.github.com${RESET}"
fi

# curl
if ! command -v curl &>/dev/null; then
    err "curl not found."; exit 1
fi
ok "curl available"

# ─────────────────────────────────────────────────────────────────────────────
#  STEP 1 — Configuration
# ─────────────────────────────────────────────────────────────────────────────
step "1/7" "Configuration"
echo ""

# Try to load token from config file
CONFIG_FILE="$HOME/.config/git-pusher/config.json"
GH_TOKEN_SAVED=""
GL_TOKEN_SAVED=""
GL_URL_SAVED="https://gitlab.com"
if [ -f "$CONFIG_FILE" ]; then
    GH_TOKEN_SAVED=$(python3 -c "import json; d=json.load(open('$CONFIG_FILE')); print(d.get('github_token',''))" 2>/dev/null || echo "")
    GL_TOKEN_SAVED=$(python3 -c "import json; d=json.load(open('$CONFIG_FILE')); print(d.get('gitlab_token',''))" 2>/dev/null || echo "")
    GL_URL_SAVED=$(python3 -c "import json; d=json.load(open('$CONFIG_FILE')); print(d.get('gitlab_url','https://gitlab.com'))" 2>/dev/null || echo "https://gitlab.com")
fi

# Platform selection
ask "Publish to: [1] GitHub only  [2] GitLab only  [3] Both  (default: 1)"
read -rp "  → " PLATFORM_CHOICE
PLATFORM_CHOICE="${PLATFORM_CHOICE:-1}"

PUBLISH_GITHUB=false
PUBLISH_GITLAB=false
[[ "$PLATFORM_CHOICE" == "1" || "$PLATFORM_CHOICE" == "3" ]] && PUBLISH_GITHUB=true
[[ "$PLATFORM_CHOICE" == "2" || "$PLATFORM_CHOICE" == "3" ]] && PUBLISH_GITLAB=true

# GitHub config
if $PUBLISH_GITHUB; then
    echo ""
    ask "GitHub username: (default: guenfils)"
    read -rp "  → " GH_USER
    GH_USER="${GH_USER:-guenfils}"

    ask "GitHub repo name: (default: git-pusher)"
    read -rp "  → " GH_REPO
    GH_REPO="${GH_REPO:-git-pusher}"

    ask "Repo visibility: [1] public  [2] private  (default: 1)"
    read -rp "  → " VIS_CHOICE
    GH_VISIBILITY="public"
    [ "${VIS_CHOICE:-1}" == "2" ] && GH_VISIBILITY="private"

    if [ -z "$GH_TOKEN_SAVED" ]; then
        ask "GitHub personal access token (needs repo + write:packages scopes):"
        read -rsp "  → " GH_TOKEN; echo ""
    else
        GH_TOKEN="$GH_TOKEN_SAVED"
        ok "GitHub token loaded from config"
    fi
fi

# GitLab config
if $PUBLISH_GITLAB; then
    echo ""
    ask "GitLab URL: (default: ${GL_URL_SAVED})"
    read -rp "  → " GL_URL
    GL_URL="${GL_URL:-$GL_URL_SAVED}"

    ask "GitLab username: (default: guenson)"
    read -rp "  → " GL_USER
    GL_USER="${GL_USER:-guenson}"

    ask "GitLab repo name: (default: git-pusher)"
    read -rp "  → " GL_REPO
    GL_REPO="${GL_REPO:-git-pusher}"

    GL_VISIBILITY_API="public"
    ask "Repo visibility: [1] public  [2] private  (default: 1)"
    read -rp "  → " VIS_GL
    [ "${VIS_GL:-1}" == "2" ] && GL_VISIBILITY_API="private"

    if [ -z "$GL_TOKEN_SAVED" ]; then
        ask "GitLab personal access token (needs api scope):"
        read -rsp "  → " GL_TOKEN; echo ""
    else
        GL_TOKEN="$GL_TOKEN_SAVED"
        ok "GitLab token loaded from config"
    fi
fi

echo ""
ok "Configuration complete"

# ─────────────────────────────────────────────────────────────────────────────
#  STEP 2 — Git init & first commit
# ─────────────────────────────────────────────────────────────────────────────
step "2/7" "Git repository"

if [ ! -d ".git" ]; then
    git init -b main
    ok "git init (branch: main)"
else
    ok "Git repo already initialized"
fi

# Update README with real username
if $PUBLISH_GITHUB && [ -n "$GH_USER" ]; then
    sed -i "s|guenfils|${GH_USER}|g" README.md 2>/dev/null || true
    ok "README.md updated with GitHub username"
fi

# Stage all files
git add .

# Commit (only if there are staged changes)
if git diff --cached --quiet; then
    ok "Nothing new to commit"
else
    git commit -m "feat: initial release v${VERSION} — full repo manager with 25 features

- 6-step push wizard (.gitignore, secret scanner, README generator)
- 20-panel Repo Manager (clone, sync, branches, gitflow, diff, stash...)
- Multi-account GitHub + GitLab support
- Scheduled push and Watch Mode automation
- SSH Key Manager, Webhooks, Issue tracker, Collaborators
- Professional logo and dark theme UI"
    ok "Initial commit created"
fi

# Tag
if git tag | grep -q "^v${VERSION}$"; then
    warn "Tag v${VERSION} already exists"
else
    git tag "v${VERSION}" -m "Release v${VERSION}"
    ok "Tag v${VERSION} created"
fi

# ─────────────────────────────────────────────────────────────────────────────
#  STEP 3 — Create remote repositories
# ─────────────────────────────────────────────────────────────────────────────
step "3/7" "Creating remote repositories"

GH_REPO_URL=""
GL_REPO_URL=""

# GitHub
if $PUBLISH_GITHUB; then
    DESCRIPTION="Free open-source GUI for GitHub & GitLab — push, clone, sync, branches, gitflow and more in one click"

    if $HAS_GH; then
        # Use gh CLI
        if gh repo view "${GH_USER}/${GH_REPO}" &>/dev/null 2>&1; then
            warn "GitHub repo ${GH_USER}/${GH_REPO} already exists"
        else
            gh repo create "${GH_REPO}" \
                --${GH_VISIBILITY} \
                --description "$DESCRIPTION" \
                --homepage "https://github.com/${GH_USER}/${GH_REPO}" \
                --source=. \
                --remote=origin 2>/dev/null || true
        fi
        GH_REPO_URL="https://github.com/${GH_USER}/${GH_REPO}"
    else
        # Use GitHub REST API
        RESP=$(curl -s -X POST \
            -H "Authorization: token ${GH_TOKEN}" \
            -H "Content-Type: application/json" \
            -d "{
                \"name\": \"${GH_REPO}\",
                \"description\": \"${DESCRIPTION}\",
                \"private\": $([ \"$GH_VISIBILITY\" = 'private' ] && echo true || echo false),
                \"auto_init\": false,
                \"has_issues\": true,
                \"has_projects\": false,
                \"has_wiki\": false
            }" \
            "https://api.github.com/user/repos")

        GH_REPO_URL=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('html_url',''))" 2>/dev/null || echo "")

        if [ -z "$GH_REPO_URL" ] || echo "$RESP" | grep -q '"message"'; then
            MSG=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('message','unknown error'))" 2>/dev/null || echo "unknown")
            if echo "$MSG" | grep -q "already exists"; then
                warn "GitHub repo already exists — continuing"
                GH_REPO_URL="https://github.com/${GH_USER}/${GH_REPO}"
            else
                err "GitHub repo creation failed: $MSG"; exit 1
            fi
        fi
    fi
    ok "GitHub: ${GH_REPO_URL}"
fi

# GitLab
if $PUBLISH_GITLAB; then
    DESCRIPTION="Free open-source GUI for GitHub & GitLab — push, clone, sync, branches, gitflow and more in one click"
    GL_API="${GL_URL}/api/v4"

    # Check if repo already exists before attempting creation
    EXISTING_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
        -H "PRIVATE-TOKEN: ${GL_TOKEN}" \
        "${GL_API}/projects/${GL_USER}%2F${GL_REPO}")

    if [ "$EXISTING_CODE" = "200" ]; then
        warn "GitLab repo ${GL_USER}/${GL_REPO} already exists — skipping creation"
        GL_REPO_URL="${GL_URL}/${GL_USER}/${GL_REPO}.git"
    elif [ "$EXISTING_CODE" = "401" ]; then
        err "GitLab authentication failed (HTTP 401) — check your token"; exit 1
    elif [ "$EXISTING_CODE" = "403" ]; then
        err "GitLab permission denied (HTTP 403) — token needs 'api' scope"; exit 1
    else
        # Repo does not exist — create it, capturing HTTP code separately
        GL_RAW=$(curl -s -w "\n%{http_code}" -X POST \
            -H "PRIVATE-TOKEN: ${GL_TOKEN}" \
            -H "Content-Type: application/json" \
            -d "{
                \"name\": \"${GL_REPO}\",
                \"description\": \"${DESCRIPTION}\",
                \"visibility\": \"${GL_VISIBILITY_API}\",
                \"initialize_with_readme\": false
            }" \
            "${GL_API}/projects")

        GL_HTTP_CODE=$(echo "$GL_RAW" | tail -1)
        GL_BODY=$(echo "$GL_RAW" | head -n -1)

        if [ "$GL_HTTP_CODE" = "201" ]; then
            GL_REPO_URL=$(echo "$GL_BODY" | python3 -c "import sys,json; print(json.load(sys.stdin).get('http_url_to_repo',''))" 2>/dev/null || echo "")
            if [ -z "$GL_REPO_URL" ]; then
                err "GitLab repo created but URL not found in response"; exit 1
            fi
        else
            GL_MSG=$(echo "$GL_BODY" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    m = d.get('message', d.get('error', 'unknown error'))
    if isinstance(m, dict):
        parts = []
        for k, v in m.items():
            parts.append('{}: {}'.format(k, v[0] if isinstance(v, list) else v))
        print('; '.join(parts))
    else:
        print(str(m))
except Exception as e:
    print('could not parse response')
" 2>/dev/null || echo "unknown error")

            case "$GL_HTTP_CODE" in
                401) err "GitLab authentication failed (HTTP 401) — check your token"; exit 1 ;;
                403) err "GitLab permission denied (HTTP 403) — token needs 'api' scope"; exit 1 ;;
                404) err "GitLab namespace not found (HTTP 404) — check username"; exit 1 ;;
                422)
                    if echo "$GL_MSG" | grep -qi "already been taken\|already exists"; then
                        warn "GitLab repo already exists — continuing"
                        GL_REPO_URL="${GL_URL}/${GL_USER}/${GL_REPO}.git"
                    else
                        err "GitLab repo creation failed (HTTP 422): ${GL_MSG}"; exit 1
                    fi
                    ;;
                *)  err "GitLab repo creation failed (HTTP ${GL_HTTP_CODE}): ${GL_MSG}"; exit 1 ;;
            esac
        fi
    fi
    ok "GitLab: ${GL_REPO_URL}"
fi

# ─────────────────────────────────────────────────────────────────────────────
#  STEP 4 — Add remotes & push
# ─────────────────────────────────────────────────────────────────────────────
step "4/7" "Pushing code"

push_to_remote() {
    local NAME=$1 URL_HTTPS=$2 TOKEN=$3 PLATFORM=$4

    # Build authenticated URL
    # For GitHub: prefer gh CLI token (works with new repos created by gh CLI)
    if [ "$PLATFORM" = "github" ]; then
        local EFFECTIVE_TOKEN="$TOKEN"
        if $HAS_GH; then
            local CLI_TOKEN
            CLI_TOKEN=$(gh auth token 2>/dev/null || echo "")
            [ -n "$CLI_TOKEN" ] && EFFECTIVE_TOKEN="$CLI_TOKEN"
        fi
        AUTH_URL="https://${GH_USER}:${EFFECTIVE_TOKEN}@${URL_HTTPS#https://}"
    else
        AUTH_URL="https://oauth2:${TOKEN}@${URL_HTTPS#https://}"
    fi

    # Add or update remote
    if git remote get-url "$NAME" &>/dev/null 2>&1; then
        git remote set-url "$NAME" "$AUTH_URL"
    else
        git remote add "$NAME" "$AUTH_URL"
    fi

    git push -u "$NAME" main --tags
    # Remove token from remote URL after push (security)
    git remote set-url "$NAME" "$URL_HTTPS"
}

if $PUBLISH_GITHUB; then
    push_to_remote "origin" "${GH_REPO_URL}" "${GH_TOKEN}" "github"
    ok "Pushed to GitHub"
fi

if $PUBLISH_GITLAB; then
    push_to_remote "gitlab" "${GL_REPO_URL}" "${GL_TOKEN}" "gitlab"
    ok "Pushed to GitLab"
fi

# ─────────────────────────────────────────────────────────────────────────────
#  STEP 5 — Build standalone binary
# ─────────────────────────────────────────────────────────────────────────────
step "5/7" "Building standalone binary"
echo ""

bash build.sh

# ─────────────────────────────────────────────────────────────────────────────
#  STEP 6 — Package release assets
# ─────────────────────────────────────────────────────────────────────────────
step "6/7" "Packaging release assets"

RELEASE_DIR="release/v${VERSION}"
mkdir -p "$RELEASE_DIR"

ARCH=$(uname -m)
BINARY_NAME="${APP}-linux-${ARCH}"
cp "dist/${APP}" "${RELEASE_DIR}/${BINARY_NAME}"
chmod +x "${RELEASE_DIR}/${BINARY_NAME}"

# Source tarball
SOURCE_TAR="${APP}-${VERSION}-source.tar.gz"
tar --exclude='.git' \
    --exclude='build' \
    --exclude='dist' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='release' \
    --exclude='.venv' \
    -czf "${RELEASE_DIR}/${SOURCE_TAR}" \
    -C "$(dirname "$(realpath .)")" \
    "$(basename "$(realpath .)")"

# SHA256 checksums
cd "$RELEASE_DIR"
sha256sum "${BINARY_NAME}" "${SOURCE_TAR}" > SHA256SUMS
cd - > /dev/null

ok "${BINARY_NAME}  ($(du -sh "${RELEASE_DIR}/${BINARY_NAME}" | cut -f1))"
ok "${SOURCE_TAR}"
ok "SHA256SUMS"

# ─────────────────────────────────────────────────────────────────────────────
#  STEP 7 — Publish GitHub release
# ─────────────────────────────────────────────────────────────────────────────
step "7/7" "Publishing release"

RELEASE_NOTES="## Git Pusher v${VERSION}

The first major release — free, open-source GUI for GitHub & GitLab on Linux.

### Highlights
- 🚀 6-step push wizard with .gitignore generator, secret scanner, README generator
- 📁 20-panel Repo Manager: clone, sync, branches, gitflow, diff, stash and more
- 👥 Multi-account support (multiple GitHub + GitLab accounts)
- ⏰ Scheduled push and Watch Mode (auto-commit on file changes)
- 🔑 SSH Key Manager, Webhooks, Issues tracker, Collaborators panel
- 🌿 Gitflow automation — feature/release/hotfix/bugfix workflows

### Installation

**Linux standalone binary (no Python required):**
\`\`\`bash
wget https://github.com/${GH_USER:-guenfils}/${GH_REPO:-git-pusher}/releases/download/v${VERSION}/${BINARY_NAME}
chmod +x ${BINARY_NAME}
./${BINARY_NAME}
\`\`\`

**From source:**
\`\`\`bash
git clone https://github.com/${GH_USER:-guenfils}/${GH_REPO:-git-pusher}.git
cd ${GH_REPO:-git-pusher}
./install.sh
\`\`\`

See [CHANGELOG.md](CHANGELOG.md) for full details."

if $PUBLISH_GITHUB; then
    if $HAS_GH; then
        gh release create "v${VERSION}" \
            "${RELEASE_DIR}/${BINARY_NAME}" \
            "${RELEASE_DIR}/${SOURCE_TAR}" \
            "${RELEASE_DIR}/SHA256SUMS" \
            --title "Git Pusher v${VERSION}" \
            --notes "$RELEASE_NOTES" \
            --latest
        ok "GitHub release published via gh CLI"
    else
        # Create release via API, then upload assets
        RELEASE_RESP=$(curl -s -X POST \
            -H "Authorization: token ${GH_TOKEN}" \
            -H "Content-Type: application/json" \
            -d "{
                \"tag_name\": \"v${VERSION}\",
                \"name\": \"Git Pusher v${VERSION}\",
                \"body\": $(echo "$RELEASE_NOTES" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read()))"),
                \"draft\": false,
                \"prerelease\": false,
                \"make_latest\": \"true\"
            }" \
            "https://api.github.com/repos/${GH_USER}/${GH_REPO}/releases")

        UPLOAD_URL=$(echo "$RELEASE_RESP" | python3 -c "
import sys,json
d=json.load(sys.stdin)
url=d.get('upload_url','')
print(url.replace('{?name,label}',''))
" 2>/dev/null || echo "")

        if [ -n "$UPLOAD_URL" ]; then
            # Upload binary
            curl -s -X POST \
                -H "Authorization: token ${GH_TOKEN}" \
                -H "Content-Type: application/octet-stream" \
                --data-binary @"${RELEASE_DIR}/${BINARY_NAME}" \
                "${UPLOAD_URL}?name=${BINARY_NAME}" > /dev/null
            ok "Binary uploaded"

            # Upload source tarball
            curl -s -X POST \
                -H "Authorization: token ${GH_TOKEN}" \
                -H "Content-Type: application/gzip" \
                --data-binary @"${RELEASE_DIR}/${SOURCE_TAR}" \
                "${UPLOAD_URL}?name=${SOURCE_TAR}" > /dev/null
            ok "Source tarball uploaded"

            # Upload checksums
            curl -s -X POST \
                -H "Authorization: token ${GH_TOKEN}" \
                -H "Content-Type: text/plain" \
                --data-binary @"${RELEASE_DIR}/SHA256SUMS" \
                "${UPLOAD_URL}?name=SHA256SUMS" > /dev/null
            ok "Checksums uploaded"

            RELEASE_URL=$(echo "$RELEASE_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('html_url',''))" 2>/dev/null || echo "")
            ok "GitHub release published: ${RELEASE_URL}"
        else
            MSG=$(echo "$RELEASE_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('message',''))" 2>/dev/null || echo "")
            warn "Could not create release automatically: $MSG"
            warn "Upload files manually from: ${RELEASE_DIR}/"
        fi
    fi
fi

# GitLab release
if $PUBLISH_GITLAB; then
    GL_PROJECT_ID=$(curl -s \
        -H "PRIVATE-TOKEN: ${GL_TOKEN}" \
        "${GL_URL}/api/v4/projects/${GL_USER}%2F${GL_REPO}" \
        | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo "")

    if [ -n "$GL_PROJECT_ID" ]; then
        curl -s -X POST \
            -H "PRIVATE-TOKEN: ${GL_TOKEN}" \
            -H "Content-Type: application/json" \
            -d "{
                \"name\": \"Git Pusher v${VERSION}\",
                \"tag_name\": \"v${VERSION}\",
                \"description\": \"${RELEASE_NOTES}\"
            }" \
            "${GL_URL}/api/v4/projects/${GL_PROJECT_ID}/releases" > /dev/null
        ok "GitLab release created"
    fi
fi

# ─────────────────────────────────────────────────────────────────────────────
#  Done
# ─────────────────────────────────────────────────────────────────────────────
echo ""
bar
echo -e "  ${GREEN}${BOLD}✅  Published successfully!${RESET}"
echo ""

$PUBLISH_GITHUB && echo -e "  GitHub → ${CYAN}https://github.com/${GH_USER}/${GH_REPO}${RESET}"
$PUBLISH_GITLAB && echo -e "  GitLab → ${CYAN}${GL_URL}/${GL_USER}/${GL_REPO}${RESET}"

echo ""
echo -e "  ${DIM}Release assets in: ${RELEASE_DIR}/${RESET}"
echo ""
echo -e "  ${BOLD}Share with the community:${RESET}"
echo "    • Reddit:   r/linux, r/github, r/learnprogramming, r/programming"
echo "    • HackerNews: news.ycombinator.com/submit"
echo "    • Dev.to:   dev.to/new"
echo "    • LinkedIn: share the GitHub link"
echo ""
