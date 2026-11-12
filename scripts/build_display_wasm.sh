#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$ROOT/installer_wizard/web/display/hands/wasm"
WANT="$(awk '/^name = "wasm-bindgen"$/{getline; gsub(/version = |"/,""); print; exit}' "$ROOT/native/Cargo.lock")"
HAVE="$(wasm-bindgen --version | awk '{print $2}')"
if [ "$WANT" != "$HAVE" ]; then
  echo "wasm-bindgen-cli $WANT richiesto, trovato $HAVE: cargo install wasm-bindgen-cli --version $WANT --locked" >&2
  exit 1
fi
cd "$ROOT/native"
CARGO_PROFILE_RELEASE_STRIP=false cargo build --release --locked --target wasm32-unknown-unknown -p nuxiva-display-wasm
mkdir -p "$OUT"
wasm-bindgen --target no-modules --no-typescript --out-dir "$OUT" --out-name hands_core \
  "$ROOT/native/target/wasm32-unknown-unknown/release/nuxiva_display_wasm.wasm"
sha256sum "$OUT/hands_core_bg.wasm" | awk '{print $1}' > "$OUT/hands_core_bg.wasm.sha256"
