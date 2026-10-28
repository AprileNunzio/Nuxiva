#!/usr/bin/env bash
set -e

if ! command -v cargo &> /dev/null; then
    if [ -d "$HOME/.cargo/bin" ]; then
        export PATH="$HOME/.cargo/bin:$PATH"
    elif [ -d "/c/Users/$USER/.cargo/bin" ]; then
        export PATH="/c/Users/$USER/.cargo/bin:$PATH"
    fi
fi

echo "==> [1/4] Verifico sintassi Python e linting pyflakes..."
python -m pyflakes server sandbox_broker installer_wizard client_satellite

echo "==> [2/4] Verifico formattazione e clippy del core Rust..."
cargo fmt --manifest-path native/Cargo.toml --all --check
cargo clippy --manifest-path native/Cargo.toml --workspace --all-targets --locked -- -D warnings

echo "==> [3/4] Eseguo test unitari Rust del workspace..."
cargo test --manifest-path native/Cargo.toml --workspace --locked

echo "==> [4/4] Eseguo test unitari Python pertinenti..."
python -m unittest installer_wizard.tests.test_ollama_hardware_tuning server.tests.test_cortex_core_platform server.tests.test_embodied_cortex -v

echo "==> TUTTI I CONTROLLI PRE-PUSH SUPERATI CON SUCCESSO! Invio in corso a GitHub..."
exit 0
