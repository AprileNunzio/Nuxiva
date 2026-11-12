$ErrorActionPreference = "Stop"

$script:AppRoot = $PSScriptRoot
if (-not $script:AppRoot) {
    $script:AppRoot = (Get-Location).Path
}

$script:LangDir = Join-Path $script:AppRoot "installer_wizard\language"
$script:Lang = if ($env:NUXIVA_LANG) { $env:NUXIVA_LANG.ToLowerInvariant() } else { [System.Globalization.CultureInfo]::CurrentUICulture.TwoLetterISOLanguageName.ToLowerInvariant() }
if (-not (Test-Path (Join-Path $script:LangDir "$($script:Lang).json"))) {
    $script:Lang = "en"
}

$script:Dict = @{}
$baseLangPath = Join-Path $script:LangDir "en.json"
if (Test-Path $baseLangPath) {
    $baseObj = Get-Content $baseLangPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($baseObj.dictionary) {
        foreach ($prop in $baseObj.dictionary.PSObject.Properties) {
            $script:Dict[$prop.Name] = [string]$prop.Value
        }
    }
}

$targetLangPath = Join-Path $script:LangDir "$($script:Lang).json"
if ((Test-Path $targetLangPath) -and ($targetLangPath -ne $baseLangPath)) {
    $targetObj = Get-Content $targetLangPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($targetObj.dictionary) {
        foreach ($prop in $targetObj.dictionary.PSObject.Properties) {
            $script:Dict[$prop.Name] = [string]$prop.Value
        }
    }
}

function Get-T {
    param([string]$Key, [object[]]$Args)
    $msg = $script:Dict[$Key]
    if (-not $msg) {
        $msg = $Key
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
