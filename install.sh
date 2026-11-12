#!/usr/bin/env bash
set -Eeuo pipefail
umask 027
export LC_NUMERIC=C

readonly DEFAULT_REPO="https://github.com/AprileNunzio/Nuxiva"
readonly MIN_FREE_MB=2048
readonly MAX_SCRIPT_BYTES=4000000

REPO_URL="${NUXIVA_REPO:-$DEFAULT_REPO}"
BRANCH="${NUXIVA_BRANCH:-main}"
REF="${NUXIVA_REF:-}"
EXPECT_SHA256="${NUXIVA_SHA256:-}"
MODE=install
CHECK_ONLY=0
PASS=()
WORK=""

declare -A M=()

load_messages() {
    local l="${NUXIVA_LANG:-${LC_ALL:-${LC_MESSAGES:-${LANG:-en}}}}"
    l="${l,,}"; l="${l%%.*}"; l="${l%%_*}"
    case "$l" in
    it) M=(
        [title]="Installazione di Nuxiva" [checks]="Controllo del sistema"
        [os_bad]="Sistema non supportato: serve Debian 12 o Ubuntu 22.04 o successivi con apt-get. Rilevato: %s"
        [arch_bad]="Architettura non supportata: %s (servono x86_64 o arm64)"
        [bash_bad]="Serve bash 4 o successivo"
        [root]="Permessi di amministratore"
        [root_bad]="Servono i permessi di amministratore. Esegui:"
        [tools]="Strumenti di base" [tools_bad]="Manca un programma necessario: %s. Installalo con: sudo apt-get install -y %s"
        [disk]="Spazio libero" [disk_bad]="Spazio insufficiente: %s MB liberi, ne servono almeno %s"
        [net]="Connessione a GitHub" [net_bad]="GitHub non è raggiungibile: controlla la connessione, il DNS o il proxy e riprova"
        [apt]="Sorgenti dei pacchetti"
        [apt_bad]="apt-get update non riesce a leggere le sorgenti dei pacchetti (errore 404 o simile). Righe del problema:"
        [apt_eol]="Questa versione del sistema probabilmente non è più supportata: i suoi archivi sono stati spostati. Aggiorna a una versione supportata e riprova."
        [rev]="Revisione da installare" [rev_bad]="Impossibile trovare la revisione «%s» (HTTP %s)"
        [dl]="Download dell'installatore" [http_bad]="Download non riuscito: HTTP %s su %s"
        [http_404]="Il file non esiste a questo indirizzo (404): controlla repository, branch o commit indicati"
        [verify]="Verifica dell'integrità" [verify_bad]="Verifica fallita: il file scaricato non corrisponde a quello pubblicato. Nulla è stato eseguito."
        [verify_na]="Impossibile ottenere l'impronta di riferimento da GitHub (HTTP %s). Riprova più tardi oppure installa da un clone git."
        [repo_bad]="Repository non valido: è accettato solo un indirizzo https://github.com/proprietario/nome"
        [ref_bad]="Commit non valido: servono 40 caratteri esadecimali"
        [start]="Avvio dell'installazione di base" [checked]="Controlli completati: il sistema è pronto"
        [failed]="Installazione interrotta" [uninstall]="Avvio della disinstallazione"
        [usage]="Uso: install.sh [--check] [--uninstall [--purge] [--yes]] [--branch NOME] [--ref COMMIT] [--sha256 HASH] [--force-apt]" ) ;;
    fr) M=(
        [title]="Installation de Nuxiva" [checks]="Vérification du système"
        [os_bad]="Système non pris en charge : Debian 12 ou Ubuntu 22.04 ou plus récent avec apt-get est requis. Détecté : %s"
        [arch_bad]="Architecture non prise en charge : %s (x86_64 ou arm64 requis)"
        [bash_bad]="bash 4 ou plus récent est requis"
        [root]="Droits d'administrateur"
        [root_bad]="Les droits d'administrateur sont nécessaires. Exécutez :"
        [tools]="Outils de base" [tools_bad]="Programme requis manquant : %s. Installez-le avec : sudo apt-get install -y %s"
        [disk]="Espace libre" [disk_bad]="Espace insuffisant : %s Mo libres, au moins %s nécessaires"
        [net]="Connexion à GitHub" [net_bad]="GitHub est injoignable : vérifiez la connexion, le DNS ou le proxy puis réessayez"
        [apt]="Sources des paquets"
        [apt_bad]="apt-get update ne parvient pas à lire les sources des paquets (erreur 404 ou similaire). Lignes concernées :"
        [apt_eol]="Cette version du système n'est probablement plus prise en charge : ses archives ont été déplacées. Passez à une version prise en charge et réessayez."
        [rev]="Révision à installer" [rev_bad]="Révision « %s » introuvable (HTTP %s)"
        [dl]="Téléchargement de l'installateur" [http_bad]="Échec du téléchargement : HTTP %s sur %s"
        [http_404]="Le fichier n'existe pas à cette adresse (404) : vérifiez le dépôt, la branche ou le commit indiqués"
        [verify]="Vérification de l'intégrité" [verify_bad]="Échec de la vérification : le fichier téléchargé ne correspond pas à celui publié. Rien n'a été exécuté."
        [verify_na]="Impossible d'obtenir l'empreinte de référence auprès de GitHub (HTTP %s). Réessayez plus tard ou installez depuis un clone git."
        [repo_bad]="Dépôt non valide : seule une adresse https://github.com/propriétaire/nom est acceptée"
        [ref_bad]="Commit non valide : 40 caractères hexadécimaux sont requis"
        [start]="Lancement de l'installation de base" [checked]="Vérifications terminées : le système est prêt"
        [failed]="Installation interrompue" [uninstall]="Lancement de la désinstallation"
        [usage]="Usage : install.sh [--check] [--uninstall [--purge] [--yes]] [--branch NOM] [--ref COMMIT] [--sha256 HASH] [--force-apt]" ) ;;
    es) M=(
        [title]="Instalación de Nuxiva" [checks]="Comprobación del sistema"
        [os_bad]="Sistema no compatible: se necesita Debian 12 o Ubuntu 22.04 o posterior con apt-get. Detectado: %s"
        [arch_bad]="Arquitectura no compatible: %s (se necesita x86_64 o arm64)"
        [bash_bad]="Se necesita bash 4 o posterior"
        [root]="Permisos de administrador"
        [root_bad]="Se necesitan permisos de administrador. Ejecuta:"
        [tools]="Herramientas básicas" [tools_bad]="Falta un programa necesario: %s. Instálalo con: sudo apt-get install -y %s"
        [disk]="Espacio libre" [disk_bad]="Espacio insuficiente: %s MB libres, se necesitan al menos %s"
        [net]="Conexión con GitHub" [net_bad]="No se puede acceder a GitHub: revisa la conexión, el DNS o el proxy y vuelve a intentarlo"
        [apt]="Fuentes de paquetes"
        [apt_bad]="apt-get update no puede leer las fuentes de paquetes (error 404 o similar). Líneas del problema:"
        [apt_eol]="Probablemente esta versión del sistema ya no tiene soporte: sus archivos se han trasladado. Actualiza a una versión con soporte y vuelve a intentarlo."
        [rev]="Revisión que se instalará" [rev_bad]="No se encuentra la revisión «%s» (HTTP %s)"
        [dl]="Descarga del instalador" [http_bad]="Descarga fallida: HTTP %s en %s"
        [http_404]="El archivo no existe en esta dirección (404): revisa el repositorio, la rama o el commit indicados"
        [verify]="Verificación de integridad" [verify_bad]="Verificación fallida: el archivo descargado no coincide con el publicado. No se ha ejecutado nada."
        [verify_na]="No se puede obtener la huella de referencia de GitHub (HTTP %s). Vuelve a intentarlo más tarde o instala desde un clon de git."
        [repo_bad]="Repositorio no válido: solo se acepta una dirección https://github.com/propietario/nombre"
        [ref_bad]="Commit no válido: se necesitan 40 caracteres hexadecimales"
        [start]="Inicio de la instalación base" [checked]="Comprobaciones terminadas: el sistema está listo"
        [failed]="Instalación interrumpida" [uninstall]="Inicio de la desinstalación"
        [usage]="Uso: install.sh [--check] [--uninstall [--purge] [--yes]] [--branch NOMBRE] [--ref COMMIT] [--sha256 HASH] [--force-apt]" ) ;;
    *) M=(
        [title]="Nuxiva installer" [checks]="Checking the system"
        [os_bad]="Unsupported system: Debian 12 or Ubuntu 22.04 or later with apt-get is required. Detected: %s"
        [arch_bad]="Unsupported architecture: %s (x86_64 or arm64 required)"
        [bash_bad]="bash 4 or later is required"
        [root]="Administrator rights"
        [root_bad]="Administrator rights are required. Run:"
        [tools]="Basic tools" [tools_bad]="A required program is missing: %s. Install it with: sudo apt-get install -y %s"
        [disk]="Free space" [disk_bad]="Not enough space: %s MB free, at least %s needed"
        [net]="Connection to GitHub" [net_bad]="GitHub cannot be reached: check the connection, DNS or proxy and try again"
        [apt]="Package sources"
        [apt_bad]="apt-get update cannot read the package sources (404 or similar error). Affected lines:"
        [apt_eol]="This system release is probably no longer supported: its archives have been moved. Upgrade to a supported release and try again."
        [rev]="Revision to install" [rev_bad]="Revision \"%s\" not found (HTTP %s)"
        [dl]="Downloading the installer" [http_bad]="Download failed: HTTP %s on %s"
        [http_404]="The file does not exist at this address (404): check the repository, branch or commit given"
        [verify]="Integrity check" [verify_bad]="Verification failed: the downloaded file does not match the published one. Nothing was run."
        [verify_na]="The reference fingerprint could not be obtained from GitHub (HTTP %s). Try again later or install from a git clone."
        [repo_bad]="Invalid repository: only an https://github.com/owner/name address is accepted"
        [ref_bad]="Invalid commit: 40 hexadecimal characters are required"
        [start]="Starting the base installation" [checked]="Checks complete: the system is ready"
        [failed]="Installation stopped" [uninstall]="Starting the uninstaller"
        [usage]="Usage: install.sh [--check] [--uninstall [--purge] [--yes]] [--branch NAME] [--ref COMMIT] [--sha256 HASH] [--force-apt]" ) ;;
    esac
}

