#!/usr/bin/env bash

declare -g -A L=()

detect_os_lang() {
    local l=""
    if [ -r /etc/nuxiva/nuxiva.env ]; then
        l=$(sed -n 's/^NUXIVA_UI_LANG=//p' /etc/nuxiva/nuxiva.env | tail -n 1)
    fi
    if [ -z "$l" ]; then
        l="${UI_LANG:-${LC_ALL:-${LC_MESSAGES:-${LANG:-en}}}}"
    fi
    l="${l,,}"
    l="${l%%.*}"
    l="${l%%_*}"
    case "$l" in
        it) echo "it" ;;
        fr) echo "fr" ;;
        es) echo "es" ;;
        "") echo "en" ;;
        *) echo "$l" ;;
    esac
}

load_os_language() {
    local target_lang="${1:-$(detect_os_lang)}"
    local script_base
    script_base="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local lang_dir="${2:-$script_base/language}"
    local base_file="$lang_dir/en.json"
    local target_file="$lang_dir/$target_lang.json"

    [ -f "$target_file" ] || target_file="$base_file"

    local py_bin=""
    if command -v python3 >/dev/null 2>&1 && python3 -c "import sys" 2>/dev/null; then
        py_bin="python3"
    elif command -v python >/dev/null 2>&1 && python -c "import sys" 2>/dev/null; then
        py_bin="python"
    fi

    if [ -n "$py_bin" ]; then
        local pairs
        pairs=$("$py_bin" - "$base_file" "$target_file" <<'PY'
import sys, json

try:
    sys.stdout.reconfigure(newline='\n')
except Exception:
    pass

base_path, target_path = sys.argv[1], sys.argv[2]
merged = {}
for p in (base_path, target_path):
    try:
        with open(p, "r", encoding="utf-8") as f:
            d = json.load(f).get("dictionary", {})
            merged.update(d)
    except Exception:
        pass

for k, v in merged.items():
    if isinstance(v, str):
        v_clean = v.replace('\r', '').replace('\n', ' ')
        print(f"{k}\t{v_clean}")
PY
)
        while IFS=$'\t' read -r k v; do
            v="${v%$'\r'}"
            [ -n "$k" ] && L["$k"]="$v"
        done <<< "$pairs"
    elif command -v jq >/dev/null 2>&1; then
        while IFS="=" read -r k v; do
            v="${v%$'\r'}"
            [ -n "$k" ] && L["$k"]="$v"
        done < <(jq -r '.dictionary // {} | to_entries[] | "\(.key)=\(.value)"' "$target_file" 2>/dev/null)
    fi
}

i18n_t() {
    local key="$1"
    local default_val="${2:-$1}"
    if [ -n "${L[$key]:-}" ]; then
        echo "${L[$key]}"
    else
        echo "$default_val"
    fi
}
