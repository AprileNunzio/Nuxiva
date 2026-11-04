#!/usr/bin/env bash
. "$(dirname "$0")/../lib.sh"

VOICE_DIR=/opt/nuxiva-voice
KOKORO="$VOICE_DIR/kokoro"
KOKORO_URL=https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0
PIPER_VERSION=2023.11.14-2
VOICES_URL=https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0
FALLBACK="${NUXIVA_VOICE_FALLBACK:-it_IT-riccardo-x_low}"
UNIT_SRC="$NUXIVA_DIR/scripts/os/systemd/nuxiva-voice.service"
UNIT=/etc/systemd/system/nuxiva-voice.service
CODE="$NUXIVA_DIR/installer_wizard/features/voices/service.py"
MIGRATION="$NUXIVA_STATE/.voice-v2"

piper_arch() {
    case "$(uname -m)" in
        x86_64) echo x86_64 ;;
        aarch64) echo aarch64 ;;
        *) fail "Architettura non supportata da Piper: $(uname -m)" ;;
    esac
}

piper_voice_path() {
    local v=$1 lang=${1%%-*} rest=${1#*-}
    echo "${lang%%_*}/$lang/${rest%-*}/${rest##*-}/$v"
}

kokoro_ok() { curl -fsS --max-time 5 http://127.0.0.1:8092/health >/dev/null 2>&1; }

piper_ok() {
    local out size
    out=$(mktemp)
    echo "Sistemi vocali operativi." \
        | "$VOICE_DIR/piper/piper" --model "$VOICE_DIR/voices/$FALLBACK.onnx" --output_raw >"$out" 2>/dev/null || true
    size=$(stat -c %s "$out")
    rm -f "$out"
    [ "$size" -gt 4096 ]
}

piper_voices_ready() {
    commercial && return 0
    [ -x "$VOICE_DIR/piper/piper" ] && [ -s "$VOICE_DIR/voices/$FALLBACK.onnx" ]
}

install_piper_fallback() {
    if [ ! -x "$VOICE_DIR/piper/piper" ]; then
        local tarball
        tarball=$(mktemp)
        retry 3 5 download_file "$tarball" \
            "https://github.com/rhasspy/piper/releases/download/$PIPER_VERSION/piper_linux_$(piper_arch).tar.gz" \
            "Piper ($PIPER_VERSION)" 5 20
        rm -rf "$VOICE_DIR/piper"
        tar -xzf "$tarball" -C "$VOICE_DIR"
        rm -f "$tarball"
    fi
    local ext
    for ext in onnx onnx.json; do
        if [ ! -s "$VOICE_DIR/voices/$FALLBACK.$ext" ]; then
            retry 3 5 download_file "$VOICE_DIR/voices/$FALLBACK.$ext" \
                "$VOICES_URL/$(piper_voice_path "$FALLBACK").$ext" "$FALLBACK.$ext" 25 15
        fi
    done
    piper_ok || warn "Voce di riserva Piper non funzionante"
}

step_check() {
    [ -f "$MIGRATION" ] || return 1
    piper_voices_ready || return 1
    [ -s "$KOKORO/kokoro-v1.0.onnx" ] && [ -s "$KOKORO/voices-v1.0.bin" ] || return 1
    same_content "$UNIT" < "$UNIT_SRC" && systemctl is-enabled --quiet nuxiva-voice && kokoro_ok \
        && code_current voice "$CODE"
}

step_apply() {
    mkdir -p "$VOICE_DIR/voices" "$KOKORO"

    if commercial; then
        info "Uso commerciale: la voce di riserva Piper non si installa da sola (ogni voce ha la sua licenza); puoi sceglierla dal pannello Voci"
    else
        install_piper_fallback
    fi

    progress 25 "Ambiente della voce neurale"
    [ -x "$KOKORO/venv/bin/python" ] || python3 -m venv "$KOKORO/venv"
    if ! "$KOKORO/venv/bin/python" -c "import kokoro_onnx, numpy" 2>/dev/null; then
        retry 3 5 "$KOKORO/venv/bin/pip" install -q --upgrade pip
        retry 3 5 "$KOKORO/venv/bin/pip" install -q kokoro-onnx
    fi
    local f base=45
    for f in kokoro-v1.0.onnx voices-v1.0.bin; do
        if [ ! -s "$KOKORO/$f" ]; then
            retry 3 5 download_file "$KOKORO/$f" "$KOKORO_URL/$f" "Kokoro ($f)" "$base" 18
        fi
        base=$((base + 18))
    done

    progress 80 "Avvio del servizio vocale"
    if write_if_changed "$UNIT" < "$UNIT_SRC"; then systemctl daemon-reload; fi
    systemctl enable nuxiva-voice >/dev/null 2>&1
    systemctl restart nuxiva-voice
    wait_for 90 kokoro_ok || fail "Il servizio vocale Kokoro non risponde"
    code_mark voice "$CODE"

    if [ ! -f "$MIGRATION" ]; then
        [ -n "${NUXIVA_VOICE:-}" ] || set_env NUXIVA_VOICE if_sara
        touch "$MIGRATION"
    fi
    info "Voce neurale: ${NUXIVA_VOICE:-if_sara} (riserva: $FALLBACK)"
    progress 100 "Voce neurale maschile attiva"
}

step_main "$@"
