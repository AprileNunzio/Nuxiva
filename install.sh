#!/usr/bin/env bash
set -Eeuo pipefail
umask 027

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LANG_DIR="$SCRIPT_DIR/installer_wizard/language"

detect_lang() {
    local l="${NUXIVA_LANG:-${LC_ALL:-${LC_MESSAGES:-${LANG:-en}}}}"
    l="${l,,}"
    l="${l%%.*}"
    l="${l%%_*}"
    [ -n "$l" ] || l="en"
    echo "$l"
}

get_err_msg() {
    local lang target_file base_file
    lang="$(detect_lang)"
    target_file="$LANG_DIR/$lang.json"
    base_file="$LANG_DIR/en.json"

    [ -f "$target_file" ] || target_file="$base_file"

    local msg=""
    if [ -f "$target_file" ]; then
        if command -v python3 >/dev/null 2>&1 && python3 -c "import sys" 2>/dev/null; then
            msg=$(python3 - "$target_file" "$base_file" <<'PY'
import sys, json

target_p, base_p = sys.argv[1], sys.argv[2]
msg = None
for p in (target_p, base_p):
    try:
        with open(p, "r", encoding="utf-8") as f:
            d = json.load(f).get("dictionary", {})
            if "download_err" in d:
                msg = d["download_err"]
                break
    except Exception:
        pass
if msg:
    print(msg)
PY
)
        elif command -v jq >/dev/null 2>&1; then
            msg=$(jq -r '.dictionary.download_err // empty' "$target_file" 2>/dev/null || true)
        fi
    fi

    if [ -z "$msg" ]; then
        msg="Unable to download or execute Nuxiva bootstrap."
    fi
    echo "[ERROR] $msg" >&2
}

BOOTSTRAP_LOCAL="$SCRIPT_DIR/installer_wizard/bootstrap.sh"
BOOTSTRAP_URL="${NUXIVA_BOOTSTRAP_URL:-https://raw.githubusercontent.com/AprileNunzio/NUXIVA/main/installer_wizard/bootstrap.sh}"

if [ -f "$BOOTSTRAP_LOCAL" ]; then
    exec bash "$BOOTSTRAP_LOCAL" "$@"
fi

TMP_SCRIPT="$(mktemp -t nuxiva-bootstrap-XXXXXX.sh)"
cleanup() {
    rm -f "$TMP_SCRIPT"
}
trap cleanup EXIT

if command -v curl >/dev/null 2>&1; then
    curl -fsSL --proto '=https' --tlsv1.2 "$BOOTSTRAP_URL" -o "$TMP_SCRIPT"
elif command -v wget >/dev/null 2>&1; then
    wget --https-only --secure-protocol=TLSv1_2 -qO "$TMP_SCRIPT" "$BOOTSTRAP_URL"
else
    get_err_msg
    exit 1
fi

if [ -s "$TMP_SCRIPT" ]; then
    chmod 700 "$TMP_SCRIPT"
    exec bash "$TMP_SCRIPT" "$@"
else
    get_err_msg
    exit 1
fi
