#!/usr/bin/env bash
. "$(dirname "$0")/../lib.sh"

NATIVE_SRC="$NUXIVA_DIR/native"
NATIVE_HOME="${NUXIVA_NATIVE_HOME:-/opt/nuxiva-native}"
RUST_VERSION="1.89.0"
MATURIN_VERSION="1.9.6"
RUSTUP_URL="https://static.rust-lang.org/rustup/dist/$(uname -m)-unknown-linux-gnu/rustup-init"
VENV="$NUXIVA_DIR/installer_wizard/venv"
STAMP="$NATIVE_HOME/.installed"
EGRESS_BIN="$NATIVE_HOME/bin/nuxiva-egress"
NETGUARD_BIN="$NATIVE_HOME/bin/nuxiva-netguard"
AGENCY_BIN="$NATIVE_HOME/bin/nuxiva-agency"
AGENCY_UNIT_SRC="$NUXIVA_DIR/scripts/os/systemd/nuxiva-agency.service"
AGENCY_UNIT_DST=/etc/systemd/system/nuxiva-agency.service

export RUSTUP_HOME="$NATIVE_HOME/rustup"
export CARGO_HOME="$NATIVE_HOME/cargo"
export CARGO_TARGET_DIR="$NATIVE_HOME/target"
export PATH="$CARGO_HOME/bin:$PATH"

wanted() { [ "${NUXIVA_NATIVE:-auto}" != "0" ]; }

src_hash() {
    (
        cd "$NUXIVA_DIR"
        git -c safe.directory='*' rev-parse HEAD:native 2>/dev/null | cut -c1-16
    )
}

native_loaded() { "$VENV/bin/python" -I -c "import nuxiva_native" >/dev/null 2>&1; }

step_check() {
    if ! wanted; then
        ! native_loaded && [ ! -e "$EGRESS_BIN" ]
        return
    fi
    [ -x "$VENV/bin/python" ] || return 0
    native_loaded && [ -x "$EGRESS_BIN" ] && [ -x "$NETGUARD_BIN" ] && [ -x "$AGENCY_BIN" ] \
        && cmp -s "$AGENCY_UNIT_SRC" "$AGENCY_UNIT_DST" && [ -n "$(src_hash)" ] && [ "$(cat "$STAMP" 2>/dev/null)" = "$(src_hash)" ]
}

agency_env() {
    local vram=0
    if command -v nvidia-smi >/dev/null 2>&1; then
        vram=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>/dev/null | sort -n | tail -n 1 | tr -dc '0-9')
    fi
    install -d -m 0755 /etc/nuxiva
    printf '%s\n' '# Gestito da Nuxiva OS: memoria della scheda video rilevata in MB' "NUXIVA_AGENCY_VRAM_MB=${vram:-0}" \
        > /etc/nuxiva/agency.env
    chmod 0644 /etc/nuxiva/agency.env
}

install_rust() {
    rustc --version 2>/dev/null | grep -q " $RUST_VERSION " && return 0
    local tmp rc=1
    tmp=$(mktemp -d)
    if curl --proto '=https' --tlsv1.2 -fsSL "$RUSTUP_URL" -o "$tmp/rustup-init" \
        && curl --proto '=https' --tlsv1.2 -fsSL "$RUSTUP_URL.sha256" -o "$tmp/rustup-init.sha256" \
        && [ "$(cut -d' ' -f1 "$tmp/rustup-init.sha256")" = "$(sha256sum "$tmp/rustup-init" | cut -d' ' -f1)" ]; then
        chmod 700 "$tmp/rustup-init"
        "$tmp/rustup-init" -y -q --no-modify-path --profile minimal --default-toolchain "$RUST_VERSION" && rc=0
    fi
    rm -rf "$tmp"
    return "$rc"
}

