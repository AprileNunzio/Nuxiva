#!/bin/sh
set -eu

root=$(cd "$(dirname "$0")/../.." && pwd)
out=$root/client_apk/app/src/main/jniLibs

if ! command -v cargo-ndk >/dev/null 2>&1; then
    echo "cargo-ndk is required: cargo install cargo-ndk --locked" >&2
    exit 1
fi

cd "$root/native"
cargo ndk -t arm64-v8a -t armeabi-v7a -t x86_64 -o "$out" build --release --locked -p nuxiva-wakeword-jni
