#!/usr/bin/env bash

BUILD_PROFILE="${NUXIVA_BUILD_PROFILE:-device}"
BUILD_HEARTBEAT=15

clock() {
    local s=$1
    printf '%dm%02ds' $((s / 60)) $((s % 60))
}

cargo_units() {
    local pkg=$1
    (
        cd "$NATIVE_SRC" || exit 0
        timeout 60 cargo tree --locked -q -p "$pkg" -e normal,build --prefix none --format '{p}' 2>/dev/null \
            | sed 's/ (\*)$//' | sort -u | wc -l
    )
}

cargo_stream() {
    local label=$1 lo=$2 hi=$3 pkg=$4
    shift 4
    local total start log rc
    total=$(cargo_units "$pkg")
    [ "${total:-0}" -gt 0 ] 2>/dev/null || total=0
    local shown=$total
    [ "$total" -gt 0 ] || shown="?"
    start=$SECONDS
    log=$(mktemp)
    progress "$lo" "$label"
    "$@" 2>&1 | {
        local n=0 crate="" line pct span=$((hi - lo)) status
        while :; do
            IFS= read -r -t "$BUILD_HEARTBEAT" line
            status=$?
            if [ "$status" -gt 128 ]; then
                detail "$label · ${crate:-avvio} · $n/$shown · $(clock $((SECONDS - start))) · ottimizzazione e collegamento"
                continue
            fi
            [ "$status" -ne 0 ] && [ -z "$line" ] && break
            printf '%s\n' "$line" >> "$log"
            case "$line" in
                *Compiling\ *)
                    n=$((n + 1))
                    crate=$(printf '%s' "$line" | awk '{for (i = 1; i <= NF; i++) if ($i == "Compiling") { print $(i + 1) " " $(i + 2); exit }}')
                    if [ "$total" -gt 0 ]; then
                        pct=$((lo + span * (n < total ? n : total - 1) / total))
                    else
                        pct=$lo
                    fi
                    progress "$pct" "$label · $n/$shown · $(clock $((SECONDS - start)))"
                    detail "Compiling $crate"
                    ;;
                *error*|*warning:\ unused*|*Finished*) info "$line" ;;
            esac
            [ "$status" -ne 0 ] && break
        done
    }
    rc=${PIPESTATUS[0]}
    if [ "$rc" -ne 0 ]; then
        tail -n 30 "$log" | while IFS= read -r line; do warn "$line"; done
    else
        info "$label: completato in $(clock $((SECONDS - start)))"
    fi
    rm -f "$log"
    return "$rc"
}
