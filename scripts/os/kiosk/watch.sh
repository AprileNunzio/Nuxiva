#!/usr/bin/env bash
set -Eeuo pipefail

ENV_FILE="${NUXIVA_ENV_FILE:-/etc/nuxiva/nuxiva.env}"
GETTY_OVERRIDE="${NUXIVA_GETTY_OVERRIDE:-/etc/systemd/system/getty@tty1.service.d/override.conf}"
DRM_GLOB="${NUXIVA_DRM_GLOB:-/sys/class/drm/card*-*/status}"
POLL="${NUXIVA_SCREEN_POLL:-3}"
GRACE="${NUXIVA_SCREEN_GRACE:-20}"
KIOSK_PROC_PATTERN='kiosk/launch\.sh|kiosk/session\.sh|startx|xinit|Xorg|chromium'

[[ "$POLL" =~ ^[1-9][0-9]?$ && "$GRACE" =~ ^[0-9]{1,3}$ ]] || { echo "Parametri di controllo schermo non validi" >&2; exit 64; }

env_value() {
    [ -r "$ENV_FILE" ] || return 0
    sed -n "s/^$1=//p" "$ENV_FILE" | tail -n 1 | tr -d "\"'[:space:]"
}

kiosk_user() {
    local u
    u=$(env_value NUXIVA_KIOSK_USER)
    [[ "$u" =~ ^[a-z_][a-z0-9_-]{0,31}$ ]] || u=nuxiva-kiosk
    printf '%s\n' "$u"
}

kiosk_enabled() {
    case "$(env_value NUXIVA_KIOSK)" in
        0|false|no|off|FALSE|NO|OFF) return 1 ;;
        *) [ -f "$GETTY_OVERRIDE" ] ;;
    esac
}

screen_connected() {
    local f found=0
    for f in $DRM_GLOB; do
        [ -r "$f" ] || continue
        found=1
        grep -qi '^connected' "$f" && return 0
    done
    (( found )) && return 1
    [ -e /dev/fb0 ]
}

kiosk_running() {
    pgrep -u "$1" -f "$KIOSK_PROC_PATTERN" >/dev/null 2>&1
}

tty1_in_use() {
    local user comm
    while read -r user comm; do
        [ -n "$user" ] || continue
        [ "$user" = "$1" ] && continue
        case "$comm" in agetty|login) continue ;; esac
        return 0
    done < <(ps -t tty1 -o user=,comm= 2>/dev/null || true)
    return 1
}

say() { printf '%s\n' "$*"; }

last=""
busy=0
while true; do
    user=$(kiosk_user)
    state=off
    if kiosk_enabled && id "$user" >/dev/null 2>&1; then
        if screen_connected; then state=connected; else state=standby; fi
    fi
    if [ "$state" != "$last" ]; then
        case "$state" in
            connected) say "Schermo collegato: kiosk Nuxiva attivo / Screen connected: Nuxiva kiosk active" ;;
            standby) say "Nessuno schermo: kiosk in standby / No screen: kiosk on standby" ;;
            off) say "Kiosk disattivato da configurazione / Kiosk disabled by configuration" ;;
        esac
        last=$state
    fi
    if [ "$state" = connected ] && ! kiosk_running "$user"; then
        if tty1_in_use "$user"; then
            (( busy )) || say "tty1 occupata da un'altra sessione: il kiosk partirà quando si libera / tty1 busy: kiosk will start once it is free"
            busy=1
        else
            busy=0
            say "Avvio della sessione kiosk su tty1 / Starting kiosk session on tty1"
            systemctl restart getty@tty1.service || say "Riavvio di getty@tty1 non riuscito / getty@tty1 restart failed"
            sleep "$GRACE"
        fi
    fi
    sleep "$POLL"
done
