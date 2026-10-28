#!/usr/bin/env bash
. "$(dirname "$0")/../lib.sh"

OVERRIDE=/etc/systemd/system/ollama.service.d/nuxiva.conf

hardware_parallel() {
    local ram_gb
    ram_gb=$(awk '/MemTotal/ {printf "%d", ($2 / 1024 / 1024) + 0.5}' /proc/meminfo 2>/dev/null || echo 8)
    if [ "$ram_gb" -ge 32 ]; then echo 4; else echo 2; fi
}

max_loaded() {
    local ram_gb
    ram_gb=$(awk '/MemTotal/ {printf "%d", ($2 / 1024 / 1024) + 0.5}' /proc/meminfo 2>/dev/null || echo 8)
    if [ "$ram_gb" -ge 32 ]; then echo 3; elif [ "$ram_gb" -ge 12 ]; then echo 2; else echo 1; fi
}

override_conf() {
    if python3 -c "import sys; sys.path.insert(0, '$NUXIVA_DIR/installer_wizard'); from features.ollama.service import load_config, generate_systemd_override; print(generate_systemd_override(load_config()), end='')" 2>/dev/null; then
        return 0
    fi
    printf '%s\n' \
        '# Gestito da Nuxiva OS (Auto-Tuning Hardware)' \
        '[Service]' \
        'Environment="OLLAMA_HOST=127.0.0.1:11434"' \
        'Environment="OLLAMA_KEEP_ALIVE=24h"' \
        "Environment=\"OLLAMA_MAX_LOADED_MODELS=$(max_loaded)\"" \
        "Environment=\"OLLAMA_NUM_PARALLEL=$(hardware_parallel)\"" \
        'Environment="OLLAMA_MAX_QUEUE=512"' \
        'Environment="OLLAMA_FLASH_ATTENTION=1"' \
        'Restart=always' \
        'RestartSec=3' \
        'CPUWeight=100' \
        'Nice=0'
}

api_ok() { curl -fsS --max-time 5 "$OLLAMA_URL/api/version" >/dev/null 2>&1; }

runner_present() {
    [ -x /usr/local/lib/ollama/llama-server ] || [ -x /usr/lib/ollama/llama-server ]
}

local_off() { ! systemctl is-active --quiet ollama 2>/dev/null; }

ensure_ollama_user() {
    getent group ollama >/dev/null || groupadd -r ollama || true
    if ! id -u ollama >/dev/null 2>&1; then
        useradd -r -g ollama -s /bin/false -m -d /usr/share/ollama ollama 2>/dev/null || \
        useradd -r -s /bin/false -m -d /usr/share/ollama ollama 2>/dev/null || true
    fi
    for grp in render video; do
        getent group "$grp" >/dev/null && usermod -a -G "$grp" ollama 2>/dev/null || true
    done
    mkdir -p /usr/share/ollama/.ollama/models
    chown -R ollama:ollama /usr/share/ollama 2>/dev/null || true
    chmod 755 /usr/share/ollama 2>/dev/null || true
}

unit_present() {
    [ -f /etc/systemd/system/ollama.service ] || [ -f /lib/systemd/system/ollama.service ] || [ -f /usr/lib/systemd/system/ollama.service ]
}

ensure_unit() {
    ensure_ollama_user
    unit_present && return 0
    local bin
    bin=$(command -v ollama)
    printf '%s\n' \
        '[Unit]' \
        'Description=Ollama Service' \
        'After=network-online.target' \
        '' \
        '[Service]' \
        "ExecStart=$bin serve" \
        'User=ollama' \
        'Group=ollama' \
        'Restart=always' \
        'RestartSec=3' \
        'Environment="PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"' \
        'Environment="HOME=/usr/share/ollama"' \
        'WorkingDirectory=/usr/share/ollama' \
        '' \
        '[Install]' \
        'WantedBy=default.target' > /etc/systemd/system/ollama.service
    systemctl daemon-reload
}

step_check() {
    if local_llm_disabled; then
        local_off && ! pgrep -x llama-server >/dev/null 2>&1
        return
    fi
    if ollama_remote; then
        api_ok && local_off
        return
    fi
    if [ "${NUXIVA_BRAIN:-}" != "local" ] && [ -n "${NUXIVA_BRAIN:-}" ]; then
        return 0
    fi
    if [ "${NUXIVA_BRAIN:-}" = "cloud" ]; then
        return 0
    fi
    command -v ollama >/dev/null 2>&1 \
        && runner_present \
        && unit_present \
        && api_ok
}

step_apply() {
    if local_llm_disabled; then
        systemctl disable --now ollama >/dev/null 2>&1 || true
        pkill -x llama-server >/dev/null 2>&1 || true
        info "Ollama locale lasciato spento: Cervello LLM disattivato da Gestore Attivita'"
        progress 100 "Ollama locale disattivato"
        return 0
    fi
    if ollama_remote; then
        progress 30 "Motore neurale remoto: $OLLAMA_URL"
        if systemctl is-active --quiet ollama 2>/dev/null; then
            systemctl disable --now ollama >/dev/null 2>&1 || true
            info "Ollama locale fermato: uso il server remoto e libero la memoria"
        fi
        wait_for 30 api_ok || { warn "Il server Ollama remoto $OLLAMA_URL non risponde"; return 0; }
        info "Ollama remoto $(curl -fsS "$OLLAMA_URL/api/version" | jq -r .version 2>/dev/null) operativo su $OLLAMA_URL"
        progress 100 "Motore neurale remoto operativo"
        return
    fi
    if [ "${NUXIVA_BRAIN:-}" != "local" ]; then
        if [ "${NUXIVA_BRAIN:-}" = "cloud" ] && systemctl is-active --quiet ollama 2>/dev/null; then
            systemctl disable --now ollama >/dev/null 2>&1 || true
            info "Ollama locale fermato: selezionato cervello cloud esterno"
        fi
        info "Motore neurale locale in attesa di scelta (Ollama locale o LLM esterno con API key)"
        progress 100 "In attesa di scelta LLM"
        return 0
    fi
    if ! command -v ollama >/dev/null 2>&1 || ! runner_present; then
        progress 10 "Download e installazione/riparazione del motore neurale Ollama"
        ensure_ollama_user
        local installer
        installer=$(mktemp)
        retry 3 5 curl -fsSL https://ollama.com/install.sh -o "$installer"
        progress 25 "Installazione Ollama (può richiedere alcuni minuti)"
        retry 2 10 sh "$installer"
        rm -f "$installer"
    fi

    progress 75 "Configurazione servizio neurale"
    ensure_unit
    if override_conf | write_if_changed "$OVERRIDE"; then
        systemctl daemon-reload
    fi
    systemctl enable ollama >/dev/null 2>&1 || true
    systemctl restart ollama || true

    progress 90 "Attesa risposta del motore neurale"
    if ! wait_for 90 api_ok; then
        warn "Ollama non risponde su $OLLAMA_URL: proseguo (puoi configurare Ollama o un LLM esterno)"
        journalctl -u ollama -n 25 --no-pager 2>/dev/null || true
        progress 100 "Bypassato: in attesa di configurazione LLM"
        return 0
    fi
    info "Ollama $(curl -fsS "$OLLAMA_URL/api/version" | jq -r .version 2>/dev/null) operativo"
    progress 100 "Motore neurale operativo"
}

step_main "$@"
