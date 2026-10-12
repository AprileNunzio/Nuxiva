#!/usr/bin/env bash
set -Eeuo pipefail

NUXIVA_DIR="${NUXIVA_DIR:-/opt/Nuxiva}"
WIZ="$NUXIVA_DIR/installer_wizard"
VENV="$WIZ/venv"
REQ="$WIZ/backend/requirements.txt"
STAMP="$VENV/.requirements.sha1"

mkdir -p /etc/nuxiva /var/lib/nuxiva /var/log/nuxiva
touch /etc/nuxiva/nuxiva.env
chmod 700 /etc/nuxiva
chmod 600 /etc/nuxiva/nuxiva.env

if ! "$VENV/bin/python" -c "import fastapi, uvicorn, httpx, psutil, pam" >/dev/null 2>&1 \
        && [ -f "$STAMP" ]; then
    echo "Ambiente Python corrotto: ricostruzione"
    rm -rf "$VENV"
fi
if [ ! -x "$VENV/bin/pip" ]; then
    rm -rf "$VENV"
    python3 -m venv "$VENV"
fi
want=$(sha1sum "$REQ" | cut -c1-40)
have=$(cat "$STAMP" 2>/dev/null || true)
install_requirements() {
    flock -w 1800 9 || return 1
    [ "$(cat "$STAMP" 2>/dev/null || true)" = "$want" ] && return 0
    "$VENV/bin/pip" install "$@" --disable-pip-version-check --no-input --upgrade pip || return 1
    "$VENV/bin/pip" install "$@" --disable-pip-version-check --no-input -r "$REQ" || return 1
    echo "$want" > "$STAMP.tmp" && mv -f "$STAMP.tmp" "$STAMP"
}
if [ -z "$have" ] || ! "$VENV/bin/python" -c "import fastapi, uvicorn, httpx, psutil, pam" >/dev/null 2>&1; then
    echo "Installazione delle librerie Python di Nuxiva, può richiedere alcuni minuti..."
    install_requirements --progress-bar off 9>"$VENV/.requirements.lock"
elif [ "$have" != "$want" ]; then
    echo "Aggiornamento librerie in background..."
    ( install_requirements -q 9>"$VENV/.requirements.lock" || true ) &
fi

pkill -f 'backend/wizard_server.py' >/dev/null 2>&1 || true

units_changed=0
for unit in nuxiva-supervisor.service nuxiva-rollback.service; do
    src="$NUXIVA_DIR/scripts/os/systemd/$unit"
    if [ -f "$src" ] && ! cmp -s "$src" "/etc/systemd/system/$unit"; then
        install -m 0644 "$src" /etc/systemd/system/
        units_changed=1
    fi
done
if [ "$units_changed" = 1 ]; then systemctl daemon-reload >/dev/null 2>&1 || true; fi

if [ ! -f /etc/pam.d/nuxiva-admin ]; then
    printf '%s\n' '# Nuxiva OS admin panel' '@include common-auth' '@include common-account' > /etc/pam.d/nuxiva-admin
fi
getent group nuxiva-admin >/dev/null || groupadd --system nuxiva-admin
