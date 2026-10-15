#!/usr/bin/env bash
set -Eeuo pipefail
umask 027

export DEBIAN_FRONTEND=noninteractive
NUXIVA_DIR="${NUXIVA_DIR:-/opt/Nuxiva}"
BRANCH="${1:-main}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/i18n.sh"
load_os_language

if [ -t 1 ]; then
    C_CYAN=$'\033[0;36m' C_GREEN=$'\033[0;32m' C_YELLOW=$'\033[0;33m' C_RED=$'\033[0;31m' C_RESET=$'\033[0m'
else
    C_CYAN="" C_GREEN="" C_YELLOW="" C_RED="" C_RESET=""
fi

if [ -t 1 ]; then
    echo -e "${C_CYAN}==================================================================${C_RESET}"
    echo -e "${C_CYAN}      ${L[banner]}       ${C_RESET}"
    echo -e "${C_CYAN}==================================================================${C_RESET}"
else
    echo "=== ${L[banner]} ==="
fi

if [ "$EUID" -ne 0 ]; then
    echo -e "${C_YELLOW}${L[root_req]}${C_RESET}"
    exec sudo -- "$0" "$@"
fi

if [ ! -d "$NUXIVA_DIR/.git" ]; then
    printf "${C_RED}${L[repo_err]}${C_RESET}\n" "$NUXIVA_DIR" >&2
    exit 1
fi

echo -e "\n${C_CYAN}${L[s1]}${C_RESET}"
git config --system --add safe.directory "$NUXIVA_DIR" || true
mkdir -p /var/log/nuxiva /var/lib/nuxiva /etc/nuxiva
chmod 750 /var/log/nuxiva
chmod 700 /var/lib/nuxiva

echo -e "\n${C_CYAN}$(printf "${L[s2]}" "$BRANCH")${C_RESET}"
cd "$NUXIVA_DIR"

export GIT_TERMINAL_PROMPT=0
if ! git fetch --prune --tags origin; then
    echo -e "${C_RED}${L[net_err]}${C_RESET}" >&2
    exit 1
fi

git reset --hard HEAD 2>/dev/null || true
git checkout -f -B "$BRANCH" "origin/$BRANCH"
git reset --hard "origin/$BRANCH"
git clean -fd -e .env -e "local_*"

COMMIT_HASH=$(git rev-parse --short HEAD)
COMMIT_MSG=$(git log -1 --pretty=%B | head -n 1)
printf "${C_GREEN}${L[commit_info]}${C_RESET}\n" "$COMMIT_HASH" "$COMMIT_MSG"

echo -e "\n${C_CYAN}${L[s3]}${C_RESET}"
WIZ_DIR="$NUXIVA_DIR/installer_wizard"
WIZ_VENV="$WIZ_DIR/venv"
WIZ_REQ="$WIZ_DIR/backend/requirements.txt"

if [ -f "$WIZ_REQ" ]; then
    if [ ! -x "$WIZ_VENV/bin/python" ]; then
        rm -rf "$WIZ_VENV"
        python3 -m venv "$WIZ_VENV"
    fi
    if ! "$WIZ_VENV/bin/pip" install --quiet --upgrade pip setuptools wheel; then
        rm -rf "$WIZ_VENV"
        python3 -m venv "$WIZ_VENV"
        "$WIZ_VENV/bin/pip" install --quiet --upgrade pip setuptools wheel
    fi
    "$WIZ_VENV/bin/pip" install --quiet -r "$WIZ_REQ"
fi

echo -e "\n${C_CYAN}${L[s4]}${C_RESET}"
SRV_REQ="$NUXIVA_DIR/server/requirements.txt"
if [ -f "$SRV_REQ" ]; then
    SRV_VENV="$NUXIVA_DIR/.venv"
    if [ ! -x "$SRV_VENV/bin/python" ]; then
        rm -rf "$SRV_VENV"
        python3 -m venv "$SRV_VENV"
    fi
    if command -v uv >/dev/null 2>&1; then
        uv pip install --python "$SRV_VENV/bin/python" -r "$SRV_REQ" --quiet || true
    else
        "$SRV_VENV/bin/pip" install --quiet -r "$SRV_REQ" || true
    fi
fi

echo -e "\n${C_CYAN}${L[s5]}${C_RESET}"
SYSTEMD_SRC="$NUXIVA_DIR/scripts/os/systemd"
if [ -d "$SYSTEMD_SRC" ]; then
    cp -f "$SYSTEMD_SRC"/*.service /etc/systemd/system/ 2>/dev/null || true
    systemctl daemon-reload
fi

rm -f /run/nuxiva-repair.lock /run/nuxiva-upgrade.lock

echo -e "\n${C_CYAN}${L[s6]}${C_RESET}"
for unit in nuxiva-supervisor nuxiva-core nuxiva-voice nuxiva-vision nuxiva-ear; do
    if systemctl list-unit-files "$unit.service" &>/dev/null; then
        systemctl restart "$unit.service" || true
    fi
done

echo -e "\n${C_GREEN}==================================================================${C_RESET}"
echo -e "${C_GREEN}   ${L[done_banner]}   ${C_RESET}"
printf "${C_GREEN}   ${L[version_active]}${C_RESET}\n" "$COMMIT_HASH"
echo -e "${C_CYAN}   ${L[check_hint]}${C_RESET}"
echo -e "${C_GREEN}==================================================================${C_RESET}"
