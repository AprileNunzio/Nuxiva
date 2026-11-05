#!/usr/bin/env bash
set -Eeuo pipefail
umask 027

PURGE=0
ASSUME_YES=0
FAILURES=0
declare -A M=()

load_messages() {
    local l="${NUXIVA_LANG:-}"
    if [ -z "$l" ] && [ -r /etc/nuxiva/nuxiva.env ]; then
        l=$(sed -n 's/^NUXIVA_UI_LANG=//p' /etc/nuxiva/nuxiva.env | tail -n 1)
    fi
    l="${l:-${LC_ALL:-${LC_MESSAGES:-${LANG:-en}}}}"
    l="${l,,}"; l="${l%%.*}"; l="${l%%_*}"
    case "$l" in
    it) M=(
        [title]="Disinstallazione di Nuxiva" [root]="Servono i permessi di amministratore: esegui con sudo."
        [plan]="Verranno fermati i servizi di Nuxiva e rimossi programma, comandi e configurazioni di sistema."
        [keep]="I tuoi dati (/etc/nuxiva, /var/lib/nuxiva, /srv/nuxiva) restano al loro posto. Usa --purge per eliminarli."
        [purge]="Verranno eliminati anche i tuoi dati: chiavi, archivio cifrato, memoria, file condivisi e account di servizio. Operazione irreversibile."
        [ask]="Scrivi «si» per continuare: " [yes]="si" [abort]="Disinstallazione annullata." [notty]="Nessun terminale disponibile: aggiungi --yes per confermare."
        [services]="Servizi fermati e disattivati" [containers]="Container rimossi" [files]="Programma e file di sistema rimossi"
        [data]="Dati eliminati" [users]="Account di servizio rimossi" [reload]="Configurazione di sistema ricaricata"
        [warn]="Non riuscito" [done]="Nuxiva è stata disinstallata." [partial]="Disinstallazione completata con avvisi: controlla le righe segnate."
        [left]="Restano installati, perché possono servire ad altri programmi: Ollama, Docker e i pacchetti di sistema. Rimuovili a mano se non ti servono."
        [reboot]="Riavvia il computer per ripristinare del tutto la console e i driver video."
        [usage]="Uso: uninstall.sh [--purge] [--yes]" ) ;;
    fr) M=(
        [title]="Désinstallation de Nuxiva" [root]="Les droits d'administrateur sont nécessaires : lancez avec sudo."
        [plan]="Les services de Nuxiva seront arrêtés et le programme, les commandes et la configuration système seront supprimés."
        [keep]="Vos données (/etc/nuxiva, /var/lib/nuxiva, /srv/nuxiva) restent en place. Utilisez --purge pour les supprimer."
        [purge]="Vos données seront aussi supprimées : clés, coffre chiffré, mémoire, fichiers partagés et comptes de service. Opération irréversible."
        [ask]="Tapez « oui » pour continuer : " [yes]="oui" [abort]="Désinstallation annulée." [notty]="Aucun terminal disponible : ajoutez --yes pour confirmer."
        [services]="Services arrêtés et désactivés" [containers]="Conteneurs supprimés" [files]="Programme et fichiers système supprimés"
        [data]="Données supprimées" [users]="Comptes de service supprimés" [reload]="Configuration système rechargée"
        [warn]="Échec" [done]="Nuxiva a été désinstallée." [partial]="Désinstallation terminée avec des avertissements : vérifiez les lignes signalées."
        [left]="Restent installés, car d'autres programmes peuvent en avoir besoin : Ollama, Docker et les paquets système. Supprimez-les à la main si besoin."
        [reboot]="Redémarrez l'ordinateur pour rétablir complètement la console et les pilotes vidéo."
        [usage]="Usage : uninstall.sh [--purge] [--yes]" ) ;;
    es) M=(
        [title]="Desinstalación de Nuxiva" [root]="Se necesitan permisos de administrador: ejecuta con sudo."
        [plan]="Se detendrán los servicios de Nuxiva y se eliminarán el programa, los comandos y la configuración del sistema."
        [keep]="Tus datos (/etc/nuxiva, /var/lib/nuxiva, /srv/nuxiva) se conservan. Usa --purge para eliminarlos."
        [purge]="También se eliminarán tus datos: claves, almacén cifrado, memoria, archivos compartidos y cuentas de servicio. Operación irreversible."
        [ask]="Escribe «si» para continuar: " [yes]="si" [abort]="Desinstalación cancelada." [notty]="No hay terminal disponible: añade --yes para confirmar."
        [services]="Servicios detenidos y desactivados" [containers]="Contenedores eliminados" [files]="Programa y archivos del sistema eliminados"
        [data]="Datos eliminados" [users]="Cuentas de servicio eliminadas" [reload]="Configuración del sistema recargada"
        [warn]="Fallido" [done]="Nuxiva se ha desinstalado." [partial]="Desinstalación terminada con avisos: revisa las líneas marcadas."
        [left]="Siguen instalados porque otros programas pueden necesitarlos: Ollama, Docker y los paquetes del sistema. Elimínalos a mano si no los necesitas."
        [reboot]="Reinicia el equipo para restablecer por completo la consola y los controladores de vídeo."
        [usage]="Uso: uninstall.sh [--purge] [--yes]" ) ;;
    *) M=(
        [title]="Nuxiva uninstaller" [root]="Administrator rights are required: run it with sudo."
        [plan]="Nuxiva services will be stopped and the program, commands and system configuration removed."
        [keep]="Your data (/etc/nuxiva, /var/lib/nuxiva, /srv/nuxiva) stays in place. Use --purge to delete it."
        [purge]="Your data will be deleted too: keys, encrypted vault, memory, shared files and service accounts. This cannot be undone."
        [ask]="Type \"yes\" to continue: " [yes]="yes" [abort]="Uninstall cancelled." [notty]="No terminal available: add --yes to confirm."
        [services]="Services stopped and disabled" [containers]="Containers removed" [files]="Program and system files removed"
        [data]="Data deleted" [users]="Service accounts removed" [reload]="System configuration reloaded"
        [warn]="Failed" [done]="Nuxiva has been uninstalled." [partial]="Uninstall finished with warnings: check the marked lines."
        [left]="Still installed, because other programs may need them: Ollama, Docker and system packages. Remove them by hand if you do not need them."
        [reboot]="Restart the computer to fully restore the console and video drivers."
        [usage]="Usage: uninstall.sh [--purge] [--yes]" ) ;;
    esac
}

