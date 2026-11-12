#!/usr/bin/env bash
set -Eeuo pipefail
umask 022

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/i18n.sh"
load_os_language

SRC_DIR="${1:-$SCRIPT_DIR/systemd}"
DST_DIR="${2:-/etc/systemd/system}"
SELF=nuxiva-supervisor.service
REQUIRED=(nuxiva-supervisor.service nuxiva-rollback.service)
NAME_RE='^nuxiva-[a-z0-9]+(-[a-z0-9]+)*\.service$'

say() {
    local key=$1 fallback=$2
    shift 2
    local fmt
    fmt=$(i18n_t "$key" "$fallback")
    printf -- "$fmt\n" "$@"
}

valid_source() {
    local src=$1
    [ -f "$src" ] && [ ! -L "$src" ] && [ -r "$src" ] || return 1
    [ "$(stat -c %s "$src")" -le 65536 ] || return 1
    grep -q '^\[Service\]' "$src" && grep -q '^ExecStart=' "$src"
}

required() {
    local name=$1 r
    for r in "${REQUIRED[@]}"; do [ "$r" = "$name" ] && return 0; done
    return 1
}

replace_unit() {
    local src=$1 dst=$2 tmp
    tmp=$(mktemp "$DST_DIR/.nuxiva-unit.XXXXXX")
    if ! { cp -- "$src" "$tmp" && chmod 0644 "$tmp" && mv -f -T -- "$tmp" "$dst"; }; then
        rm -f -- "$tmp"
        return 1
    fi
}

wants_restart() {
    local unit=$1
    [ "$unit" != "$SELF" ] || return 1
    [ "$(systemctl show -p Type --value "$unit" 2>/dev/null)" != oneshot ] || return 1
    systemctl is-enabled -q "$unit" 2>/dev/null && return 0
    case "$(systemctl show -p ActiveState --value "$unit" 2>/dev/null)" in
        active|activating|reloading) return 0 ;;
    esac
    return 1
}

[ -d "$SRC_DIR" ] && [ ! -L "$SRC_DIR" ] || exit 0
[ -d "$DST_DIR" ] || exit 0

changed=()
failed=0
for src in "$SRC_DIR"/nuxiva-*.service; do
    [ -e "$src" ] || continue
    name=${src##*/}
    [[ $name =~ $NAME_RE ]] || continue
    dst="$DST_DIR/$name"
    if [ -L "$dst" ]; then
        say units_masked "Unit left untouched (masked or linked by the administrator): %s" "$name"
        continue
    fi
    if [ ! -e "$dst" ] && ! required "$name"; then
        continue
    fi
    if [ -e "$dst" ] && [ ! -f "$dst" ]; then
        say units_invalid "Unit skipped because it is not valid: %s" "$name"
        failed=1
        continue
    fi
    cmp -s -- "$src" "$dst" && continue
    if ! valid_source "$src"; then
        say units_invalid "Unit skipped because it is not valid: %s" "$name"
        failed=1
        continue
    fi
    if replace_unit "$src" "$dst"; then
        changed+=("$name")
        say units_synced "System unit updated to the installed version: %s" "$name"
    else
        say units_failed "Could not update the system unit: %s" "$name"
        failed=1
    fi
done

[ "${#changed[@]}" -gt 0 ] || exit "$failed"

if ! systemctl daemon-reload >/dev/null 2>&1; then
    say units_reload_failed "systemd did not reload the updated units"
    exit 1
fi

for name in "${changed[@]}"; do
    wants_restart "$name" || continue
    systemctl reset-failed "$name" >/dev/null 2>&1 || true
    if systemctl restart --no-block "$name" >/dev/null 2>&1; then
        say units_restarted "Service restarted with its new configuration: %s" "$name"
    else
        say restart_warn "Warning: %s could not be restarted" "$name"
        failed=1
    fi
done

exit "$failed"
