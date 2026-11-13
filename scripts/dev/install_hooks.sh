#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
chmod +x .githooks/pre-push scripts/ci/check.sh
git config core.hooksPath .githooks
printf 'Hook pre-push attivato / pre-push hook enabled: %s\n' "$(git config core.hooksPath)"