if [ -t 2 ] && [ "${TERM:-dumb}" != dumb ] && [ -z "${NO_COLOR:-}" ]; then
    C_OK=$'\033[32m' C_BAD=$'\033[31m' C_DIM=$'\033[2m' C_HEAD=$'\033[1;36m' C_OFF=$'\033[0m'
else
    C_OK="" C_BAD="" C_DIM="" C_HEAD="" C_OFF=""
fi
if [ "$(locale charmap 2>/dev/null || true)" = UTF-8 ]; then G_OK="✓" G_BAD="✗" G_GO="→"; else G_OK="+" G_BAD="x" G_GO=">"; fi

say() { printf '%s\n' "$*" >&2; }
ok() { printf ' %s%s%s %s%s%s\n' "$C_OK" "$G_OK" "$C_OFF" "$1" "${2:+ $C_DIM· }" "${2:-}${2:+$C_OFF}" >&2; }
step() { printf ' %s%s%s %s\n' "$C_HEAD" "$G_GO" "$C_OFF" "$1" >&2; }
fail() {
    local fmt=$1; shift
    local text
    printf -v text "$fmt" "$@"
    printf ' %s%s %s%s\n' "$C_BAD" "$G_BAD" "$text" "$C_OFF" >&2
    printf '\n %s%s%s\n' "$C_DIM" "${M[failed]}" "$C_OFF" >&2
    exit 1
}

