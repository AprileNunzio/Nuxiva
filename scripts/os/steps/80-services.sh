#!/usr/bin/env bash
. "$(dirname "$0")/../lib.sh"
. "$(dirname "$0")/../core_diagnosis.sh"

core_healthy() { curl -fsS --max-time 5 "$CORE_URL/health" >/dev/null 2>&1; }

CORE_USER=nuxiva-core
UNIT_SRC="$NUXIVA_DIR/scripts/os/systemd/nuxiva-core.service"
UNIT=/etc/systemd/system/nuxiva-core.service
NATIVE_ENV="$NUXIVA_ETC/core-native.env"
RUN_MARK="$NUXIVA_STATE/.core-native-running"
DATA_DIRS=(db certs models projects)

native_env() {
    printf '%s\n' PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 "PYTHONPATH=$NUXIVA_DIR" \
        NUXIVA_ENV=production NUXIVA_HOST=0.0.0.0 NUXIVA_PORT=8443 QDRANT_HOST=127.0.0.1 \
        "NUXIVA_TTS_MODELS_DIR=$NUXIVA_DIR/data/models/tts" "BRAIN_ROUTES_PATH=$NUXIVA_STATE/brain/routes.json" \
        "OLLAMA_BASE_URL=$OLLAMA_URL"
}
native_active() { systemctl is-active --quiet nuxiva-core 2>/dev/null; }

native_check() {
    same_content "$UNIT" < "$UNIT_SRC" || return 1
    same_content "$NATIVE_ENV" < <(native_env) || return 1
    [ "$(cat "$RUN_MARK" 2>/dev/null)" = "$(core_src_hash)" ] || return 1
    ! core_code_unreadable "$CORE_USER" || return 1
    native_active && core_healthy
}

stop_containers() {
    command -v docker >/dev/null 2>&1 || return 0
    docker rm -f nuxiva-core nuxiva-qdrant nuxiva-inference atena-core atena-qdrant atena-inference >/dev/null 2>&1 || true
}

stop_native() {
    [ -f "$UNIT" ] || return 0
    systemctl disable --now nuxiva-core >/dev/null 2>&1 || true
    rm -f "$RUN_MARK"
}

prepare_native_data() {
    id "$CORE_USER" >/dev/null 2>&1 \
        || useradd --system --user-group --home-dir /nonexistent --no-create-home --shell /usr/sbin/nologin "$CORE_USER"
    local d
    install -d -m 0750 -o "$CORE_USER" -g "$CORE_USER" "$NUXIVA_DIR/data"
    for d in "${DATA_DIRS[@]}"; do
        install -d -m 0750 -o "$CORE_USER" -g "$CORE_USER" "$NUXIVA_DIR/data/$d"
        chown -R "$CORE_USER:$CORE_USER" "$NUXIVA_DIR/data/$d"
    done
    find "$NUXIVA_DIR/data" -maxdepth 1 -type f -exec chown "$CORE_USER:$CORE_USER" {} +
    install -d -m 0750 -g "$CORE_USER" "$NUXIVA_STATE/brain"
    chgrp "$CORE_USER" "$NUXIVA_STATE/brain"
    chmod 0750 "$NUXIVA_STATE/brain"
    command -v setfacl >/dev/null 2>&1 && setfacl -m "u:$CORE_USER:x" "$NUXIVA_STATE" 2>/dev/null || true
    core_grant_code_access "$CORE_USER"
}

rollback_to_docker() {
    local reason
    reason=$(core_native_reason "$CORE_USER")
    warn "Il core senza Docker non risponde: $reason"
    journalctl -u nuxiva-core -n 40 --no-pager 2>&1 || true
    stop_native
    if command -v docker >/dev/null 2>&1 && docker image inspect nuxiva-core:local >/dev/null 2>&1; then
        warn "Torno al core in Docker, che su questo computer era già installato"
        set_env NUXIVA_CORE_RUNTIME docker
        apply_docker
        return 0
    fi
    core_fail "$reason"
}

apply_native() {
    progress 10 "Preparazione del core senza Docker"
    ensure_secret
    prepare_native_data
    write_if_changed "$NATIVE_ENV" 0600 < <(native_env) || true
    if write_if_changed "$UNIT" < "$UNIT_SRC"; then systemctl daemon-reload; fi
    progress 30 "Spegnimento dei container non più necessari"
    stop_containers
    progress 45 "Avvio di Nuxiva Core"
    systemctl enable nuxiva-core >/dev/null 2>&1
    systemctl restart nuxiva-core
    progress 60 "Attesa risposta di Nuxiva Core"
    if ! wait_for 180 core_healthy; then
        rollback_to_docker
        return 0
    fi
    core_src_hash > "$RUN_MARK"
    info "$(curl -fsS "$CORE_URL/health" | jq -c '{status, version, active_agents}' 2>/dev/null)"
    progress 100 "Servizi operativi senza Docker"
}

