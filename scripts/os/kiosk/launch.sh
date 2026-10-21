#!/usr/bin/env bash
[ -n "${BASH_VERSION:-}" ] || exec /bin/bash "$0" "$@"
SESSION="$(dirname "$(readlink -f "$0")")/session.sh"
LOG="$HOME/.cache/xorg-session.log"
MAX_LOG_BYTES=1048576
QUICK_FAIL_SECONDS=20
MAX_BACKOFF=60
mkdir -p "$(dirname "$LOG")"

stamp() { date -Is; }

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
    rotate
    started=$(date +%s)
    echo "[$(stamp)] startx" >>"$LOG"
    startx /bin/bash "$SESSION" -- :0 vt1 -nolisten tcp -keeptty >>"$LOG" 2>&1
    code=$?
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
