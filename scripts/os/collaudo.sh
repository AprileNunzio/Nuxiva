#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/i18n.sh"
load_os_language

API="${NUXIVA_COLLAUDO_API:-http://127.0.0.1:8080/api/collaudo}"
APP_DIR="${NUXIVA_DIR:-/opt/Nuxiva}/installer_wizard"
PY="${NUXIVA_PYTHON:-$APP_DIR/venv/bin/python}"
SAVED="${NUXIVA_COLLAUDO_TOKEN_FILE:-$HOME/.config/nuxiva/collaudo-token}"
LANG_CODE="$(detect_os_lang)"
case "$LANG_CODE" in it|en|fr|es) ;; *) LANG_CODE=en ;; esac

token() {
    if [ -n "${NUXIVA_COLLAUDO_TOKEN:-}" ]; then
        printf '%s' "$NUXIVA_COLLAUDO_TOKEN"
    elif [ -r "$SAVED" ]; then
        tr -d '[:space:]' < "$SAVED"
    else
        echo "${L[collaudo_need_token]}" >&2
        exit 4
    fi
}

request() {
    local method="$1" path="$2" body="${3:-}" t code
    t="$(token)"
    local args=(-sS --max-time "${TIMEOUT:-60}" -X "$method" -H "Authorization: Bearer $t" -H "X-Nuxiva-Request: 1" -w '\n%{http_code}')
    [ -n "$body" ] && args+=(-H "Content-Type: application/json" --data "$body")
    local out
    out="$(curl "${args[@]}" "$API/$path")" || { echo "${L[collaudo_unreachable]}" >&2; exit 1; }
    code="${out##*$'\n'}"
    out="${out%$'\n'*}"
    if [ "$code" -ge 400 ]; then
        echo "${L[collaudo_refused]}: HTTP $code $out" >&2
        exit 1
    fi
    printf '%s\n' "$out"
}

need_root() {
    [ "$EUID" -eq 0 ] || exec sudo -- "$0" "$@"
}

issue() {
    PYTHONPATH="$APP_DIR:$APP_DIR/backend" "$PY" -c 'from agenti.collaudo import tokens; print(tokens.issue())'
}

verdict_code() {
    case "$1" in
        pass) return 0 ;;
        warn) return 1 ;;
        fail) return 2 ;;
        *) return 3 ;;
    esac
}

cmd="${1:-help}"
shift || true
case "$cmd" in
    bench)
        BENCH_BIN="${NUXIVA_BENCH_BIN:-${NUXIVA_NATIVE_HOME:-/opt/nuxiva-native}/bin/nuxiva-bench}"
        [ -x "$BENCH_BIN" ] || { echo "${L[collaudo_bench_missing]}" >&2; exit 1; }
        exec "$BENCH_BIN" "$@"
        ;;
    on)
        need_root "$cmd" "$@"
        t="$(issue)"
        if [ "${1:-}" = "--save" ]; then
            install -d -m 0700 "$(dirname "$SAVED")"
            umask 077
            printf '%s\n' "$t" > "$SAVED"
            echo "${L[collaudo_saved]}: $SAVED"
        else
            echo "$t"
            echo "${L[collaudo_token_note]}" >&2
        fi
        ;;
    off)
        need_root "$cmd" "$@"
        rm -f /var/lib/nuxiva/collaudo/token "$SAVED"
        echo "${L[collaudo_disarmed]}"
        ;;
    status)
        request GET status
        ;;
    mode)
        case "${1:-}" in on) v=true ;; off) v=false ;; *) echo "${L[collaudo_usage]}" >&2; exit 2 ;; esac
        request POST mode "{\"enabled\":$v}"
        ;;
    mark)
        request POST mark "{\"label\":\"${1:?}\"}"
        ;;
    events)
        q="limit=${LIMIT:-200}"
        for kv in "$@"; do q+="&$kv"; done
        request GET "events?$q" | jq -c '.events[]'
        ;;
    stream)
        q=""
        for kv in "$@"; do q+="&$kv"; done
        curl -sN -H "Authorization: Bearer $(token)" "$API/stream?${q#&}" | sed -u -n 's/^data: //p'
        ;;
    verify)
        request GET verify
        ;;
    baseline)
        request POST "baseline?minutes=${1:-15}"
        ;;
    report)
        request GET "report?minutes=${1:-15}&lang=$LANG_CODE"
        ;;
    smoke)
        only="$(printf '%s\n' "$@" | jq -R . | jq -sc 'map(select(length>0))')"
        TIMEOUT=420 request POST "smoke?lang=$LANG_CODE" "{\"only\":$only}"
        ;;
    scenario)
        name="${1:?}"
        seconds="${2:-15}"
        TIMEOUT=$((seconds + 30)) request POST scenario "{\"name\":\"$name\",\"seconds\":$seconds}"
        ;;
    diagnose)
        request POST mode '{"enabled":true}' > /dev/null
        request POST mark '{"label":"diagnose_start"}' > /dev/null
        result="$(TIMEOUT=420 request POST "smoke?lang=$LANG_CODE" '{"only":[]}')"
        request POST mode '{"enabled":false}' > /dev/null
        printf '%s\n' "$result" | jq '{verdict: .report.verdict, events: .report.events, checks: [.report.checks[] | {id, status, severity, count, worst}], errors: .report.errors, latency: .report.latency, hints: .hints}'
        v="$(printf '%s\n' "$result" | jq -r '.report.verdict')"
        verdict_code "$v"
        ;;
    *)
        echo "${L[collaudo_usage]}" >&2
        exit 2
        ;;
esac
