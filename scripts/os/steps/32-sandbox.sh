#!/usr/bin/env bash
. "$(dirname "$0")/../lib.sh"

IMAGE=nuxiva-sandbox:local
BASE_IMAGE=python:3.11-slim-bookworm
UNIT_SRC="$NUXIVA_DIR/scripts/os/systemd/nuxiva-sandbox.service"
UNIT_DST=/etc/systemd/system/nuxiva-sandbox.service
SOCKET=/run/nuxiva/sandbox/broker.sock
EGRESS_BRIDGE=nuxiva-sbx0
EGRESS_GATEWAY=172.29.240.1
EGRESS_PORTS=38000:38099

sources() {
    find "$NUXIVA_DIR/sandbox_broker" "$NUXIVA_DIR/server/features/sandbox" -name '*.py' | sort
    echo "$UNIT_SRC"
    echo "$NUXIVA_DIR/scripts/os/steps/32-sandbox.sh"
    echo "$NUXIVA_DIR/docker/sandbox/Dockerfile"
}

service_active() { systemctl is-active --quiet nuxiva-sandbox; }

firewall_active() { command -v ufw >/dev/null 2>&1 && ufw status 2>/dev/null | grep -q "Status: active"; }

firewall_ready() { ! firewall_active || ufw status | grep -q "$EGRESS_BRIDGE"; }

open_egress_proxy_ports() {
    firewall_active || return 0
    ufw allow in on "$EGRESS_BRIDGE" to "$EGRESS_GATEWAY" port "$EGRESS_PORTS" proto tcp >/dev/null
}

step_check() {
    code_current sandbox $(sources) \
        && docker image inspect "$IMAGE" >/dev/null 2>&1 \
        && service_active \
        && firewall_ready \
        && [ -S "$SOCKET" ]
}

step_apply() {
    progress 5 "Verifica prerequisiti"
    apt_install python3 curl ca-certificates
    docker info >/dev/null 2>&1 || fail "Docker non risponde"

    progress 20 "Immagine di base"
    retry 3 10 docker pull "$BASE_IMAGE" >/dev/null || warn "Pull dell'immagine base non riuscito: uso la copia locale se presente"

    progress 50 "Immagine della sandbox"
    docker build --quiet -t "$IMAGE" "$NUXIVA_DIR/docker/sandbox" >/dev/null || fail "Build dell'immagine sandbox non riuscita"

    progress 70 "Uscita controllata verso le API"
    open_egress_proxy_ports || warn "Regola del firewall per il proxy di uscita non applicata: gli script senza rete funzionano comunque"

    progress 80 "Servizio Sandbox Broker"
    install -m 0644 "$UNIT_SRC" "$UNIT_DST"
    systemctl daemon-reload
    systemctl enable nuxiva-sandbox >/dev/null 2>&1
    systemctl restart nuxiva-sandbox
    wait_for 60 test -S "$SOCKET" || fail "Il Sandbox Broker non si è avviato: journalctl -u nuxiva-sandbox"

    code_mark sandbox $(sources)
    progress 100 "Sandbox isolata attiva"
}

step_main "$@"
