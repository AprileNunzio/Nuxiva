#!/usr/bin/env bash

CORE_CODE_DIRS=(server client_satellite/microcontroller)
CORE_SIGILL_EXIT=132
CORE_OOM_EXIT=137

core_code_paths() {
    local d
    for d in "${CORE_CODE_DIRS[@]}"; do
        [ -d "$NUXIVA_DIR/$d" ] && [ ! -L "$NUXIVA_DIR/$d" ] && printf '%s\0' "$NUXIVA_DIR/$d"
    done
}

core_code_parents() {
    printf '%s\0' "$NUXIVA_DIR"
    [ -d "$NUXIVA_DIR/client_satellite" ] && [ ! -L "$NUXIVA_DIR/client_satellite" ] \
        && printf '%s\0' "$NUXIVA_DIR/client_satellite"
    return 0
}

core_code_unreadable() {
    local user=$1
    local -a paths parents
    mapfile -d '' -t paths < <(core_code_paths)
    [ "${#paths[@]}" -gt 0 ] || return 1
    mapfile -d '' -t parents < <(core_code_parents)
    find "${parents[@]}" -maxdepth 0 ! -perm -o=rx -print -quit 2>/dev/null | grep -q . && return 0
    find "${paths[@]}" ! -type l \
        \( \( -type d ! -perm -o=rx \( ! -group "$user" -o ! -perm -g=rx \) \) \
        -o \( ! -type d ! -perm -o=r \( ! -group "$user" -o ! -perm -g=r \) \) \) \
        -print -quit 2>/dev/null | grep -q .
}

core_grant_code_access() {
    local user=$1
    local -a paths parents
    [ -L "$NUXIVA_DIR" ] && fail "Percorso Nuxiva non sicuro (link simbolico): $NUXIVA_DIR"
    mapfile -d '' -t parents < <(core_code_parents)
    chmod o+rx,o-w,g-w "${parents[@]}"
    mapfile -d '' -t paths < <(core_code_paths)
    [ "${#paths[@]}" -gt 0 ] || fail "Codice di Nuxiva Core mancante in $NUXIVA_DIR/server"
    chgrp -R --no-dereference "$user" "${paths[@]}"
    chmod -R g+rX,g-w,o-w "${paths[@]}"
    ! core_code_unreadable "$user" || fail "L'utente $user non può leggere il codice in $NUXIVA_DIR/server"
}

core_cpu_missing_flags() {
    local f missing=()
    [ "$(uname -m)" = x86_64 ] || return 0
    for f in ssse3 sse4_1 sse4_2 popcnt; do
        grep -qw -- "$f" /proc/cpuinfo 2>/dev/null || missing+=("$f")
    done
    echo "${missing[*]}"
}

core_cpu_hint() {
    local missing
    missing=$(core_cpu_missing_flags)
    [ -n "$missing" ] || return 0
    echo "La CPU vista dal sistema non ha le istruzioni ${missing// /, }: se è una macchina virtuale (Proxmox, KVM) imposta il tipo di CPU su 'host' o 'x86-64-v2-AES' e riavviala."
}

core_port_owner() {
    command -v ss >/dev/null 2>&1 || return 0
    { ss -H -ltnp "sport = :${CORE_URL##*:}" 2>/dev/null || true; } \
        | sed -n 's/.*users:(("\([^"]*\)",pid=\([0-9]*\).*/\1 \2/p' | head -n 1
}

core_port_conflict() {
    local own_pid=$1 owner
    owner=$(core_port_owner)
    [ -n "$owner" ] && [ "${owner##* }" != "$own_pid" ] || return 1
    echo "la porta ${CORE_URL##*:} è già occupata dal programma '${owner% *}' (PID ${owner##* })."
}

core_log_tail() {
    grep -E 'Error|Exception|denied|No module|Illegal|Killed|address already in use' -i \
        | tail -n 1 | cut -c1-220 || true
}

core_reason_from_exit() {
    local code=$1 oom=$2 hint
    if [ "$oom" = true ] || [ "$code" = "$CORE_OOM_EXIT" ]; then
        echo "memoria RAM esaurita: Nuxiva Core è stato terminato dal sistema. Assegna almeno 4 GB di RAM."
        return 0
    fi
    if [ "$code" = "$CORE_SIGILL_EXIT" ]; then
        hint=$(core_cpu_hint)
        echo "istruzione della CPU non supportata (SIGILL). ${hint:-Imposta il tipo di CPU della macchina virtuale su 'host'.}"
        return 0
    fi
    return 1
}

core_native_reason() {
    local user=$1 status result line
    if core_code_unreadable "$user"; then
        echo "l'utente $user non può leggere il codice in $NUXIVA_DIR/server (permessi)."
        return 0
    fi
    status=$(systemctl show -p ExecMainStatus --value nuxiva-core 2>/dev/null || true)
    result=$(systemctl show -p Result --value nuxiva-core 2>/dev/null || true)
    case "$result:$status" in
        oom-kill:*) status=$CORE_OOM_EXIT ;;
        core-dump:4|signal:4) status=$CORE_SIGILL_EXIT ;;
    esac
    core_reason_from_exit "$status" false && return 0
    core_port_conflict "$(systemctl show -p MainPID --value nuxiva-core 2>/dev/null || true)" && return 0
    line=$({ journalctl -u nuxiva-core -n 80 --no-pager -o cat 2>/dev/null || true; } | core_log_tail)
    echo "${line:-nessun errore nei log; il servizio non ha risposto entro il tempo previsto.}"
}

core_docker_reason() {
    local state code oom line
    state=$(docker inspect -f '{{.State.Status}}' nuxiva-core 2>/dev/null || true)
    [ -n "$state" ] || { echo "il container nuxiva-core non esiste: la build del Core non è stata completata."; return 0; }
    code=$(docker inspect -f '{{.State.ExitCode}}' nuxiva-core 2>/dev/null || true)
    oom=$(docker inspect -f '{{.State.OOMKilled}}' nuxiva-core 2>/dev/null || true)
    core_reason_from_exit "$code" "$oom" && return 0
    core_port_conflict "$(docker inspect -f '{{.State.Pid}}' nuxiva-core 2>/dev/null)" && return 0
    line=$({ docker logs --tail 80 nuxiva-core 2>&1 || true; } | core_log_tail)
    echo "${line:-container in stato '$state' senza errori nei log; il servizio non ha risposto entro il tempo previsto.}"
}

core_fail() {
    local reason=$1 hint
    hint=$(core_cpu_hint)
    [[ -z "$hint" || "$reason" == *"$hint"* ]] || reason="$reason $hint"
    fail "Nuxiva Core non risponde su $CORE_URL/health: $reason"
}
