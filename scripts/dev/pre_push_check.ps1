$ErrorActionPreference = "Stop"

if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    if (Test-Path "$env:USERPROFILE\.cargo\bin") {
        $env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
    }
}

Write-Host "==> [1/4] Verifico sintassi Python e linting pyflakes..." -ForegroundColor Cyan
python -m pyflakes server sandbox_broker installer_wizard client_satellite
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERRORE] Pyflakes ha rilevato errori o import inutilizzati nel codice Python!" -ForegroundColor Red
    exit 1
}

Write-Host "==> [2/4] Verifico formattazione e clippy del core Rust..." -ForegroundColor Cyan
cargo fmt --manifest-path native/Cargo.toml --all --check
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERRORE] Il codice Rust non rispetta 'cargo fmt'. Esegui 'cargo fmt --manifest-path native/Cargo.toml --all'!" -ForegroundColor Red
    exit 1
}

cargo clippy --manifest-path native/Cargo.toml --workspace --all-targets --locked -- -D warnings
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERRORE] Cargo clippy ha rilevato warning o errori!" -ForegroundColor Red
    exit 1
}

Write-Host "==> [3/4] Eseguo test unitari Rust del workspace..." -ForegroundColor Cyan
cargo test --manifest-path native/Cargo.toml --workspace --locked
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERRORE] Uno o piu test Rust sono falliti!" -ForegroundColor Red
    exit 1
}

Write-Host "==> [4/4] Eseguo test unitari Python (installer_wizard e server cortex)..." -ForegroundColor Cyan
Push-Location installer_wizard
try {
    python -m unittest discover -s tests -t . -v
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERRORE] Uno o piu test in installer_wizard/tests sono falliti!" -ForegroundColor Red
        exit 1
    }
} finally {
    Pop-Location
}

python -m unittest server.tests.test_cortex_core_platform server.tests.test_embodied_cortex -v
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERRORE] Uno o piu test della piattaforma Cortex sono falliti!" -ForegroundColor Red
    exit 1
}

Write-Host "==> TUTTI I CONTROLLI PRE-PUSH SUPERATI CON SUCCESSO! Puoi pushare in sicurezza." -ForegroundColor Green
exit 0
