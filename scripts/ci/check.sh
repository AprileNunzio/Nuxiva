#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
export PATH="$HOME/.cargo/bin:$PATH"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONHASHSEED=0

MODE="${1:-full}"
REMOTE="${NUXIVA_REMOTE:-origin}"
BRANCH="${NUXIVA_BRANCH:-main}"
PY="${NUXIVA_PYTHON:-python3}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
STEPS=0
FAILED=()

step() {
    STEPS=$((STEPS + 1))
    printf '\n==> [%s] %s\n' "$STEPS" "$1"
}

fail() {
    FAILED+=("$1")
    printf '!! FALLITO / FAILED: %s\n' "$1" >&2
}

run() {
    local label="$1"
    shift
    step "$label"
    if ! "$@"; then
        fail "$label"
    fi
}

changed_files() {
    git diff --name-only "$REMOTE/$BRANCH"...HEAD 2>/dev/null || git diff --name-only HEAD~1 HEAD
}

touches() {
    changed_files | grep -qE "$1"
}

sync_state() {
    step "Allineamento con $REMOTE/$BRANCH / Sync with $REMOTE/$BRANCH"
    git fetch --quiet "$REMOTE" "$BRANCH"
    local behind
    behind="$(git rev-list --count "HEAD..$REMOTE/$BRANCH")"
    if [ "$behind" -gt 0 ]; then
        fail "il ramo è indietro di $behind commit: esegui git pull --rebase $REMOTE $BRANCH / branch is $behind commits behind: run git pull --rebase $REMOTE $BRANCH"
        return
    fi
    if ! git diff --quiet || ! git diff --cached --quiet; then
        fail "modifiche non committate: i controlli devono vedere esattamente ciò che parte / uncommitted changes: checks must see exactly what is pushed"
    fi
}

changelog_check() {
    local head base
    head="$(git rev-parse HEAD)"
    base="$(git rev-parse "$REMOTE/$BRANCH")"
    "$PY" scripts/ci/changelog_required.py "$base" "$head"
}

python_static() {
    "$PY" -m pyflakes server sandbox_broker installer_wizard client_satellite || return 1
    "$PY" -m py_compile $(find server sandbox_broker installer_wizard client_satellite -name "*.py") || return 1
}

script_syntax() {
    local f
    for f in $(find scripts installer_wizard -name "*.sh") scripts/os/nuxivactl install.sh; do
        if [ -f "$f" ]; then bash -n "$f" || return 1; fi
    done
    for f in $(find installer_wizard -name "*.js"); do
        node --check "$f" || return 1
    done
}

rust_checks() {
    cargo fmt --manifest-path native/Cargo.toml --all --check || return 1
    if [ "$MODE" = "full" ] || touches '^native/'; then
        cargo clippy --manifest-path native/Cargo.toml --workspace --all-targets --locked -- -D warnings || return 1
        cargo test --manifest-path native/Cargo.toml --workspace --locked || return 1
    fi
}

web_checks() {
    (cd client_web && npm ci --silent && npm run build --silent) || return 1
    local f
    for f in client_web/tests/*.test.cjs; do
        if [ -f "$f" ]; then node "$f" || return 1; fi
    done
}

unit_checks() {
    "$PY" scripts/ci/unit.py --top installer_wizard --title "Installer wizard" --network report --summary "$TMP/unit.md"
}

kernel_checks() {
    "$PY" scripts/ci/unit.py --top . --start server/tests --title "Kernel" --network report
}

sync_state
run "Note di rilascio per ogni commit / Release note for every commit" changelog_check
run "Limite di 500 righe per file / 500-line limit per file" "$PY" scripts/ci/line_limit.py
run "Accessi ai file solo tramite il server MCP / File access only through the MCP server" "$PY" scripts/ci/fs_boundary.py
run "Nessuna logica MCP in Python / No MCP logic in Python" "$PY" scripts/ci/mcp_boundary.py
run "Marcatori di conflitto git / Git conflict markers" "$PY" scripts/ci/conflict_markers.py
run "Sintassi e analisi statica Python / Python syntax and static analysis" python_static
run "Sintassi script shell e JavaScript / Shell and JavaScript syntax" script_syntax
if [ "$MODE" = "full" ] || touches '^native/'; then
    run "Rust: fmt, clippy, test / Rust: fmt, clippy, tests" rust_checks
fi
if [ "$MODE" = "full" ] || touches '^client_web/'; then
    run "Client web: build e test / Web client: build and tests" web_checks
fi
if [ "$MODE" = "full" ] || touches '^(installer_wizard|server|sandbox_broker|scripts|native)/'; then
    run "Test unitari Python con classificazione / Python unit tests with classification" unit_checks
    run "Test del kernel / Kernel tests" kernel_checks
fi

printf '\n'
if [ "${#FAILED[@]}" -gt 0 ]; then
    printf 'CONTROLLI FALLITI / CHECKS FAILED (%s):\n' "${#FAILED[@]}" >&2
    printf ' - %s\n' "${FAILED[@]}" >&2
    printf 'Il push è bloccato: la CI su main sarebbe rossa. / Push blocked: CI on main would be red.\n' >&2
    exit 1
fi
printf 'TUTTI I CONTROLLI SUPERATI / ALL CHECKS PASSED\n'
