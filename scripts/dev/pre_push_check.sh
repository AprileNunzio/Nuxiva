#!/usr/bin/env bash
set -e

if ! command -v cargo &> /dev/null; then
    if [ -d "$HOME/.cargo/bin" ]; then
        export PATH="$HOME/.cargo/bin:$PATH"
    elif [ -d "/c/Users/$USER/.cargo/bin" ]; then
        export PATH="/c/Users/$USER/.cargo/bin:$PATH"
    fi
fi

echo "==> [1/5] Verifico sintassi Python e linting pyflakes..."
python -m pyflakes server sandbox_broker installer_wizard client_satellite

echo "==> [2/5] Verifico sintassi degli script Shell (bash -n)..."
for f in $(find scripts installer_wizard -name "*.sh") scripts/os/nuxivactl install.sh; do
    [ -f "$f" ] && bash -n "$f"
done

echo "==> [3/5] Verifico formattazione e clippy del core Rust..."
cargo fmt --manifest-path native/Cargo.toml --all --check

if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" || -n "$WINDIR" ]]; then
    echo "[INFO] Piattaforma Windows/MinGW rilevata: verifica clippy e test sui crate compatibili (vitals-core, bus-core)..."
    cargo clippy --manifest-path native/Cargo.toml -p nuxiva-vitals-core -p nuxiva-bus-core --locked -- -D warnings
    echo "==> [4/5] Eseguo test unitari Rust dei crate compatibili Windows..."
    cargo test --manifest-path native/Cargo.toml -p nuxiva-vitals-core -p nuxiva-bus-core --locked
else
    cargo clippy --manifest-path native/Cargo.toml --workspace --all-targets --locked -- -D warnings
    echo "==> [4/5] Eseguo test unitari Rust del workspace..."
    cargo test --manifest-path native/Cargo.toml --workspace --locked
fi

echo "==> [5/5] Eseguo test unitari Python pertinenti..."
python -m unittest installer_wizard.tests.test_reboot_gate installer_wizard.tests.test_ollama_hardware_tuning installer_wizard.tests.test_brain_tuning installer_wizard.tests.test_control_panel_layout server.tests.test_cortex_core_platform server.tests.test_embodied_cortex installer_wizard.tests.test_kiosk_toggle installer_wizard.tests.test_kiosk_smart_display installer_wizard.tests.test_hardware_agent installer_wizard.tests.test_hardware_universal installer_wizard.tests.test_ear_realtime installer_wizard.tests.test_ear_host_mic installer_wizard.tests.test_voice_playback installer_wizard.tests.test_remote_display_captions installer_wizard.tests.test_auto_update_self_healing installer_wizard.tests.test_store_feature installer_wizard.tests.test_os_subsystems -v

echo "==> TUTTI I CONTROLLI PRE-PUSH SUPERATI CON SUCCESSO! Invio in corso a GitHub..."
exit 0
