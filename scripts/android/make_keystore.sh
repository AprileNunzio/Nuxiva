#!/bin/sh
set -eu

out=${1:-nuxiva-release.p12}
alias=${2:-nuxiva}

if [ -e "$out" ]; then
    echo "$out already exists" >&2
    exit 1
fi

password=$(openssl rand -hex 24)
keytool -genkeypair -keystore "$out" -storetype PKCS12 -storepass "$password" -keypass "$password" \
    -alias "$alias" -keyalg RSA -keysize 4096 -validity 9125 -dname "CN=Nuxiva,O=Nuxiva"
chmod 600 "$out"

printf 'NUXIVA_ANDROID_KEYSTORE_BASE64=%s\n' "$(base64 < "$out" | tr -d '\n')"
printf 'NUXIVA_ANDROID_KEYSTORE_PASSWORD=%s\n' "$password"
printf 'NUXIVA_ANDROID_KEY_ALIAS=%s\n' "$alias"
printf 'NUXIVA_ANDROID_KEY_PASSWORD=%s\n' "$password"