cleanup() { if [ -n "$WORK" ] && [ -d "$WORK" ]; then rm -rf -- "$WORK"; fi; }
on_err() { fail "%s (%s %s)" "${M[failed]}" "line" "$1"; }

parse_args() {
    while [ $# -gt 0 ]; do
        case "$1" in
            -h|--help) say "${M[usage]}"; exit 0 ;;
            --check) CHECK_ONLY=1 ;;
            --uninstall) MODE=uninstall ;;
            --branch) [ $# -ge 2 ] || fail "%s" "${M[usage]}"; BRANCH=$2; shift ;;
            --branch=*) BRANCH=${1#*=} ;;
            --ref) [ $# -ge 2 ] || fail "%s" "${M[usage]}"; REF=$2; shift ;;
            --ref=*) REF=${1#*=} ;;
            --sha256) [ $# -ge 2 ] || fail "%s" "${M[usage]}"; EXPECT_SHA256=$2; shift ;;
            --sha256=*) EXPECT_SHA256=${1#*=} ;;
            *) PASS+=("$1") ;;
        esac
        shift
    done
    [[ "$BRANCH" =~ ^[A-Za-z0-9._/-]{1,100}$ ]] && [[ "$BRANCH" != *..* ]] || fail "%s" "${M[usage]}"
    [ -z "$REF" ] || [[ "$REF" =~ ^[0-9a-f]{40}$ ]] || fail "%s" "${M[ref_bad]}"
    [ -z "$EXPECT_SHA256" ] || [[ "$EXPECT_SHA256" =~ ^[0-9a-f]{64}$ ]] || fail "%s" "${M[verify_bad]}"
    REPO_URL="${REPO_URL%/}"; REPO_URL="${REPO_URL%.git}"
    [[ "$REPO_URL" =~ ^https://github\.com/([A-Za-z0-9_.-]{1,100})/([A-Za-z0-9_.-]{1,100})$ ]] || fail "%s" "${M[repo_bad]}"
    SLUG="${BASH_REMATCH[1]}/${BASH_REMATCH[2]}"
}

local_tree() {
    local self="${BASH_SOURCE[0]:-}" dir
    [ -n "$self" ] && [ -f "$self" ] || return 1
    dir="$(cd -P "$(dirname "$self")" && pwd)" || return 1
    [ -f "$dir/installer_wizard/bootstrap.sh" ] && [ -d "$dir/.git" ] || return 1
    printf '%s\n' "$dir"
}

check_system() {
    local id="" like="" ver="" name="" codename="" arch
    (( BASH_VERSINFO[0] >= 4 )) || fail "%s" "${M[bash_bad]}"
    [ "$(uname -s)" = Linux ] || fail "${M[os_bad]}" "$(uname -s)"
    if [ -r /etc/os-release ]; then
        id=$(. /etc/os-release && printf '%s' "${ID:-}")
        like=$(. /etc/os-release && printf '%s' "${ID_LIKE:-}")
        ver=$(. /etc/os-release && printf '%s' "${VERSION_ID:-}")
        name=$(. /etc/os-release && printf '%s' "${PRETTY_NAME:-$ID}")
        codename=$(. /etc/os-release && printf '%s' "${VERSION_CODENAME:-}")
    fi
    case "$id" in
        debian) [[ "${ver%%.*}" =~ ^[0-9]+$ ]] && (( ${ver%%.*} < 12 )) && fail "${M[os_bad]}" "$name" ;;
        ubuntu) [[ "${ver%%.*}" =~ ^[0-9]+$ ]] && (( ${ver%%.*} < 22 )) && fail "${M[os_bad]}" "$name" ;;
        *) [[ " $like " == *" debian "* || " $like " == *" ubuntu "* ]] || fail "${M[os_bad]}" "${name:-unknown}" ;;
    esac
    command -v apt-get >/dev/null 2>&1 || fail "${M[os_bad]}" "${name:-unknown}"
    arch=$(uname -m)
    case "$arch" in x86_64|amd64|aarch64|arm64) ;; *) fail "${M[arch_bad]}" "$arch" ;; esac
    ok "${name:-$id}" "$arch${codename:+ · $codename}"
}

