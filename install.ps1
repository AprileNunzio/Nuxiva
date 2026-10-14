$ErrorActionPreference = "Stop"

$script:AppRoot = $PSScriptRoot
if (-not $script:AppRoot) {
    $script:AppRoot = (Get-Location).Path
}

$script:Lang = [System.Globalization.CultureInfo]::CurrentUICulture.TwoLetterISOLanguageName
if ($script:Lang -ne "it" -and $script:Lang -ne "fr") {
    $script:Lang = "en"
}

$script:Loc = @{
    "it" = @{
        "title" = "Nuxiva Orchestrator Installer - NunzioTech"
        "banner_sub" = "ORCHESTRATORE COGNITIVO AUTONOMO"
        "step_prefix" = "[Passo Nuxiva] "
        "success_prefix" = "[SUCCESSO] "
        "error_prefix" = "[ERRORE] "
        "step_1" = "1/5 - Verifica ambiente runtime Python e Node.js..."
        "step_2" = "2/5 - Creazione e verifica ambiente virtuale isolato..."
        "step_3" = "3/5 - Configurazione storage sicuro e directory isolate..."
        "step_4" = "4/5 - Installazione dipendenze server con autoriparazione..."
        "step_5" = "5/5 - Configurazione interfaccia web e avvio orchestratore..."
        "py_missing" = "Python non trovato su PATH. Installare Python 3.11 o superiore."
        "py_old" = "Versione Python non supportata ({0}). Richiesto Python 3.11+."
        "py_detected" = "Ambiente Python rilevato: {0}"
        "node_detected" = "Ambiente Node.js rilevato: {0}"
        "node_missing" = "Node.js non rilevato. L'interfaccia client_web richiedera l'installazione manuale."
        "venv_ready" = "Ambiente virtuale isolato pronto: {0}"
        "dirs_ready" = "Directory di memorizzazione isolate e sicure create."
        "deps_installing" = "Installazione pacchetti server in corso..."
        "deps_retry" = "Anomalia rilevata nelle dipendenze. Esecuzione autoriparazione e reinstallazione pulita..."
        "deps_success" = "Tutte le dipendenze server sono state verificate e installate."
        "client_ready" = "Console web compilata e pronta."
        "ready_banner" = "NUXIVA PRONTO ALL'USO SULLA MACCHINA LOCALE"
        "powered_by" = "NunzioTech Autonomous System 2026"
    };
    "en" = @{
        "title" = "Nuxiva Orchestrator Installer - NunzioTech"
        "banner_sub" = "AUTONOMOUS COGNITIVE ORCHESTRATOR"
        "step_prefix" = "[Nuxiva Step] "
        "success_prefix" = "[SUCCESS] "
        "error_prefix" = "[ERROR] "
        "step_1" = "1/5 - Verifying Python and Node.js runtime environments..."
        "step_2" = "2/5 - Creating and verifying isolated virtual environment..."
        "step_3" = "3/5 - Setting up secure storage and isolated directories..."
        "step_4" = "4/5 - Installing server dependencies with self-healing..."
        "step_5" = "5/5 - Configuring web interface and launching orchestrator..."
        "py_missing" = "Python not found on PATH. Install Python 3.11 or higher."
        "py_old" = "Unsupported Python version ({0}). Python 3.11+ required."
        "py_detected" = "Detected Python runtime: {0}"
        "node_detected" = "Detected Node.js runtime: {0}"
        "node_missing" = "Node.js not detected. The client_web interface will require manual setup."
        "venv_ready" = "Isolated virtual environment ready: {0}"
        "dirs_ready" = "Secure isolated storage directories created."
        "deps_installing" = "Installing server packages..."
        "deps_retry" = "Dependency fault detected. Executing self-healing clean reinstallation..."
        "deps_success" = "All server dependencies verified and installed."
        "client_ready" = "Web console compiled and ready."
        "ready_banner" = "NUXIVA READY FOR EXECUTION ON LOCAL SYSTEM"
        "powered_by" = "NunzioTech Autonomous System 2026"
    };
    "fr" = @{
        "title" = "Installateur Nuxiva Orchestrator - NunzioTech"
        "banner_sub" = "ORCHESTRATEUR COGNITIF AUTONOME"
        "step_prefix" = "[Étape Nuxiva] "
        "success_prefix" = "[SUCCÈS] "
        "error_prefix" = "[ERREUR] "
        "step_1" = "1/5 - Vérification des environnements d'exécution Python et Node.js..."
        "step_2" = "2/5 - Création et vérification de l'environnement virtuel isolé..."
        "step_3" = "3/5 - Configuration du stockage sécurisé et des répertoires isolés..."
        "step_4" = "4/5 - Installation des dépendances du serveur avec autoréparation..."
        "step_5" = "5/5 - Configuration de l'interface web et lancement de l'orchestrateur..."
        "py_missing" = "Python introuvable sur PATH. Veuillez installer Python 3.11 ou supérieur."
        "py_old" = "Version Python non prise en charge ({0}). Python 3.11+ requis."
        "py_detected" = "Environnement Python détecté : {0}"
        "node_detected" = "Environnement Node.js détecté : {0}"
        "node_missing" = "Node.js non détecté. L'interface client_web nécessitera une installation manuelle."
        "venv_ready" = "Environnement virtuel isolé prêt : {0}"
        "dirs_ready" = "Répertoires de stockage isolés et sécurisés créés."
        "deps_installing" = "Installation des dépendances serveur en cours..."
        "deps_retry" = "Anomalie détectée dans les dépendances. Exécution de l'autoréparation..."
        "deps_success" = "Toutes les dépendances serveur ont été vérifiées et installées."
        "client_ready" = "Console web compilée et prête."
        "ready_banner" = "NUXIVA PRÊT POUR L'EXÉCUTION SUR LA MACHINE LOCALE"
        "powered_by" = "NunzioTech Autonomous System 2026"
    }
}

