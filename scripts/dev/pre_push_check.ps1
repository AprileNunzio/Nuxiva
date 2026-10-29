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

Write-Host "==> [4/4] Eseguo test unitari Python pertinenti (installer_wizard e server cortex)..." -ForegroundColor Cyan
python -m unittest installer_wizard.tests.test_ollama_hardware_tuning installer_wizard.tests.test_brain_tuning installer_wizard.tests.test_control_panel_layout server.tests.test_cortex_core_platform server.tests.test_embodied_cortex installer_wizard.tests.test_kiosk_toggle installer_wizard.tests.test_hardware_agent installer_wizard.tests.test_hardware_universal -v
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERRORE] Uno o piu test unitari Python pertinenti sono falliti!" -ForegroundColor Red
    exit 1
}

Write-Host "==> TUTTI I CONTROLLI PRE-PUSH SUPERATI CON SUCCESSO! Puoi pushare in sicurezza." -ForegroundColor Green
exit 0
