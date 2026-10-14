#!/usr/bin/env bash
set -Eeuo pipefail
umask 027

export DEBIAN_FRONTEND=noninteractive
NUXIVA_DIR="${NUXIVA_DIR:-/opt/Nuxiva}"
BRANCH="${1:-main}"

ui_lang=""
if [ -r /etc/nuxiva/nuxiva.env ]; then
    ui_lang=$(sed -n 's/^NUXIVA_UI_LANG=//p' /etc/nuxiva/nuxiva.env | tail -n 1)
fi

case "${ui_lang:-${LC_ALL:-${LC_MESSAGES:-${LANG:-}}}}" in
    it*) UI_LANG=it ;;
    fr*) UI_LANG=fr ;;
    *) UI_LANG=en ;;
esac

declare -A L
if [ "$UI_LANG" = it ]; then
    L=(
        [banner]="NUXIVA — AGGIORNAMENTO FORZATO (EMERGENCY)"
        [root_req]="Richiesti privilegi di root: elevazione con sudo..."
        [repo_err]="ERRORE: Repository git non trovato in %s"
        [s1]="[1/6] Configurazione ambiente Git e directory sicure..."
        [s2]="[2/6] Scaricamento versione da GitHub (ramo: %s)..."
        [net_err]="ERRORE: Impossibile contattare GitHub. Verifica connessione Internet."
        [commit_info]="Codice aggiornato al commit: %s - %s"
        [s3]="[3/6] Allineamento dipendenze Supervisore e autoriparazione..."
        [s4]="[4/6] Aggiornamento runtime Core..."
        [s5]="[5/6] Allineamento unit systemd e pulizia lock..."
        [s6]="[6/6] Riavvio coordinato dei servizi Nuxiva..."
        [done_banner]="AGGIORNAMENTO FORZATO COMPLETATO CON SUCCESSO"
        [version_active]="Versione attiva: %s"
        [check_hint]="Stato del sistema consultabile tramite: sudo nuxivactl status"
    )
elif [ "$UI_LANG" = fr ]; then
    L=(
        [banner]="NUXIVA — MISE À JOUR FORCÉE (URGENCE)"
        [root_req]="Privilèges root requis : élévation avec sudo..."
        [repo_err]="ERREUR : Dépôt git introuvable dans %s"
        [s1]="[1/6] Configuration de l'environnement Git et répertoires sécurisés..."
        [s2]="[2/6] Téléchargement de la version depuis GitHub (branche: %s)..."
        [net_err]="ERREUR : Impossible de joindre GitHub. Vérifiez la connexion Internet."
        [commit_info]="Code mis à jour au commit : %s - %s"
        [s3]="[3/6] Alignement des dépendances du Superviseur et autoréparation..."
        [s4]="[4/6] Mise à jour du runtime Core..."
        [s5]="[5/6] Alignement des unités systemd et nettoyage des verrous..."
        [s6]="[6/6] Redémarrage coordonné des services Nuxiva..."
        [done_banner]="MISE À JOUR FORCÉE TERMINÉE AVEC SUCCÈS"
        [version_active]="Version active : %s"
        [check_hint]="État du système consultable via : sudo nuxivactl status"
    )
else
    L=(
        [banner]="NUXIVA — FORCE UPGRADE (EMERGENCY)"
        [root_req]="Root privileges required: elevating with sudo..."
        [repo_err]="ERROR: Git repository not found in %s"
        [s1]="[1/6] Configuring Git environment and safe directories..."
        [s2]="[2/6] Fetching release from GitHub (branch: %s)..."
        [net_err]="ERROR: Unable to contact GitHub. Check Internet connection."
        [commit_info]="Code updated to commit: %s - %s"
        [s3]="[3/6] Aligning Supervisor dependencies and self-healing..."
        [s4]="[4/6] Updating Core runtime..."
        [s5]="[5/6] Aligning systemd units and clearing stale locks..."
        [s6]="[6/6] Coordinated restart of Nuxiva services..."
        [done_banner]="FORCE UPGRADE COMPLETED SUCCESSFULLY"
        [version_active]="Active version: %s"
        [check_hint]="Inspect system status via: sudo nuxivactl status"
    )
fi

if [ -t 1 ]; then
    C_CYAN=$'\033[0;36m' C_GREEN=$'\033[0;32m' C_YELLOW=$'\033[0;33m' C_RED=$'\033[0;31m' C_RESET=$'\033[0m'
else
    C_CYAN="" C_GREEN="" C_YELLOW="" C_RED="" C_RESET=""
fi

if [ -t 1 ]; then
    echo -e "${C_CYAN}==================================================================${C_RESET}"
    echo -e "${C_CYAN}      ${L[banner]}       ${C_RESET}"
    echo -e "${C_CYAN}==================================================================${C_RESET}"
else
    echo "=== ${L[banner]} ==="
fi

if [ "$EUID" -ne 0 ]; then
    echo -e "${C_YELLOW}${L[root_req]}${C_RESET}"
    exec sudo -- "$0" "$@"
fi

if [ ! -d "$NUXIVA_DIR/.git" ]; then
    printf "${C_RED}${L[repo_err]}${C_RESET}\n" "$NUXIVA_DIR" >&2
    exit 1
fi

echo -e "${C_CYAN}${L[s1]}${C_RESET}"
git config --global --add safe.directory "$NUXIVA_DIR" 2>/dev/null || true
git -C "$NUXIVA_DIR" config --add safe.directory '*' 2>/dev/null || true