check_root() {
    if [ "$EUID" -eq 0 ]; then ok "${M[root]}"; return 0; fi
    (( CHECK_ONLY )) && return 0
    local self="${BASH_SOURCE[0]:-}"
    if [ -n "$self" ] && [ -f "$self" ] && command -v sudo >/dev/null 2>&1 && ( : </dev/tty ) 2>/dev/null; then
        exec sudo env "NUXIVA_REPO=$REPO_URL" "NUXIVA_BRANCH=$BRANCH" "NUXIVA_REF=$REF" "NUXIVA_SHA256=$EXPECT_SHA256" \
            "NUXIVA_LANG=${NUXIVA_LANG:-${LANG:-}}" bash "$self" "${ORIG_ARGS[@]}" </dev/tty
    fi
    say " ${C_BAD}${G_BAD}${C_OFF} ${M[root_bad]}"
    say "   curl -fsSL https://raw.githubusercontent.com/$SLUG/$BRANCH/install.sh | sudo bash"
    exit 1
}

check_tools() {
    local t
    if ! command -v curl >/dev/null 2>&1 && [ "$EUID" -eq 0 ]; then
        apt-get install -y -q --no-install-recommends curl ca-certificates >/dev/null 2>&1 \
            || { apt-get update -q >/dev/null 2>&1 || true; apt-get install -y -q --no-install-recommends curl ca-certificates >/dev/null 2>&1; } \
            || true
    fi
    for t in curl sha1sum sha256sum mktemp; do
        command -v "$t" >/dev/null 2>&1 || fail "${M[tools_bad]}" "$t" "$( [ "$t" = curl ] && echo curl || echo coreutils )"
    done
    ok "${M[tools]}" "curl · sha256sum"
}

