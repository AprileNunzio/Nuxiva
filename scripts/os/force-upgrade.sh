#!/usr/bin/env bash
set -Eeuo pipefail
umask 027

export DEBIAN_FRONTEND=noninteractive
NUXIVA_DIR="${NUXIVA_DIR:-/opt/Nuxiva}"
BRANCH="${1:-main}"
STATE="${NUXIVA_STATE_DIR:-/var/lib/nuxiva}"
HEALTH_URL="${NUXIVA_HEALTH_URL:-http://127.0.0.1:8080/healthz}"
HEALTH_WAIT="${NUXIVA_HEALTH_WAIT:-180}"
UNITS=(nuxiva-supervisor nuxiva-core nuxiva-voice nuxiva-vision nuxiva-ear)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/i18n.sh"
load_os_language

if [ -t 1 ]; then
    C_CYAN=$'\033[0;36m' C_GREEN=$'\033[0;32m' C_YELLOW=$'\033[0;33m' C_RED=$'\033[0;31m' C_RESET=$'\033[0m'
else
    C_CYAN="" C_GREEN="" C_YELLOW="" C_RED="" C_RESET=""
fi

step() { echo -e "\n${C_CYAN}$*${C_RESET}"; }
warn() { echo -e "${C_YELLOW}$*${C_RESET}" >&2; }
fail() {
    echo -e "\n${C_RED}==================================================================${C_RESET}" >&2
    echo -e "${C_RED}   ${L[fail_banner]}${C_RESET}" >&2
    echo -e "${C_RED}   $*${C_RESET}" >&2
    echo -e "${C_RED}==================================================================${C_RESET}" >&2
    exit 1
}
trap 'fail "$(printf "${L[line_err]}" "$LINENO" "$BASH_COMMAND")"' ERR

echo -e "${C_CYAN}=== ${L[banner]} ===${C_RESET}"

if [ "$EUID" -ne 0 ]; then
    echo -e "${C_YELLOW}${L[root_req]}${C_RESET}"
    exec sudo -- "$0" "$@"
fi

[[ "$BRANCH" =~ ^[A-Za-z0-9._/-]{1,100}$ ]] || fail "$(printf "${L[branch_err]}" "$BRANCH")"
[ -d "$NUXIVA_DIR/.git" ] || fail "$(printf "${L[repo_err]}" "$NUXIVA_DIR")"

step "${L[s1]}"
git config --system --get-all safe.directory 2>/dev/null | grep -qxF "$NUXIVA_DIR" \
    || git config --system --add safe.directory "$NUXIVA_DIR"
mkdir -p /var/log/nuxiva "$STATE" /etc/nuxiva
chmod 750 /var/log/nuxiva
chmod 700 "$STATE"
if ! pgrep -x git >/dev/null 2>&1; then
    find "$NUXIVA_DIR/.git" -maxdepth 3 -name '*.lock' -type f -print -delete | sed "s/^/${L[lock_removed]} /"
fi

step "$(printf "${L[s2]}" "$BRANCH")"
cd "$NUXIVA_DIR"
PREVIOUS=$(git rev-parse HEAD 2>/dev/null || true)
export GIT_TERMINAL_PROMPT=0
git fetch --prune --tags origin "+refs/heads/$BRANCH:refs/remotes/origin/$BRANCH" || fail "${L[net_err]}"
git checkout -f -B "$BRANCH" "origin/$BRANCH"
git reset --hard "origin/$BRANCH"
git clean -fd -e .env -e "local_*"
TARGET=$(git rev-parse HEAD)
[ "$TARGET" = "$(git rev-parse "origin/$BRANCH")" ] || fail "$(printf "${L[rev_err]}" "$TARGET")"
printf "${C_GREEN}${L[commit_info]}${C_RESET}\n" "${TARGET:0:7}" "$(git log -1 --pretty=%s)"

step "${L[s3]}"
WIZ_DIR="$NUXIVA_DIR/installer_wizard"
WIZ_VENV="$WIZ_DIR/venv"
WIZ_REQ="$WIZ_DIR/backend/requirements.txt"
if [ ! -x "$WIZ_VENV/bin/python" ] || ! "$WIZ_VENV/bin/python" -c "import sys" >/dev/null 2>&1; then
    rm -rf "$WIZ_VENV"
    python3 -m venv "$WIZ_VENV"
fi
"$WIZ_VENV/bin/pip" install --quiet --disable-pip-version-check --upgrade pip setuptools wheel \
    || fail "${L[deps_err]}"