if [ -t 2 ] && [ "${TERM:-dumb}" != dumb ] && [ -z "${NO_COLOR:-}" ]; then
    C_OK=$'\033[32m' C_BAD=$'\033[31m' C_WARN=$'\033[33m' C_HEAD=$'\033[1;36m' C_OFF=$'\033[0m'
else
    C_OK="" C_BAD="" C_WARN="" C_HEAD="" C_OFF=""
fi

say() { printf '%s\n' "$*" >&2; }
ok() { printf ' %s+%s %s\n' "$C_OK" "$C_OFF" "$1" >&2; }
warn() { FAILURES=$(( FAILURES + 1 )); printf ' %s!%s %s: %s\n' "$C_WARN" "$C_OFF" "${M[warn]}" "$1" >&2; }
try() { "$@" >/dev/null 2>&1 || warn "$*"; }

parse_args() {
    local a
    for a in "$@"; do
        case "$a" in
            --purge) PURGE=1 ;;
            --yes|-y) ASSUME_YES=1 ;;
            -h|--help) say "${M[usage]}"; exit 0 ;;
            *) say "${M[usage]}"; exit 2 ;;
        esac
    done
}

confirm() {
    local answer=""
    say " ${M[plan]}"
    if (( PURGE )); then say " ${C_BAD}${M[purge]}${C_OFF}"; else say " ${M[keep]}"; fi
    (( ASSUME_YES )) && return 0
    ( : </dev/tty ) 2>/dev/null || { say " ${M[notty]}"; exit 2; }
    printf '\n %s' "${M[ask]}" >/dev/tty
    IFS= read -r answer </dev/tty || answer=""
    answer="${answer,,}"
    if [ "$answer" != "${M[yes],,}" ] && [ "$answer" != yes ]; then say " ${M[abort]}"; exit 1; fi
}

nuxiva_units() {
    {
        systemctl list-unit-files --no-legend --plain 'nuxiva-*' 2>/dev/null | awk '{print $1}'
        find /etc/systemd/system /usr/lib/systemd/system /lib/systemd/system -maxdepth 1 -name 'nuxiva-*' -printf '%f\n' 2>/dev/null
    } | grep -E '^nuxiva-[A-Za-z0-9_@.-]+\.(service|timer|socket|path)$' | sort -u
}