check_disk() {
    local target=/opt free
    [ -d "$target" ] || target=/
    free=$(df -Pm "$target" | awk 'NR==2 {print $4+0}')
    (( free >= MIN_FREE_MB )) || fail "${M[disk_bad]}" "$free" "$MIN_FREE_MB"
    ok "${M[disk]}" "$(( free / 1024 )) GB"
}

http_get() {
    local url=$1 out=$2 accept=${3:-}
    local -a hdr=(-H "User-Agent: nuxiva-installer")
    [ -n "$accept" ] && hdr+=(-H "Accept: $accept")
    local code rc=0
    code=$(curl -sS -L --proto '=https' --proto-redir '=https' --tlsv1.2 --connect-timeout 15 --max-time 180 \
        --retry 3 --retry-delay 2 --retry-connrefused --max-filesize "$MAX_SCRIPT_BYTES" \
        "${hdr[@]}" -o "$out" -w '%{http_code}' "$url" 2>>"$WORK/http.log") || rc=$?
    if (( rc != 0 )); then rm -f -- "$out"; printf '000'; else printf '%s' "${code:-000}"; fi
}

check_network() {
    local code
    local host
    for host in api.github.com raw.githubusercontent.com; do
        code=$(http_get "https://$host/" "$WORK/probe")
        [ "$code" != 000 ] || fail "%s" "${M[net_bad]} ($host)"
    done
    ok "${M[net]}" "api.github.com · raw.githubusercontent.com"
}

check_apt_sources() {
    [ "$EUID" -eq 0 ] || return 0
    local out="$WORK/apt.log" bad
    if pgrep -x apt-get >/dev/null 2>&1 || pgrep -x apt >/dev/null 2>&1 || pgrep -x dpkg >/dev/null 2>&1 || pgrep -f unattended-upgrade >/dev/null 2>&1; then
        return 0
    fi
    timeout 300 apt-get update -q >"$out" 2>&1 || true
    bad=$(grep -E '404 +Not Found|does not have a Release file|no longer has a Release file' "$out" | head -n 6 || true)
    if [ -n "$bad" ]; then
        say " ${C_BAD}${G_BAD}${C_OFF} ${M[apt_bad]}"
        printf '%s\n' "$bad" | sed "s/^/   ${C_DIM}|${C_OFF} /" >&2
        say "   ${M[apt_eol]}"
        printf '\n %s%s%s\n' "$C_DIM" "${M[failed]}" "$C_OFF" >&2
        exit 1
    fi
    ok "${M[apt]}"
}

resolve_ref() {
    local code sha=""
    if [ -n "$REF" ]; then ok "${M[rev]}" "${REF:0:12}"; return 0; fi
    if command -v git >/dev/null 2>&1; then
        sha=$(GIT_TERMINAL_PROMPT=0 timeout 30 git ls-remote "https://github.com/$SLUG.git" "refs/heads/$BRANCH" 2>>"$WORK/http.log" | awk 'NR==1 {print $1}') || sha=""
    fi
    if ! [[ "$sha" =~ ^[0-9a-f]{40}$ ]]; then
        code=$(http_get "https://api.github.com/repos/$SLUG/commits/$BRANCH" "$WORK/ref" "application/vnd.github.sha")
        [ "$code" = 404 ] && say "   ${M[http_404]}"
        [ "$code" = 200 ] || fail "${M[rev_bad]}" "$BRANCH" "$code"
        sha=$(tr -d '[:space:]' <"$WORK/ref")
    fi
    [[ "$sha" =~ ^[0-9a-f]{40}$ ]] || fail "${M[rev_bad]}" "$BRANCH" "?"
    REF=$sha
    ok "${M[rev]}" "${REF:0:12} · $BRANCH"
}