"$WIZ_VENV/bin/pip" install --quiet --disable-pip-version-check -r "$WIZ_REQ" || fail "${L[deps_err]}"
sha1sum "$WIZ_REQ" | cut -c1-40 > "$WIZ_VENV/.requirements.sha1"

step "${L[s4]}"
SRV_REQ="$NUXIVA_DIR/server/requirements.txt"
if [ -f "$SRV_REQ" ]; then
    SRV_VENV="$NUXIVA_DIR/.venv"
    [ -x "$SRV_VENV/bin/python" ] || { rm -rf "$SRV_VENV"; python3 -m venv "$SRV_VENV"; }
    if command -v uv >/dev/null 2>&1; then
        uv pip install --python "$SRV_VENV/bin/python" -r "$SRV_REQ" --quiet || warn "${L[core_deps_warn]}"
    else
        "$SRV_VENV/bin/pip" install --quiet --disable-pip-version-check -r "$SRV_REQ" || warn "${L[core_deps_warn]}"
    fi
fi

step "${L[s5]}"
if ! (cd "$WIZ_DIR/backend" && PYTHONPATH="$NUXIVA_DIR:$WIZ_DIR:$WIZ_DIR/backend" NUXIVA_DIR="$NUXIVA_DIR" \
        timeout 120 "$WIZ_VENV/bin/python" -c "import nuxiva_supervisor" >/tmp/nuxiva-import-check.log 2>&1); then
    tail -n 30 /tmp/nuxiva-import-check.log >&2
    if [ -n "$PREVIOUS" ]; then
        git -C "$NUXIVA_DIR" reset --hard "$PREVIOUS" >/dev/null
        printf "${C_YELLOW}${L[restored]}${C_RESET}\n" "${PREVIOUS:0:7}" >&2
    fi
    fail "${L[import_err]}"
fi
rm -f /tmp/nuxiva-import-check.log
echo -e "${C_GREEN}${L[import_ok]}${C_RESET}"

step "${L[s6]}"
rm -f "$STATE/update_pending.json" "$STATE/supervisor_failures" /run/nuxiva-repair.lock /run/nuxiva-upgrade.lock
if [ -f "$STATE/bad_revs" ]; then
    grep -v -e "^${TARGET}" -e "^${TARGET:0:7}" "$STATE/bad_revs" > "$STATE/bad_revs.tmp" || true
    mv -f "$STATE/bad_revs.tmp" "$STATE/bad_revs"
fi
SYSTEMD_SRC="$NUXIVA_DIR/scripts/os/systemd"
if [ -d "$SYSTEMD_SRC" ]; then
    install -m 0644 "$SYSTEMD_SRC"/*.service /etc/systemd/system/
    systemctl daemon-reload
fi
echo -e "${C_GREEN}${L[state_reset]}${C_RESET}"

step "${L[s7]}"
for unit in "${UNITS[@]}"; do
    if systemctl cat "$unit.service" >/dev/null 2>&1; then
        systemctl reset-failed "$unit.service" >/dev/null 2>&1 || true
        systemctl restart "$unit.service" || warn "$(printf "${L[restart_warn]}" "$unit")"
    fi
done

step "${L[s8]}"
deadline=$(( $(date +%s) + HEALTH_WAIT ))
healthy=0
while [ "$(date +%s)" -lt "$deadline" ]; do
    if systemctl is-active --quiet nuxiva-supervisor.service \
            && curl -fsS --max-time 5 "$HEALTH_URL" >/dev/null 2>&1; then
        healthy=1
        break
    fi
    sleep 3
done
RUNNING=$(git rev-parse HEAD)
if [ "$healthy" != 1 ] || [ "$RUNNING" != "$TARGET" ]; then
    journalctl -u nuxiva-supervisor.service -n 60 --no-pager >&2 || true
    fail "$(printf "${L[verify_fail]}" "$HEALTH_WAIT")"
fi
echo "$TARGET" > "$STATE/last_good_rev"

echo -e "\n${C_GREEN}==================================================================${C_RESET}"
echo -e "${C_GREEN}   ${L[done_banner]}${C_RESET}"
printf "${C_GREEN}   ${L[version_active]}${C_RESET}\n" "${TARGET:0:7}"
echo -e "${C_CYAN}   ${L[check_hint]}${C_RESET}"
echo -e "${C_GREEN}==================================================================${C_RESET}"
