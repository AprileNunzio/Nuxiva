#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(git rev-parse --show-toplevel)"
OUT="${1:-$(mktemp -d)}"
mkdir -p "$OUT"
cd "$ROOT/native"

if [ -n "${NUXIVA_BENCH_BIN:-}" ]; then
    BIN="$NUXIVA_BENCH_BIN"
else
    cargo build --locked -p nuxiva-bench-core --bin nuxiva-bench
    BIN="${CARGO_TARGET_DIR:-$ROOT/native/target}/debug/nuxiva-bench"
fi
[ -x "$BIN" ] || { echo "bench gate: binary not found" >&2; exit 1; }

expect() {
    local want="$1" label="$2"
    shift 2
    local got=0
    "$@" > /dev/null || got=$?
    if [ "$got" -ne "$want" ]; then
        echo "bench gate: $label: exit $got, expected $want" >&2
        exit 1
    fi
    echo "bench gate: $label ok ($got)"
}

"$BIN" synth --seed 1 --profile healthy --out "$OUT/healthy.json"
"$BIN" synth --seed 1 --profile degraded --out "$OUT/degraded.json"
"$BIN" thresholds --out "$OUT/thresholds.json"
"$BIN" manifest --out "$OUT/manifest.json"

expect 0 "healthy corpus passes" "$BIN" run --obs "$OUT/healthy.json" --thresholds "$OUT/thresholds.json" --out "$OUT/report.json"
cp "$OUT/report.json" "$OUT/baseline.json"
expect 0 "healthy corpus has no regression" "$BIN" run --obs "$OUT/healthy.json" --baseline "$OUT/baseline.json" --out "$OUT/report-regression.json"
expect 2 "degraded corpus is rejected" "$BIN" run --obs "$OUT/degraded.json" --out "$OUT/report-degraded.json"
expect 2 "degraded corpus regresses against baseline" "$BIN" run --obs "$OUT/degraded.json" --baseline "$OUT/baseline.json" --out "$OUT/report-degraded-regression.json"
expect 4 "malformed observations are refused" "$BIN" run --obs "$OUT/thresholds.json"

if [ -n "${NUXIVA_BENCH_LEDGER:-}" ]; then
    "$BIN" a12 add --ledger "$NUXIVA_BENCH_LEDGER" --kind ci_green --id "${GITHUB_RUN_ID:-local}-${GITHUB_RUN_ATTEMPT:-1}"
fi

echo "bench gate: all checks passed, reports in $OUT"
