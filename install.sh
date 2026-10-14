#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BOOTSTRAP_LOCAL="$SCRIPT_DIR/installer_wizard/bootstrap.sh"
BOOTSTRAP_URL="${NUXIVA_BOOTSTRAP_URL:-https://raw.githubusercontent.com/AprileNunzio/NUXIVA/main/installer_wizard/bootstrap.sh}"

if [ -f "$BOOTSTRAP_LOCAL" ]; then
    exec bash "$BOOTSTRAP_LOCAL" "$@"
fi

if command -v curl >/dev/null 2>&1; then
    exec bash -c "$(curl -fsSL "$BOOTSTRAP_URL")" -- "$@"
elif command -v wget >/dev/null 2>&1; then
    exec bash -c "$(wget -qO- "$BOOTSTRAP_URL")" -- "$@"
else
    echo "ERROR: Neither curl nor wget is available to download Nuxiva bootstrap." >&2
    exit 1
fi
