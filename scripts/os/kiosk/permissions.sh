#!/usr/bin/env bash
set -Eeuo pipefail

NUXIVA_DIR="${NUXIVA_DIR:-/opt/Nuxiva}"
NUXIVA_KIOSK_USER="${NUXIVA_KIOSK_USER:-nuxiva-kiosk}"
SCRIPT_ROOT="$NUXIVA_DIR/scripts"
OS_ROOT="$SCRIPT_ROOT/os"
KIOSK_ROOT="$OS_ROOT/kiosk"
KIOSK_ENTRYPOINTS=("$KIOSK_ROOT/session.sh" "$KIOSK_ROOT/launch.sh")

die() { printf '%s\n' "$*" >&2; exit 1; }

for path in "$NUXIVA_DIR" "$SCRIPT_ROOT" "$OS_ROOT" "$KIOSK_ROOT"; do
    [ -L "$path" ] && die "Percorso Nuxiva non sicuro (link simbolico): $path"
    [ -d "$path" ] || die "Directory script Nuxiva mancante: $path"
done

for path in "${KIOSK_ENTRYPOINTS[@]}" "$OS_ROOT/nuxivactl"; do
    [ -L "$path" ] && die "Script kiosk Nuxiva non sicuro (link simbolico): $path"
    [ -f "$path" ] || die "Script kiosk Nuxiva mancante: $path"
done

if [ "$(id -u)" -eq 0 ]; then
    for path in "$NUXIVA_DIR" "$SCRIPT_ROOT" "$OS_ROOT" "$KIOSK_ROOT" "${KIOSK_ENTRYPOINTS[@]}" "$OS_ROOT/nuxivactl"; do
        [ "$(stat -c %u "$path")" -eq 0 ] || chown --no-dereference root "$path"
    done
fi

chmod o+x,o-w,g-w "$NUXIVA_DIR"
chmod 0755 "$SCRIPT_ROOT" "$OS_ROOT" "$KIOSK_ROOT"
chmod 0755 "${KIOSK_ENTRYPOINTS[@]}" "$OS_ROOT/nuxivactl" \
    "$OS_ROOT/"*.sh "$OS_ROOT/steps/"*.sh

if [ "$(id -u)" -eq 0 ] && id "$NUXIVA_KIOSK_USER" >/dev/null 2>&1 && command -v runuser >/dev/null 2>&1; then
    for path in "${KIOSK_ENTRYPOINTS[@]}"; do
        runuser -u "$NUXIVA_KIOSK_USER" -- test -r "$path" \
            || printf "L'utente kiosk %s non può leggere %s: verificare i permessi delle directory superiori\n" "$NUXIVA_KIOSK_USER" "$path" >&2
    done
fi
