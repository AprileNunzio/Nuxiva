#!/bin/sh
set -eu

here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../.." && pwd)
deps=${NUXIVA_ESP32_DEPS:-$root/.deps}
build=${NUXIVA_ESP32_BUILD:-$root/.build}
vectors=$(cd "$root/../../../native/crates/node-core/tests" && pwd)/esp32_vectors.json
crypto_rev=37a76b8f7516568e1c575b6dc9268da1ccaac6b6
json_rev=f9fe8557f13d8949eafd49ebd93a2929c4e5065f

fetch() {
    name=$1
    url=$2
    rev=$3
    dir=$deps/$name
    if [ ! -d "$dir/.git" ]; then
        mkdir -p "$dir"
        git -C "$dir" init -q
        git -C "$dir" remote add origin "$url"
    fi
    if [ "$(git -C "$dir" rev-parse -q --verify HEAD 2>/dev/null || true)" != "$rev" ]; then
        git -C "$dir" fetch -q --depth 1 origin "$rev"
        git -C "$dir" checkout -q FETCH_HEAD
    fi
}

fetch arduinolibs https://github.com/rweather/arduinolibs.git "$crypto_rev"
fetch arduinojson https://github.com/bblanchon/ArduinoJson.git "$json_rev"

crypto=$deps/arduinolibs/libraries/Crypto
mkdir -p "$build"

${CXX:-g++} -std=c++17 -O1 -g -Wall -Wextra -Werror -fsanitize=address,undefined -fno-sanitize-recover=undefined \
    -I "$here/stub" -I "$root/src/core" -isystem "$crypto" -isystem "$deps/arduinojson/src" -Wno-maybe-uninitialized \
    "$here/main.cpp" "$here/identity_tests.cpp" "$here/provision_tests.cpp" "$here/device_tests.cpp" "$here/rng_stub.cpp" \
    "$root"/src/core/hexutil.cpp "$root"/src/core/digest.cpp "$root"/src/core/canonical.cpp "$root"/src/core/signer.cpp \
    "$root"/src/core/provision.cpp "$root"/src/core/action.cpp "$root"/src/core/relay_bank.cpp \
    "$root"/src/core/speech_gate.cpp "$root"/src/core/http_date.cpp "$root"/src/core/firmware_manifest.cpp \
    "$crypto/Ed25519.cpp" "$crypto/Curve25519.cpp" "$crypto/BigNumberUtil.cpp" "$crypto/SHA512.cpp" \
    "$crypto/SHA256.cpp" "$crypto/Hash.cpp" "$crypto/Crypto.cpp" \
    -o "$build/core_tests"

"$build/core_tests" "$vectors"
