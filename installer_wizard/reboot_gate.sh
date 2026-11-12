#!/usr/bin/env bash

REBOOT_GATE_LOCKS=${REBOOT_GATE_LOCKS:-"/var/lib/dpkg/lock-frontend /var/lib/dpkg/lock /var/lib/apt/lists/lock /var/cache/apt/archives/lock"}
REBOOT_GATE_PROCS=${REBOOT_GATE_PROCS:-"apt-get apt aptitude dpkg unattended-upgr"}
REBOOT_GATE_POLL=${REBOOT_GATE_POLL:-3}
REBOOT_GATE_TRIES=${REBOOT_GATE_TRIES:-3}

reboot_gate_package_job() {
    local p lock
    for p in $REBOOT_GATE_PROCS; do
        if pgrep -x "$p" >/dev/null 2>&1; then
            printf '%s\n' "$p"
            return 0
        fi
    done
    if command -v fuser >/dev/null 2>&1; then
        for lock in $REBOOT_GATE_LOCKS; do
            if [ -e "$lock" ] && fuser "$lock" >/dev/null 2>&1; then
                printf '%s\n' "${lock##*/}"
                return 0
            fi
        done
    fi
    return 1
}

reboot_gate_inhibitor() {
    command -v busctl >/dev/null 2>&1 || return 1
    command -v jq >/dev/null 2>&1 || return 1
    local who
    who=$(busctl --json=short call org.freedesktop.login1 /org/freedesktop/login1 \
        org.freedesktop.login1.Manager ListInhibitors 2>/dev/null \
        | jq -r '[.data[0][]? | select(.[3] == "block" and ((.[0] | split(":")) | index("shutdown")))] | first | if . then "\(.[1]) (PID \(.[5]))" else empty end' 2>/dev/null) || return 1
    [ -n "$who" ] || return 1
    printf '%s\n' "$who"
}

reboot_gate_blocker() {
    reboot_gate_package_job || reboot_gate_inhibitor
}

reboot_gate_wait() {
    local limit=$1 on_wait=${2:-} t0=$EPOCHSECONDS who
    while who=$(reboot_gate_blocker); do
        (( EPOCHSECONDS - t0 >= limit )) && { printf '%s\n' "$who"; return 1; }
        [ -n "$on_wait" ] && "$on_wait" "$who" $(( EPOCHSECONDS - t0 ))
        sleep "$REBOOT_GATE_POLL"
    done
    return 0
}

reboot_gate_issue() {
    systemctl reboot -i 2>>"${REBOOT_GATE_LOG:-/dev/null}"
}

reboot_gate_run() {
    local limit=${1:-2700} on_wait=${2:-} try
    [[ "$limit" =~ ^[0-9]+$ ]] || return 64
    for (( try = 1; try <= REBOOT_GATE_TRIES; try++ )); do
        reboot_gate_wait "$limit" "$on_wait" >/dev/null || return 75
        reboot_gate_issue && return 0
        sleep $(( try * 5 ))
    done
    return 70
}

reboot_gate_defer() {
    local limit=${1:-21600} self
    self=$(readlink -f "${BASH_SOURCE[0]}") || return 1
    [ -f "$self" ] || return 1
    systemctl stop nuxiva-first-reboot.service >/dev/null 2>&1 || true
    systemd-run --quiet --collect --unit=nuxiva-first-reboot \
        --description="Nuxiva first reboot after package jobs" \
        /bin/bash "$self" run "$limit"
}

if [[ "${BASH_SOURCE[0]:-}" == "${0:-}" ]]; then
    set -Eeuo pipefail
    case "${1:-}" in
        run) reboot_gate_run "${2:-21600}" ;;
        check) if who=$(reboot_gate_blocker); then printf '%s\n' "$who"; exit 1; fi ;;
        *) exit 64 ;;
    esac
fi
