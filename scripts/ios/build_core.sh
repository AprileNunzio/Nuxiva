#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
NATIVE="$ROOT/native"
OUT="$ROOT/client_ios/Core"
CRATE="nuxiva-mobile-ffi"
LIB="libnuxiva_mobile"
PROFILE="${NUXIVA_IOS_PROFILE:-release}"
DEVICE="aarch64-apple-ios"
SIMULATORS=("aarch64-apple-ios-sim" "x86_64-apple-ios")

rustup target add "$DEVICE" "${SIMULATORS[@]}" >/dev/null
export IPHONEOS_DEPLOYMENT_TARGET=17.0

cd "$NATIVE"
for target in "$DEVICE" "${SIMULATORS[@]}"; do
    cargo build --locked -p "$CRATE" --lib --profile "$PROFILE" --target "$target"
done
cargo build --locked -p "$CRATE" --lib --profile "$PROFILE"
cargo build --locked -p "$CRATE" --features bindgen --bin uniffi-bindgen --profile "$PROFILE"

rm -rf "$OUT"
mkdir -p "$OUT/Generated" "$OUT/Headers" "$OUT/sim"
"$NATIVE/target/$PROFILE/uniffi-bindgen" generate "$NATIVE/target/$PROFILE/$LIB.dylib" \
    --language swift --out-dir "$OUT/gen" --no-format
mv "$OUT/gen/nuxiva_mobile.swift" "$OUT/Generated/"
mv "$OUT/gen/nuxiva_mobileFFI.h" "$OUT/Headers/"
mv "$OUT/gen/nuxiva_mobileFFI.modulemap" "$OUT/Headers/module.modulemap"
rm -rf "$OUT/gen"

lipo -create \
    "$NATIVE/target/${SIMULATORS[0]}/$PROFILE/$LIB.a" \
    "$NATIVE/target/${SIMULATORS[1]}/$PROFILE/$LIB.a" \
    -output "$OUT/sim/$LIB.a"

xcodebuild -create-xcframework \
    -library "$NATIVE/target/$DEVICE/$PROFILE/$LIB.a" -headers "$OUT/Headers" \
    -library "$OUT/sim/$LIB.a" -headers "$OUT/Headers" \
    -output "$OUT/NuxivaCore.xcframework"
rm -rf "$OUT/sim"
echo "NuxivaCore.xcframework ready in $OUT"
