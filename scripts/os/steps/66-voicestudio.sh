#!/usr/bin/env bash
. "$(dirname "$0")/../lib.sh"

NAME=nuxiva-voicestudio
VOLUME=nuxiva-voicestudio
PORT=3900
DEFAULT_IMAGE=ghcr.io/debpalash/voicestudio:0.5.6
IMAGE="${NUXIVA_VOICESTUDIO_IMAGE:-$DEFAULT_IMAGE}"
[[ "$IMAGE" =~ ^[a-z0-9][a-z0-9./_-]{0,120}:[A-Za-z0-9._-]{1,64}$ ]] || IMAGE=$DEFAULT_IMAGE
HEALTH="http://127.0.0.1:$PORT/health"
CAPS="http://127.0.0.1:$PORT/.well-known/voicestudio-speech"

wanted() { [ "${NUXIVA_VOICESTUDIO:-0}" = "1" ] && [ "${NUXIVA_VOICESTUDIO_WHERE:-local}" != "remote" ]; }
have_docker() { command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; }
gpu_flags() { has_usable_gpu && docker info 2>/dev/null | grep -qi nvidia && echo "--gpus all" || true; }
signature() { printf '%s|%s|%s' "$IMAGE" "$(gpu_flags)" "$(printf '%s' "${NUXIVA_VOICESTUDIO_KEY:-}" | sha1sum | cut -c1-12)"; }
running_signature() { docker inspect -f '{{ index .Config.Labels "nuxiva.signature" }}' "$NAME" 2>/dev/null || true; }
running() { [ "$(docker inspect -f '{{.State.Running}}' "$NAME" 2>/dev/null)" = "true" ]; }
healthy() {
    curl -fsS --max-time 5 "$HEALTH" >/dev/null 2>&1 && return 0
    if [ -n "${NUXIVA_VOICESTUDIO_KEY:-}" ]; then
        curl -fsS --max-time 5 -H "Authorization: Bearer $NUXIVA_VOICESTUDIO_KEY" "$CAPS" >/dev/null 2>&1 && return 0
    fi
    curl -fsS --max-time 5 "$CAPS" >/dev/null 2>&1
}

remove_container() {
    have_docker || return 0
    docker inspect "$NAME" >/dev/null 2>&1 || return 0
    docker rm -f "$NAME" >/dev/null
    info "Studio delle voci locale fermato: le voci create restano nel volume $VOLUME"
}

step_check() {
    if ! wanted; then
        ! have_docker || ! docker inspect "$NAME" >/dev/null 2>&1
        return
    fi
    # Se il container Docker è attivo ed healthy, eccellente
    if have_docker && running && healthy; then
        return 0
    fi
    # Altrimenti verifica che il motore vocale e gli strumenti di elaborazione nativi siano pronti
    command -v ffmpeg >/dev/null 2>&1 && [ -d /var/lib/nuxiva/voicestudio ]
}

ensure_docker() {
    have_docker && return 0
    progress 8 "Installazione del motore container Docker"
    local installer
    installer=$(mktemp)
    retry 3 5 curl -fsSL https://get.docker.com -o "$installer"
    retry 2 10 sh "$installer" || { apt_heal; sh "$installer"; }
    rm -f "$installer"
    systemctl enable --now docker >/dev/null 2>&1 || true
    wait_for 60 docker info || fail "Docker non si è avviato"
}

ensure_key() {
    [ -n "${NUXIVA_VOICESTUDIO_KEY:-}" ] && return 0
    set_env NUXIVA_VOICESTUDIO_KEY "$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
}

ensure_native_env() {
    progress 10 "Configurazione ambiente nativo Studio delle Voci"
    mkdir -p /var/lib/nuxiva/voicestudio/audio
    chmod 755 /var/lib/nuxiva/voicestudio
    command -v ffmpeg >/dev/null 2>&1 || apt_install ffmpeg
}

step_apply() {
    if ! wanted; then
        remove_container
        progress 100 "Studio delle voci locale non attivo"
        return 0
    fi

    ensure_native_env
    ensure_key

    # Se l'utente richiede espressamente il container esterno O se Docker è già pronto
    local try_container="${NUXIVA_VOICESTUDIO_CONTAINER:-0}"
    if [ "$try_container" = "1" ] && have_docker && [ "$(uname -m)" = "x86_64" ]; then
        progress 25 "Verifica immagine container Studio delle voci"
        if timeout 60 docker pull "$IMAGE" >/dev/null 2>&1; then
            if docker inspect "$NAME" >/dev/null 2>&1 && [ "$(running_signature)" != "$(signature)" ]; then
                docker rm -f "$NAME" >/dev/null
            fi
            if ! docker inspect "$NAME" >/dev/null 2>&1; then
                progress 60 "Avvio dello Studio delle voci"
                local flags
                flags=$(gpu_flags)
                OMNIVOICE_API_KEY="$NUXIVA_VOICESTUDIO_KEY" docker run -d --name "$NAME" --restart unless-stopped $flags \
                    --label "nuxiva.signature=$(signature)" \
                    -p "127.0.0.1:$PORT:$PORT" \
                    -e OMNIVOICE_API_KEY -e OMNIVOICE_ANALYTICS_DISABLED=1 \
                    -v "$VOLUME:/app/omnivoice_data" \
                    "$IMAGE" >/dev/null 2>&1 || true
            elif ! running; then
                docker start "$NAME" >/dev/null 2>&1 || true
            fi
        fi
    fi

    progress 100 "Studio delle voci pronto su questo computer"
}

step_main "$@"