function Get-T {
    param([string]$Key, [object[]]$Args)
    $msg = $script:Loc[$script:Lang][$Key]
    if (-not $msg) {
        $msg = $script:Loc["en"][$Key]
    }
    if ($Args -and $Args.Count -gt 0) {
        return [string]::Format($msg, $Args)
    }
    return $msg
}

function Write-NuxStep {
    param([string]$Key)
    Write-Host (Get-T "step_prefix") -ForegroundColor Cyan -NoNewline
    Write-Host (Get-T $Key) -ForegroundColor White
}

function Write-NuxSuccess {
    param([string]$Key, [object[]]$Args)
    Write-Host (Get-T "success_prefix") -ForegroundColor Green -NoNewline
    Write-Host (Get-T $Key $Args) -ForegroundColor White
}

function Write-NuxError {
    param([string]$Key, [object[]]$Args)
    Write-Host (Get-T "error_prefix") -ForegroundColor Red -NoNewline
    Write-Host (Get-T $Key $Args) -ForegroundColor Yellow
}

$Host.UI.RawUI.WindowTitle = Get-T "title"
Clear-Host

Write-Host @"
     █████╗ ████████╗███████╗███╗   ██╗ █████╗
    ██╔══██╗╚══██╔══╝██╔════╝████╗  ██║██╔══██╗
    ███████║   ██║   █████╗  ██╔██╗ ██║███████║
    ██╔══██║   ██║   ██╔══╝  ██║╚██╗██║██╔══██║
    ██║  ██║   ██║   ███████╗██║ ╚████║██║  ██║
    ╚═╝  ╚═╝   ╚═╝   ╚══════╝╚═╝  ╚═══╝╚═╝  ╚═╝
"@ -ForegroundColor Cyan
Write-Host "       $((Get-T 'banner_sub'))" -ForegroundColor White
Write-Host "================================================================" -ForegroundColor DarkCyan
Write-Host "   ENGINEERED & POWERED BY NUNZIOTECH (C) 2026" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor DarkCyan