stop_services() {
    local unit
    local -a units=()
    mapfile -t units < <(nuxiva_units)
    for unit in "${units[@]}"; do
        [[ "$unit" == *.timer ]] && try systemctl disable --now "$unit"
    done
    for unit in "${units[@]}"; do
        [[ "$unit" == *.timer ]] && continue
        systemctl disable --now "$unit" >/dev/null 2>&1 || systemctl stop "$unit" >/dev/null 2>&1 || warn "systemctl stop $unit"
    done
    ok "${M[services]} (${#units[@]})"
}

remove_containers() {
    command -v docker >/dev/null 2>&1 || return 0
    local -a ids=()
    mapfile -t ids < <(docker ps -aq --filter 'name=^nuxiva-' 2>/dev/null || true)
    (( ${#ids[@]} )) || return 0
    try docker rm -f "${ids[@]}"
    ok "${M[containers]} (${#ids[@]})"
}

remove_files() {
    local f
    local -a paths=(
        /usr/local/bin/nuxivactl /usr/local/bin/nuxiva-upgrade
        /etc/systemd/system/ollama.service.d/nuxiva.conf
        /etc/systemd/journald.conf.d/nuxiva.conf
        /etc/sysctl.d/90-nuxiva-memory.conf /etc/sysctl.d/99-nuxiva-hardening.conf
        /etc/modprobe.d/nuxiva-blacklist-nouveau.conf
        /etc/logrotate.d/nuxiva /etc/chromium/policies/managed/nuxiva.json /etc/pam.d/nuxiva-admin
        /var/log/nuxiva /run/nuxiva /run/nuxiva-repair.lock /run/nuxiva-upgrade.lock /run/nuxiva-requirements.lock
        /opt/Nuxiva
    )
    shopt -s nullglob
    paths+=(/etc/systemd/system/nuxiva-* /etc/systemd/system/*.wants/nuxiva-* /opt/nuxiva-*)
    shopt -u nullglob
    for f in "${paths[@]}"; do
        [ -e "$f" ] || [ -L "$f" ] || continue
        case "$f" in /|/etc|/opt|/usr|/var|/run|/srv) warn "$f"; continue ;; esac
        rm -rf -- "$f" 2>/dev/null || warn "rm $f"
    done
    f=/etc/systemd/system/getty@tty1.service.d/override.conf
    if [ -f "$f" ] && grep -q 'nuxiva' "$f"; then rm -f -- "$f" || warn "rm $f"; fi
    ok "${M[files]}"
}

purge_data() {
    local kiosk="" u f
    if [ -r /etc/nuxiva/nuxiva.env ]; then kiosk=$(sed -n 's/^NUXIVA_KIOSK_USER=//p' /etc/nuxiva/nuxiva.env | tail -n 1); fi
    for f in /etc/nuxiva /var/lib/nuxiva /srv/nuxiva; do
        [ -e "$f" ] || continue
        rm -rf -- "$f" || warn "rm $f"
    done
    ok "${M[data]}"
    for u in nuxiva-core nuxiva-share "${kiosk:-nuxiva-kiosk}"; do
        [[ "$u" =~ ^nuxiva-[a-z0-9-]+$ ]] || continue
        id -u "$u" >/dev/null 2>&1 || continue
        pkill -u "$u" >/dev/null 2>&1 || true
        if [ "$u" = nuxiva-share ] && command -v smbpasswd >/dev/null 2>&1; then smbpasswd -x "$u" >/dev/null 2>&1 || true; fi
        userdel -r "$u" >/dev/null 2>&1 || userdel "$u" >/dev/null 2>&1 || warn "userdel $u"
    done
    ok "${M[users]}"
}

main() {
    load_messages
    parse_args "$@"
    [ "$EUID" -eq 0 ] || { say "${M[root]}"; exit 1; }
    printf '\n %s%s%s\n\n' "$C_HEAD" "${M[title]}" "$C_OFF" >&2
    confirm
    say ""
    stop_services
    remove_containers
    remove_files
    (( PURGE )) && purge_data
    if systemctl daemon-reload >/dev/null 2>&1; then
        systemctl reset-failed >/dev/null 2>&1 || true
        sysctl --system >/dev/null 2>&1 || true
        ok "${M[reload]}"
    else
        warn "systemctl daemon-reload"
    fi
    say ""
    if (( FAILURES )); then say " ${C_WARN}${M[partial]}${C_OFF}"; else say " ${C_OK}${M[done]}${C_OFF}"; fi
    say " ${M[left]}"
    say " ${M[reboot]}"
    (( FAILURES == 0 ))
}

main "$@"
