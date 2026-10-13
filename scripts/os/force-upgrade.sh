#!/usr/bin/env bash
# ==============================================================================
# Nuxiva Emergency Force Upgrade
# Esegue un aggiornamento forzato diretto da GitHub via SSH, bypassando
# completamente supervisore, container bloccati e API non responsive.
# ==============================================================================
set -uo pipefail

export DEBIAN_FRONTEND=noninteractive
NUXIVA_DIR="${NUXIVA_DIR:-/opt/Nuxiva}"
BRANCH="${1:-main}"

# Colori terminale
C_CYAN='\033[0;36m'
C_GREEN='\033[0;32m'
C_YELLOW='\033[0;33m'
C_RED='\033[0;31m'
C_RESET='\033[0m'

if [ -t 1 ]; then
    echo -e "${C_CYAN}==================================================================${C_RESET}"
    echo -e "${C_CYAN}      NUXIVA — AGGIORNAMENTO FORZATO DA GITHUB (EMERGENCY)       ${C_RESET}"
    echo -e "${C_CYAN}==================================================================${C_RESET}"
else
    echo "=== NUXIVA — AGGIORNAMENTO FORZATO DA GITHUB (EMERGENCY) ==="
fi

# Controllo privilegi root
if [ "$EUID" -ne 0 ]; then
    echo -e "${C_YELLOW}Richiesti privilegi di root: elevazione con sudo...${C_RESET}"
    exec sudo -- "$0" "$@"
fi

if [ ! -d "$NUXIVA_DIR/.git" ]; then
    echo -e "${C_RED}ERRORE: Repository git non trovato in $NUXIVA_DIR${C_RESET}" >&2
    exit 1
fi

# 1. Configurazione permessi git
echo -e "${C_CYAN}[1/6] Configurazione ambiente Git...${C_RESET}"
git config --global --add safe.directory "$NUXIVA_DIR" 2>/dev/null || true
git -C "$NUXIVA_DIR" config --add safe.directory '*' 2>/dev/null || true

# 2. Scaricamento codice aggiornato da GitHub
echo -e "${C_CYAN}[2/6] Scaricamento dell'ultima versione da GitHub (ramo: $BRANCH)...${C_RESET}"
if ! git -C "$NUXIVA_DIR" fetch --all --prune --tags; then
    echo -e "${C_RED}ERRORE: Impossibile contattare GitHub. Verifica la connessione a Internet.${C_RESET}" >&2
    exit 1
fi

# Reset locale forzato al commit remoto
git -C "$NUXIVA_DIR" checkout -f "$BRANCH" 2>/dev/null || git -C "$NUXIVA_DIR" checkout -f -B "$BRANCH" "origin/$BRANCH"
git -C "$NUXIVA_DIR" reset --hard "origin/$BRANCH"

CURRENT_SHA=$(git -C "$NUXIVA_DIR" rev-parse --short HEAD)
CURRENT_MSG=$(git -C "$NUXIVA_DIR" log -1 --pretty=format:'%s (%cr)')
echo -e "${C_GREEN}      Codice aggiornato al commit: $CURRENT_SHA - $CURRENT_MSG${C_RESET}"

# 3. Aggiornamento dipendenze supervisore / installer wizard
echo -e "${C_CYAN}[3/6] Aggiornamento dipendenze del Supervisore e Wizard...${C_RESET}"
WIZ_VENV="$NUXIVA_DIR/installer_wizard/venv"
if [ -x "$WIZ_VENV/bin/pip" ]; then
    echo "      Aggiornamento pip e requirements in $WIZ_VENV..."
    "$WIZ_VENV/bin/pip" install --upgrade --no-input -q pip 2>/dev/null || true
    "$WIZ_VENV/bin/pip" install --no-input -q -r "$NUXIVA_DIR/installer_wizard/backend/requirements.txt" 2>/dev/null || true
fi

# 4. Aggiornamento dipendenze Core (nativo e container)
echo -e "${C_CYAN}[4/6] Aggiornamento librerie Core (inclusi fix numpy e moduli audio)...${C_RESET}"
CORE_VENV="/opt/nuxiva-core/venv"
if [ -x "$CORE_VENV/bin/pip" ]; then
    echo "      Aggiornamento ambiente nativo Core in $CORE_VENV..."
    "$CORE_VENV/bin/pip" install --upgrade --no-input -q pip 2>/dev/null || true
    "$CORE_VENV/bin/pip" install --no-input -q -r "$NUXIVA_DIR/server/requirements.txt" 2>/dev/null || true
    "$CORE_VENV/bin/pip" install --no-input -q numpy 2>/dev/null || true
fi

# Se Docker è installato e attivo, ricompila l'immagine del Core
if command -v docker >/dev/null 2>&1 && systemctl is-active --quiet docker; then
    echo "      Ricostruzione container Docker nuxiva-core..."
    if command -v docker-compose >/dev/null 2>&1; then
        (cd "$NUXIVA_DIR" && docker-compose build nuxiva-core) 2>&1 | tail -n 15 || true
    else
        (cd "$NUXIVA_DIR" && docker compose build nuxiva-core) 2>&1 | tail -n 15 || true
    fi
fi

# 5. Sincronizzazione unit systemd e pulizia lock bloccati
echo -e "${C_CYAN}[5/6] Allineamento systemd e sblocco stati pendenti...${C_RESET}"
if [ -d "$NUXIVA_DIR/scripts/os/systemd" ]; then
    cp -u "$NUXIVA_DIR/scripts/os/systemd/"*.service /etc/systemd/system/ 2>/dev/null || true
    systemctl daemon-reload 2>/dev/null || true
fi

# Rimuovi file di lock e flag di riparazione o update bloccati
rm -f /var/lib/nuxiva/update_pending.json /var/lib/nuxiva/bad_revs /run/nuxiva-repair.lock 2>/dev/null || true
chmod +x "$NUXIVA_DIR/scripts/os/nuxivactl" "$NUXIVA_DIR/scripts/os/force-upgrade.sh" 2>/dev/null || true
ln -sfn "$NUXIVA_DIR/scripts/os/nuxivactl" /usr/local/bin/nuxivactl 2>/dev/null || true
ln -sfn "$NUXIVA_DIR/scripts/os/force-upgrade.sh" /usr/local/bin/nuxiva-upgrade 2>/dev/null || true

# 6. Riavvio ordinato dei servizi
echo -e "${C_CYAN}[6/6] Riavvio dei servizi Nuxiva...${C_RESET}"
systemctl restart nuxiva-supervisor.service 2>/dev/null || true

if systemctl is-active --quiet nuxiva-core.service 2>/dev/null || systemctl list-unit-files | grep -q "nuxiva-core.service"; then
    systemctl restart nuxiva-core.service 2>/dev/null || true
elif command -v docker >/dev/null 2>&1 && systemctl is-active --quiet docker; then
    (cd "$NUXIVA_DIR" && (docker compose restart nuxiva-core 2>/dev/null || docker-compose restart nuxiva-core 2>/dev/null)) || true
fi

echo -e "\n${C_GREEN}==================================================================${C_RESET}"
echo -e "${C_GREEN} AGGIORNAMENTO FORZATO COMPLETATO CON SUCCESSO!${C_RESET}"
echo -e "${C_GREEN} Versione attiva: $CURRENT_SHA${C_RESET}"
echo -e "${C_GREEN}==================================================================${C_RESET}"
echo "Puoi controllare lo stato del sistema con: sudo nuxivactl status"