blob_sha1() {
    local f=$1
    { printf 'blob %d\0' "$(wc -c <"$f")"; cat -- "$f"; } | sha1sum | awk '{print $1}'
}

fetch_verified() {
    local path=$1 out=$2 url code expected actual sum
    url="https://raw.githubusercontent.com/$SLUG/$REF/$path"
    code=$(http_get "$url" "$out")
    if [ "$code" != 200 ]; then
        [ "$code" = 404 ] && say "   ${M[http_404]}"
        fail "${M[http_bad]}" "$code" "$url"
    fi
    [ -s "$out" ] || fail "${M[http_bad]}" "$code" "$url"
    head -n 1 "$out" | grep -qE '^#!/usr/bin/env bash|^#!/bin/bash' || fail "%s" "${M[verify_bad]}"
    ok "${M[dl]}" "$path"
    sum=$(sha256sum "$out" | awk '{print $1}')
    if [ -n "$EXPECT_SHA256" ] && [ "$path" = installer_wizard/bootstrap.sh ]; then
        [ "$sum" = "$EXPECT_SHA256" ] || fail "%s" "${M[verify_bad]}"
        ok "${M[verify]}" "sha256 ${sum:0:16}"
        return 0
    fi
    code=$(http_get "https://api.github.com/repos/$SLUG/contents/$path?ref=$REF" "$WORK/meta" "application/vnd.github+json")
    [ "$code" = 200 ] || fail "${M[verify_na]}" "$code"
    expected=$(grep -oE '"sha"[[:space:]]*:[[:space:]]*"[0-9a-f]{40}"' "$WORK/meta" | head -n 1 | grep -oE '[0-9a-f]{40}' || true)
    actual=$(blob_sha1 "$out")
    [[ "$expected" =~ ^[0-9a-f]{40}$ ]] && [ "$expected" = "$actual" ] || fail "%s" "${M[verify_bad]}"
    ok "${M[verify]}" "git ${actual:0:12} · sha256 ${sum:0:16}"
}

run_local() {
    local dir=$1
    if [ "$MODE" = uninstall ]; then exec bash "$dir/scripts/os/uninstall.sh" "${PASS[@]}"; fi
    (( CHECK_ONLY )) && { ok "${M[checked]}"; exit 0; }
    exec bash "$dir/installer_wizard/bootstrap.sh" "${PASS[@]}"
}

main() {
    load_messages
    ORIG_ARGS=("$@")
    parse_args "$@"
    trap 'on_err $LINENO' ERR
    trap cleanup EXIT
    printf '\n %s%s%s\n' "$C_HEAD" "${M[title]}" "$C_OFF" >&2
    local dir
    if dir=$(local_tree); then
        check_system; check_root; check_disk
        run_local "$dir"
    fi
    if [ "$MODE" = uninstall ] && [ -f /opt/Nuxiva/scripts/os/uninstall.sh ]; then
        check_root
        step "${M[uninstall]}"
        exec bash /opt/Nuxiva/scripts/os/uninstall.sh "${PASS[@]}"
    fi
    WORK=$(mktemp -d -t nuxiva-install-XXXXXXXX)
    chmod 700 "$WORK"
    step "${M[checks]}"
    check_system
    check_root
    check_tools
    [ "$MODE" = uninstall ] || check_disk
    check_network
    [ "$MODE" = uninstall ] || check_apt_sources
    resolve_ref
    if [ "$MODE" = uninstall ]; then
        fetch_verified scripts/os/uninstall.sh "$WORK/uninstall.sh"
        step "${M[uninstall]}"
        bash "$WORK/uninstall.sh" "${PASS[@]}" || exit $?
        exit 0
    fi
    fetch_verified installer_wizard/bootstrap.sh "$WORK/bootstrap.sh"
    if (( CHECK_ONLY )); then ok "${M[checked]}"; exit 0; fi
    step "${M[start]}"
    printf '\n' >&2
    NUXIVA_REPO="https://github.com/$SLUG.git" NUXIVA_BRANCH="$BRANCH" NUXIVA_REF="$REF" \
        bash "$WORK/bootstrap.sh" "${PASS[@]}" || exit $?
}

main "$@"
