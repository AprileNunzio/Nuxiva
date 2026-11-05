#!/usr/bin/env bash
[ -n "${BASH_VERSION:-}" ] || exec /bin/bash "$0" "$@"
SESSION="$(dirname "$(readlink -f "$0")")/session.sh"
ENV_FILE="${NUXIVA_ENV_FILE:-/etc/nuxiva/nuxiva.env}"
LOG="$HOME/.cache/xorg-session.log"
MAX_LOG_BYTES=1048576
QUICK_FAIL_SECONDS=20
MAX_BACKOFF=60
STANDBY_CHECK_SECONDS=3
mkdir -p "$(dirname "$LOG")"

if [ -z "${XDG_RUNTIME_DIR:-}" ]; then
    local_uid=$(id -u)
    if [ -d "/run/user/$local_uid" ]; then
        export XDG_RUNTIME_DIR="/run/user/$local_uid"
    fi
fi

stamp() { date -Is; }

kiosk_allowed() {
    local val="${NUXIVA_KIOSK:-}"
    if [ -r "$ENV_FILE" ]; then
        local file_val
        file_val=$(sed -n 's/^NUXIVA_KIOSK=//p' "$ENV_FILE" 2>/dev/null | tail -n 1 | tr -d "\"'[:space:]")
        [ -n "$file_val" ] && val="$file_val"
    fi
    case "${val,,}" in
        0|false|no|off) return 1 ;;
        *) return 0 ;;
    esac
}

has_connected_screen() {
    [ "${NUXIVA_KIOSK_FORCE:-0}" = "1" ] && return 0

    local found_connector=0
    local status_file
    for status_file in /sys/class/drm/card*-*/status; do
        [ -f "$status_file" ] || continue
        found_connector=1
        if grep -qi '^connected' "$status_file" 2>/dev/null; then
            return 0
        fi
    done

    if [ "$found_connector" -eq 1 ]; then
        return 1
    fi

    if [ -d /sys/class/graphics/fb0 ] || [ -e /dev/fb0 ]; then
        return 0
    fi

    return 1
}

clean_stale_x_locks() {
    local lock="/tmp/.X0-lock"
    if [ -f "$lock" ]; then
        local pid
        pid=$(head -n 1 "$lock" 2>/dev/null | tr -d '[:space:]')
        if [ -n "$pid" ] && ! kill -0 "$pid" 2>/dev/null && [ ! -d "/proc/$pid" ]; then
            echo "[$(stamp)] Pulizia lock X0 orfano rimasto da un riavvio precedente (PID $pid inattivo)" >>"$LOG"
            rm -f "$lock" "/tmp/.X11-unix/X0" 2>/dev/null || true
        fi
    fi
}

rotate() {
    [ -f "$LOG" ] && [ "$(stat -c %s "$LOG")" -gt "$MAX_LOG_BYTES" ] && mv -f "$LOG" "$LOG.1"
    return 0
}

diagnose() {
    local reason
    reason=$(tail -n 40 "$LOG" 2>/dev/null | grep -E '\(EE\)|Fatal|no screens|Cannot|denied|failed' | tail -n 5)
    printf '\n[%s] Nuxiva: il display grafico non parte (tentativo %s).\n' "$(stamp)" "$1"
    [ -n "$reason" ] && printf '%s\n' "$reason"
    printf 'Log completo: %s\n' "$LOG"
}

fails=0
while true; do
    while ! kiosk_allowed; do
        echo "[$(stamp)] Kiosk disabilitato da configurazione: in attesa di abilitazione..." >>"$LOG"
        sleep 5
    done

    if ! has_connected_screen; then
        echo "[$(stamp)] Nessuno schermo rilevato: kiosk in standby per risparmiare memoria (in attesa di uno schermo)..." >>"$LOG"
        while ! has_connected_screen; do
            if ! kiosk_allowed; then
                break
            fi
            sleep "$STANDBY_CHECK_SECONDS"
        done
        if has_connected_screen && kiosk_allowed; then
            echo "[$(stamp)] Schermo rilevato! Avvio del kiosk grafico Nuxiva..." >>"$LOG"
        else
            continue
        fi
    fi

    rotate
    clean_stale_x_locks
    started=$(date +%s)
    echo "[$(stamp)] startx" >>"$LOG"
    startx /bin/bash "$SESSION" -- :0 vt1 -nolisten tcp -keeptty >>"$LOG" 2>&1
    code=$?
    clean_stale_x_locks

    if ! kiosk_allowed; then
        continue
    fi

    if ! has_connected_screen; then
        echo "[$(stamp)] Schermo disconnesso: passaggio in standby per liberare memoria" >>"$LOG"
        fails=0
        continue
    fi

    elapsed=$(( $(date +%s) - started ))
    echo "[$(stamp)] startx terminato con codice $code dopo ${elapsed}s" >>"$LOG"
    if [ "$elapsed" -lt "$QUICK_FAIL_SECONDS" ]; then
        fails=$((fails + 1))
        diagnose "$fails" | tee -a "$LOG"
    else
        fails=0
    fi
    delay=$(( fails * 5 ))
    [ "$delay" -gt "$MAX_BACKOFF" ] && delay=$MAX_BACKOFF
    [ "$delay" -lt 2 ] && delay=2
    sleep "$delay"
done
    delay=$(( fails * 5 ))
    [ "$delay" -gt "$MAX_BACKOFF" ] && delay=$MAX_BACKOFF
    [ "$delay" -lt 2 ] && delay=2
    sleep "$delay"
done
