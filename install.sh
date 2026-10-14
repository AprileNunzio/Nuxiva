#!/usr/bin/env bash
set -Eeuo pipefail
umask 027

detect_lang() {
    local l="${LC_ALL:-${LC_MESSAGES:-${LANG:-en}}}"
    case "$l" in
        it*|IT*) echo "it" ;;
        fr*|FR*) echo "fr" ;;
        *) echo "en" ;;
    esac
}

err_msg() {
    local lang
    lang="$(detect_lang)"
    case "$lang" in
        it) echo "[ERRORE] Impossibile scaricare o eseguire il bootstrap Nuxiva (curl e wget assenti o falliti)." >&2 ;;
        fr) echo "[ERREUR] Impossible de télécharger ou exécuter le bootstrap Nuxiva (curl et wget absents ou en échec)." >&2 ;;
        *) echo "[ERROR] Unable to download or execute Nuxiva bootstrap (curl and wget missing or failed)." >&2 ;;
    esac
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
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
    err_msg
    exit 1
fi

if [ -s "$TMP_SCRIPT" ]; then
    chmod 700 "$TMP_SCRIPT"
    exec bash "$TMP_SCRIPT" "$@"
else
    err_msg
    exit 1
fi
