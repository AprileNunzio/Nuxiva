#!/usr/bin/env bash

FIRST_BOOT_DRM_GLOB=${FIRST_BOOT_DRM_GLOB:-/sys/class/drm/card*-*/status}
FIRST_BOOT_FB=${FIRST_BOOT_FB:-/dev/fb0}
FIRST_BOOT_ENV=${FIRST_BOOT_ENV:-/etc/nuxiva/nuxiva.env}
FIRST_BOOT_SETUP=${FIRST_BOOT_SETUP:-/var/lib/nuxiva/setup.json}
FIRST_BOOT_GETTY=${FIRST_BOOT_GETTY:-/etc/systemd/system/getty@tty1.service.d/override.conf}
FIRST_BOOT_TTY=${FIRST_BOOT_TTY:-/dev/tty}

first_boot_flag() {
    case "${1,,}" in
        1|true|yes|on) printf '1\n' ;;
        0|false|no|off) printf '0\n' ;;
        *) return 1 ;;
    esac
}

first_boot_screen() {
    local f found=0
    for f in $FIRST_BOOT_DRM_GLOB; do
        [ -r "$f" ] || continue
        found=1
        grep -qi '^connected' "$f" && return 0
    done
    (( found )) && return 1
    [ -e "$FIRST_BOOT_FB" ]
}

first_boot_setup_done() {
    [ -r "$FIRST_BOOT_SETUP" ] && jq -e '.done == true' "$FIRST_BOOT_SETUP" >/dev/null 2>&1
}

first_boot_env_value() {
    [ -r "$FIRST_BOOT_ENV" ] || return 1
    sed -n "s/^$1=//p" "$FIRST_BOOT_ENV" | tail -n 1 | tr -d "\"'[:space:]"
}

first_boot_kiosk_choice() {
    local v
    if [ -n "${NUXIVA_KIOSK:-}" ] && v=$(first_boot_flag "$NUXIVA_KIOSK"); then
        printf '%s\n' "$v"
        return 0
    fi
    if first_boot_setup_done && v=$(first_boot_env_value NUXIVA_KIOSK) && v=$(first_boot_flag "$v"); then
        printf '%s\n' "$v"
        return 0
    fi
    printf '1\n'
}

first_boot_set_env() {
    local key=$1 value=$2 tool=$3
    [[ "$key" =~ ^NUXIVA_[A-Z0-9_]+$ && "$value" =~ ^[A-Za-z0-9_.:/-]*$ ]] || return 64
    [ -f "$tool" ] || return 66
    python3 "$tool" set "$FIRST_BOOT_ENV" "$key" "$value"
}

first_boot_interactive() {
    [ -t 1 ] && ( : <"$FIRST_BOOT_TTY" ) 2>/dev/null
}

first_boot_countdown() {
    local secs=$1 fmt=$2 left key
    [[ "$secs" =~ ^[0-9]+$ ]] || return 64
    if ! first_boot_interactive; then
        printf -- "$fmt\n" "$secs" >&2
        sleep "$secs"
        return 0
    fi
    for (( left = secs; left > 0; left-- )); do
        printf -- "\r\033[K   $fmt" "$left" >&2
        if IFS= read -rsn1 -t 1 key <"$FIRST_BOOT_TTY"; then
            printf '\r\033[K' >&2
            return 1
        fi
    done
    printf '\r\033[K' >&2
    return 0
}

first_boot_verify() {
    local kiosk=$1 unit=nuxiva-supervisor.service
    systemctl is-enabled -q "$unit" 2>/dev/null || { printf '%s (enabled)\n' "$unit"; return 1; }
    systemctl is-active -q "$unit" 2>/dev/null || { printf '%s (active)\n' "$unit"; return 1; }
    [ "$kiosk" = 1 ] || return 0
    [ -f "$FIRST_BOOT_GETTY" ] || { printf '%s\n' "$FIRST_BOOT_GETTY"; return 1; }
    command -v chromium >/dev/null 2>&1 || { printf 'chromium\n'; return 1; }
    command -v startx >/dev/null 2>&1 || { printf 'xinit\n'; return 1; }
}

reboot_progress() {
    local shown
    fmt_dur shown "$2"
    if [ "$TTY" = 1 ]; then
        printf '\r\033[K   %s%s %s %s %s %s%s' "$C_AMBER" "$G_RUN" "${T[reboot_wait]}" "$G_DOT" "$1" "$shown" "$C_OFF" >&2
    elif (( REBOOT_NOTED == 0 )); then
        printf '   %s %s %s\n' "${T[reboot_wait]}" "$G_DOT" "$1" >&2
        REBOOT_NOTED=1
    fi
}

restart_when_idle() {
    local gate="$WIZ/reboot_gate.sh" who
    REBOOT_NOTED=0
    if ! who=$(first_boot_verify "$KIOSK"); then
        printf -v who "${T[verify_fail]}" "$who"
        echo -e "   ${C_RED}${G_BAD}${C_OFF} $who"
        return 1
    fi
    if [ "${NUXIVA_NO_REBOOT:-0}" = "1" ] || [ "$KIOSK" != 1 ]; then
        return 0
    fi
    if ! first_boot_screen; then
        echo -e "   ${C_AMBER}!${C_OFF} ${T[no_screen]}"
        return 0
    fi
    if [ ! -r "$gate" ]; then
        echo -e "   ${C_RED}${G_BAD}${C_OFF} ${T[reboot_manual]}"
        return 1
    fi
    if ! first_boot_countdown "${NUXIVA_REBOOT_DELAY:-10}" "${T[reboot_count]}"; then
        echo -e "   ${C_AMBER}!${C_OFF} ${T[reboot_cancel]}"
        return 0
    fi
    source "$gate"
    if ! who=$(reboot_gate_wait "${NUXIVA_REBOOT_WAIT:-180}" reboot_progress); then
        [ "$TTY" = 1 ] && printf '\r\033[K' >&2
        if reboot_gate_defer 21600 >>"$LOG" 2>&1; then
            printf -v who "${T[reboot_deferred]}" "$who"
            echo -e "   ${C_AMBER}!${C_OFF} $who"
            return 0
        fi
        echo -e "   ${C_RED}${G_BAD}${C_OFF} ${T[reboot_manual]}"
        return 1
    fi
    [ "$TTY" = 1 ] && printf '\r\033[K' >&2
    echo -e "   ${C_CYAN}>>> ${T[reboot_now]}${C_OFF}"
    echo
    REBOOT_GATE_LOG=$LOG reboot_gate_run 600 reboot_progress >>"$LOG" && return 0
    [ "$TTY" = 1 ] && printf '\r\033[K' >&2
    if who=$(reboot_gate_blocker) && reboot_gate_defer 21600 >>"$LOG" 2>&1; then
        printf -v who "${T[reboot_deferred]}" "$who"
        echo -e "   ${C_AMBER}!${C_OFF} $who"
        return 0
    fi
    echo -e "   ${C_RED}${G_BAD}${C_OFF} ${T[reboot_manual]}"
    return 1
}