step_apply() {
    if ! wanted; then
        progress 50 "Core nativo disattivato: ritorno al motore Python"
        "$VENV/bin/pip" uninstall -y -q nuxiva-native >/dev/null 2>&1 || true
        systemctl disable --now nuxiva-agency >/dev/null 2>&1 || true
        rm -f "$STAMP" "$EGRESS_BIN" "$NETGUARD_BIN" "$AGENCY_BIN" "$AGENCY_UNIT_DST"
        progress 100 "Core nativo disattivato"
        return 0
    fi
    [ -x "$VENV/bin/python" ] || { progress 100 "Ambiente del supervisore non pronto: nuovo tentativo al prossimo avvio"; return 0; }
    [ -f "$NATIVE_SRC/Cargo.lock" ] || fail "Sorgenti del core nativo assenti"
    install -d -m 0755 "$NATIVE_HOME"

    progress 5 "Installazione compilatore C (build-essential)"
    apt_install build-essential

    progress 10 "Toolchain Rust $RUST_VERSION verificata (checksum SHA-256)"
    retry 3 5 install_rust || fail "Installazione della toolchain Rust non riuscita"

    progress 35 "Preparazione dello strumento di build"
    [ -x "$NATIVE_HOME/build/bin/maturin" ] || python3 -m venv "$NATIVE_HOME/build"
    retry 3 5 "$NATIVE_HOME/build/bin/pip" install -q "maturin==$MATURIN_VERSION" || fail "Installazione di maturin non riuscita"

    progress 50 "Compilazione del message broker in Rust"
    rm -rf "$NATIVE_HOME/wheels"
    (
        cd "$NATIVE_SRC/crates/nuxiva-native"
        "$NATIVE_HOME/build/bin/maturin" build --release --locked --out "$NATIVE_HOME/wheels" 2>&1 | tail -n 20
        exit "${PIPESTATUS[0]}"
    ) || fail "Compilazione del core nativo non riuscita"

    progress 75 "Compilazione del proxy di uscita della sandbox"
    (
        cd "$NATIVE_SRC"
        cargo build --release --locked -p nuxiva-egress 2>&1 | tail -n 20
        exit "${PIPESTATUS[0]}"
    ) || fail "Compilazione del proxy di uscita non riuscita"
    install -d -m 0755 -o root -g root "$NATIVE_HOME/bin"
    install -m 0755 -o root -g root "$CARGO_TARGET_DIR/release/nuxiva-egress" "$EGRESS_BIN.new"
    mv -f "$EGRESS_BIN.new" "$EGRESS_BIN"

    progress 80 "Compilazione del motore di analisi del traffico (firewall)"
    (
        cd "$NATIVE_SRC"
        cargo build --release --locked -p nuxiva-netguard 2>&1 | tail -n 20
        exit "${PIPESTATUS[0]}"
    ) || fail "Compilazione del motore di analisi del traffico non riuscita"
    install -m 0755 -o root -g root "$CARGO_TARGET_DIR/release/nuxiva-netguard" "$NETGUARD_BIN.new"
    mv -f "$NETGUARD_BIN.new" "$NETGUARD_BIN"

    progress 82 "Compilazione del motore multi-agente dei progetti"
    (
        cd "$NATIVE_SRC"
        cargo build --release --locked -p nuxiva-agency 2>&1 | tail -n 20
        exit "${PIPESTATUS[0]}"
    ) || fail "Compilazione del motore multi-agente non riuscita"
    install -m 0755 -o root -g root "$CARGO_TARGET_DIR/release/nuxiva-agency" "$AGENCY_BIN.new"
    mv -f "$AGENCY_BIN.new" "$AGENCY_BIN"
    install -m 0644 -o root -g root "$AGENCY_UNIT_SRC" "$AGENCY_UNIT_DST"
    agency_env
    systemctl daemon-reload
    systemctl enable nuxiva-agency >/dev/null 2>&1 || true
    systemctl restart nuxiva-agency || fail "Avvio del motore multi-agente non riuscito"

    progress 85 "Installazione nel supervisore"
    "$VENV/bin/pip" install -q --force-reinstall --no-deps "$NATIVE_HOME"/wheels/nuxiva_native-*.whl \
        || fail "Installazione del modulo nativo non riuscita"
    native_loaded || fail "Il modulo nativo non si carica"
    src_hash > "$STAMP"
    info "Core nativo attivo dal prossimo riavvio del supervisore"
    progress 100 "Core nativo Rust pronto"
}

step_main "$@"