printf "${C_CYAN}${L[s2]}${C_RESET}\n" "$BRANCH"
if ! git -C "$NUXIVA_DIR" fetch --all --prune --tags; then
    echo -e "${C_RED}${L[net_err]}${C_RESET}" >&2
    exit 1
fi

git -C "$NUXIVA_DIR" checkout -f "$BRANCH" 2>/dev/null || git -C "$NUXIVA_DIR" checkout -f -B "$BRANCH" "origin/$BRANCH"
git -C "$NUXIVA_DIR" reset --hard "origin/$BRANCH"

CURRENT_SHA=$(git -C "$NUXIVA_DIR" rev-parse --short HEAD)
CURRENT_MSG=$(git -C "$NUXIVA_DIR" log -1 --pretty=format:'%s (%cr)')
printf "${C_GREEN}      ${L[commit_info]}${C_RESET}\n" "$CURRENT_SHA" "$CURRENT_MSG"

echo -e "${C_CYAN}${L[s3]}${C_RESET}"
WIZ_VENV="$NUXIVA_DIR/installer_wizard/venv"
WIZ_REQ="$NUXIVA_DIR/installer_wizard/backend/requirements.txt"
if [ -f "$WIZ_REQ" ]; then
    if [ ! -x "$WIZ_VENV/bin/python" ]; then
        python3 -m venv "$WIZ_VENV" 2>/dev/null || true
    fi
    if [ -x "$WIZ_VENV/bin/pip" ]; then
        "$WIZ_VENV/bin/pip" install --upgrade --no-input -q pip 2>/dev/null || true
        if ! "$WIZ_VENV/bin/pip" install --no-input -q -r "$WIZ_REQ" 2>/dev/null; then
            rm -rf "$WIZ_VENV"
            python3 -m venv "$WIZ_VENV" 2>/dev/null || true
            "$WIZ_VENV/bin/pip" install --upgrade --no-input -q pip 2>/dev/null || true
            "$WIZ_VENV/bin/pip" install --no-input -q -r "$WIZ_REQ" 2>/dev/null || true
        fi
    fi
fi

echo -e "${C_CYAN}${L[s4]}${C_RESET}"
CORE_VENV="/opt/nuxiva-core/venv"
CORE_REQ="$NUXIVA_DIR/server/requirements.txt"
if [ -f "$CORE_REQ" ]; then
    if [ ! -x "$CORE_VENV/bin/python" ]; then
        python3 -m venv "$CORE_VENV" 2>/dev/null || true
    fi
    if [ -x "$CORE_VENV/bin/pip" ]; then
        "$CORE_VENV/bin/pip" install --upgrade --no-input -q pip 2>/dev/null || true
        if ! "$CORE_VENV/bin/pip" install --no-input -q -r "$CORE_REQ" 2>/dev/null; then
            rm -rf "$CORE_VENV"
            python3 -m venv "$CORE_VENV" 2>/dev/null || true
            "$CORE_VENV/bin/pip" install --upgrade --no-input -q pip 2>/dev/null || true
            "$CORE_VENV/bin/pip" install --no-input -q -r "$CORE_REQ" 2>/dev/null || true
        fi
    fi
fi

if command -v docker >/dev/null 2>&1 && systemctl is-active --quiet docker; then
    if command -v docker-compose >/dev/null 2>&1; then
        (cd "$NUXIVA_DIR" && docker-compose build nuxiva-core) 2>&1 | tail -n 15 || true
    else
        (cd "$NUXIVA_DIR" && docker compose build nuxiva-core) 2>&1 | tail -n 15 || true
    fi
fi

echo -e "${C_CYAN}${L[s5]}${C_RESET}"
if [ -d "$NUXIVA_DIR/scripts/os/systemd" ]; then
    cp -u "$NUXIVA_DIR/scripts/os/systemd/"*.service /etc/systemd/system/ 2>/dev/null || true
    systemctl daemon-reload 2>/dev/null || true
fi

rm -f /var/lib/nuxiva/update_pending.json /var/lib/nuxiva/bad_revs /run/nuxiva-repair.lock 2>/dev/null || true
chmod +x "$NUXIVA_DIR/scripts/os/nuxivactl" "$NUXIVA_DIR/scripts/os/force-upgrade.sh" 2>/dev/null || true
ln -sfn "$NUXIVA_DIR/scripts/os/nuxivactl" /usr/local/bin/nuxivactl 2>/dev/null || true
ln -sfn "$NUXIVA_DIR/scripts/os/force-upgrade.sh" /usr/local/bin/nuxiva-upgrade 2>/dev/null || true

echo -e "${C_CYAN}${L[s6]}${C_RESET}"
systemctl restart nuxiva-supervisor.service 2>/dev/null || true

if systemctl is-active --quiet nuxiva-core.service 2>/dev/null || systemctl list-unit-files | grep -q "nuxiva-core.service"; then
    systemctl restart nuxiva-core.service 2>/dev/null || true
elif command -v docker >/dev/null 2>&1 && systemctl is-active --quiet docker; then
    (cd "$NUXIVA_DIR" && (docker compose restart nuxiva-core 2>/dev/null || docker-compose restart nuxiva-core 2>/dev/null)) || true
fi

echo -e "\n${C_GREEN}==================================================================${C_RESET}"
echo -e "${C_GREEN} ${L[done_banner]}${C_RESET}"
printf "${C_GREEN} ${L[version_active]}${C_RESET}\n" "$CURRENT_SHA"
echo -e "${C_GREEN}==================================================================${C_RESET}"
echo "${L[check_hint]}"