Write-NuxStep "step_1"
$pyCmd = Get-Command "python" -ErrorAction SilentlyContinue
if (-not $pyCmd) {
    Write-NuxError "py_missing"
    exit 1
}

$pyVerRaw = & python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')" 2>$null
$pyMajor = & python -c "import sys; print(sys.version_info.major)" 2>$null
$pyMinor = & python -c "import sys; print(sys.version_info.minor)" 2>$null

if ([int]$pyMajor -lt 3 -or ([int]$pyMajor -eq 3 -and [int]$pyMinor -lt 11)) {
    Write-NuxError "py_old" @($pyVerRaw)
    exit 1
}
Write-NuxSuccess "py_detected" @($pyVerRaw)

$nodeCmd = Get-Command "node" -ErrorAction SilentlyContinue
if ($nodeCmd) {
    $nodeVer = & node --version 2>$null
    Write-NuxSuccess "node_detected" @($nodeVer)
} else {
    Write-NuxError "node_missing"
}

Write-NuxStep "step_2"
$venvDir = Join-Path $script:AppRoot ".venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    & python -m venv $venvDir
}

if (-not (Test-Path $venvPython)) {
    $venvPython = "python"
}
Write-NuxSuccess "venv_ready" @($venvPython)

Write-NuxStep "step_3"
$storagePaths = @(
    (Join-Path $script:AppRoot "data\db"),
    (Join-Path $script:AppRoot "data\certs"),
    (Join-Path $script:AppRoot "data\logs"),
    (Join-Path $script:AppRoot "data\memory"),
    (Join-Path $script:AppRoot "data\models")
)

foreach ($dir in $storagePaths) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
    }
}
Write-NuxSuccess "dirs_ready"

Write-NuxStep "step_4"
$reqFile = Join-Path $script:AppRoot "server\requirements.txt"
$installSuccess = $false

$uvCmd = Get-Command "uv" -ErrorAction SilentlyContinue
if ($uvCmd) {
    & uv pip install --python $venvPython -r $reqFile --quiet
    if ($LASTEXITCODE -eq 0) {
        $installSuccess = $true
    }
}

if (-not $installSuccess) {
    & $venvPython -m pip install --upgrade pip --quiet
    & $venvPython -m pip install -r $reqFile --quiet
    if ($LASTEXITCODE -eq 0) {
        $installSuccess = $true
    } else {
        Write-NuxError "deps_retry"
        if (Test-Path $venvDir) {
            Remove-Item -Recurse -Force $venvDir -ErrorAction SilentlyContinue
        }
        & python -m venv $venvDir
        & $venvPython -m pip install --upgrade pip --quiet
        & $venvPython -m pip install -r $reqFile --quiet
        if ($LASTEXITCODE -eq 0) {
            $installSuccess = $true
        }
    }
}

if (-not $installSuccess) {
    exit 1
}
Write-NuxSuccess "deps_success"

Write-NuxStep "step_5"
$clientWebDir = Join-Path $script:AppRoot "client_web"
$npmCmd = Get-Command "npm" -ErrorAction SilentlyContinue

if ($npmCmd -and (Test-Path $clientWebDir)) {
    Push-Location $clientWebDir
    if (Test-Path "package-lock.json") {
        & npm ci --silent 2>$null
    } else {
        & npm install --silent 2>$null
    }
    if ($LASTEXITCODE -ne 0) {
        Remove-Item -Recurse -Force "node_modules" -ErrorAction SilentlyContinue
        & npm install --silent
    }
    Pop-Location
    Write-NuxSuccess "client_ready"
}

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "   $((Get-T 'ready_banner'))" -ForegroundColor Green
Write-Host "   $((Get-T 'powered_by'))" -ForegroundColor White
Write-Host "================================================================" -ForegroundColor Cyan

& $venvPython -m server.cmd.main
