#!/usr/bin/env bash
set -Eeuo pipefail

NUXIVA_DIR="${NUXIVA_DIR:-/opt/Nuxiva}"
SCRIPT_ROOT="$NUXIVA_DIR/scripts"
OS_ROOT="$SCRIPT_ROOT/os"
KIOSK_ROOT="$OS_ROOT/kiosk"

for path in "$SCRIPT_ROOT" "$OS_ROOT" "$KIOSK_ROOT"; do
    [ -d "$path" ] || { printf 'Directory script Nuxiva mancante: %s\n' "$path" >&2; exit 1; }
done

for path in "$KIOSK_ROOT/session.sh" "$KIOSK_ROOT/launch.sh" "$OS_ROOT/nuxivactl"; do
    [ -f "$path" ] || { printf 'Script kiosk Nuxiva mancante: %s\n' "$path" >&2; exit 1; }
done

chmod 0755 "$SCRIPT_ROOT" "$OS_ROOT" "$KIOSK_ROOT"
chmod 0755 "$KIOSK_ROOT/session.sh" "$KIOSK_ROOT/launch.sh" "$OS_ROOT/nuxivactl" \
    "$OS_ROOT/"*.sh "$OS_ROOT/steps/"*.sh
