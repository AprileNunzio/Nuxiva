#!/usr/bin/env bash
set -uo pipefail

NUXIVA_DIR="${NUXIVA_DIR:-/opt/Nuxiva}"
STATE=/var/lib/nuxiva
FAILURES="$STATE/supervisor_failures"
LOG=/var/log/nuxiva/rollback.log
WINDOW=600
THRESHOLD=4
mkdir -p "$STATE" /var/log/nuxiva
exec >>"$LOG" 2>&1

now=$(date +%s)
echo "$now" >> "$FAILURES"
recent=$(awk -v n="$now" -v w="$WINDOW" 'n - $1 < w' "$FAILURES" | wc -l)
awk -v n="$now" -v w="$WINDOW" 'n - $1 < w' "$FAILURES" > "$FAILURES.tmp" && mv "$FAILURES.tmp" "$FAILURES"
echo "[$(date -Is)] Fallimento del Supervisor ($recent negli ultimi $((WINDOW / 60)) minuti)"
if [ "$recent" -ge "$THRESHOLD" ]; then
    good=$(cat "$STATE/last_good_rev" 2>/dev/null || true)
    current=$(git -c safe.directory='*' -C "$NUXIVA_DIR" rev-parse HEAD 2>/dev/null || true)
    if [ -n "$good" ] && [ "$good" != "$current" ]; then
        echo "Crash-loop: rollback da $current a $good"
        echo "$current" >> "$STATE/bad_revs"
        git -c safe.directory='*' -C "$NUXIVA_DIR" reset --hard "$good"
        rm -f "$STATE/update_pending.json"
    else
        echo "Crash-loop senza versione precedente utilizzabile (current=$current good=$good)"
    fi
    : > "$FAILURES"
fi
if [ -x /bin/bash ] && [ -f "$NUXIVA_DIR/scripts/os/repair.sh" ]; then
    /bin/bash "$NUXIVA_DIR/scripts/os/repair.sh" --quiet --origin=rollback || echo "Riparazione automatica incompleta: vedi /var/log/nuxiva/repair.log"
else
    systemctl reset-failed nuxiva-supervisor.service
    systemctl start --no-block nuxiva-supervisor.service
fi