running() {
    [ "$(docker inspect -f '{{.State.Running}}' "$1" 2>/dev/null)" = "true" ]
}

up_to_date() {
    local service=$1 want_hash have_hash
    want_hash=$(NUXIVA_SRC_HASH=$(core_src_hash) compose config --hash "$service" 2>/dev/null | awk '{print $2}')
    have_hash=$(docker inspect -f '{{ index .Config.Labels "com.docker.compose.config-hash" }}' "$service" 2>/dev/null)
    [ -n "$want_hash" ] && [ "$want_hash" = "$have_hash" ] || return 1
    if [ "$service" = nuxiva-core ]; then
        [ "$(docker inspect -f '{{.Image}}' nuxiva-core 2>/dev/null)" = \
          "$(docker image inspect -f '{{.Id}}' nuxiva-core:local 2>/dev/null)" ] || return 1
    fi
}

ensure_secret() {
    [ -n "${NUXIVA_SECRET_KEY:-}" ] && [ -n "${NUXIVA_SECRET_KEY//0/}" ] && return 0
    set_env NUXIVA_SECRET_KEY "$(openssl rand -hex 32 2>/dev/null || python3 -c 'import secrets; print(secrets.token_hex(32))')"
    info "Chiave segreta del Core generata"
}

step_check() {
    [ -n "${NUXIVA_SECRET_KEY:-}" ] && [ -n "${NUXIVA_SECRET_KEY//0/}" ] || return 1
    if native_core; then native_check; return; fi
    ! native_active || return 1
    running nuxiva-core && running nuxiva-qdrant \
        && up_to_date nuxiva-core && up_to_date nuxiva-qdrant \
        && core_healthy
}

remove_foreign_containers() {
    local c project
    for c in atena-core atena-qdrant atena-inference; do
        if docker inspect "$c" >/dev/null 2>&1; then
            warn "Rimozione container deprecato $c"
            docker rm -f "$c" >/dev/null 2>&1 || true
        fi
    done
    for c in nuxiva-core nuxiva-qdrant nuxiva-inference; do
        project=$(docker inspect -f '{{ index .Config.Labels "com.docker.compose.project" }}' "$c" 2>/dev/null || true)
        if [ -n "$project" ] && [ "$project" != "nuxiva" ]; then
            warn "Rimozione container legacy $c (progetto '$project')"
            docker rm -f "$c" >/dev/null 2>&1 || true
        fi
    done
}

step_apply() {
    if native_core; then apply_native; else apply_docker; fi
}

apply_docker() {
    progress 10 "Pulizia configurazioni precedenti"
    stop_native
    ensure_secret
    remove_foreign_containers
    [ -d /etc/timezone ] && rmdir /etc/timezone 2>/dev/null || true
    mkdir -p "$NUXIVA_DIR/data/db" "$NUXIVA_DIR/data/certs" "$NUXIVA_DIR/data/qdrant" "$NUXIVA_DIR/data/models"

    progress 30 "Avvio servizi container"
    export NUXIVA_SRC_HASH
    NUXIVA_SRC_HASH=$(core_src_hash)
    retry 3 5 compose up -d --remove-orphans --no-build nuxiva-qdrant nuxiva-core
    if [[ ",${COMPOSE_PROFILES:-}," == *",gpu,"* ]]; then
        if docker image inspect nuxiva-inference:local >/dev/null 2>&1; then
            compose up -d --no-build nuxiva-inference || warn "Inferenza GPU non avviata: Nuxiva prosegue su CPU"
        else
            warn "Immagine di inferenza GPU assente: servizio opzionale saltato"
        fi
    else
        docker rm -f nuxiva-inference >/dev/null 2>&1 || true
    fi

    progress 60 "Attesa risposta di Nuxiva Core"
    if ! wait_for 180 core_healthy; then
        local reason
        reason=$(core_docker_reason)
        warn "Nuxiva Core non risponde: $reason"
        docker logs --tail 40 nuxiva-core 2>&1 || true
        core_fail "$reason"
    fi
    info "$(curl -fsS "$CORE_URL/health" | jq -c '{status, version, active_agents}' 2>/dev/null)"
    progress 100 "Servizi operativi"
}

step_main "$@"
