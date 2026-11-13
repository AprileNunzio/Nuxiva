#!/usr/bin/env bash
set -Eeuo pipefail
exec bash "$(dirname "$0")/../ci/check.sh" full
