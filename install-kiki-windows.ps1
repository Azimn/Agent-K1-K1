param(
    [switch]$EnableAutonomy,
    [switch]$NoChat
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

function Write-Step([string]$Message) {
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Stop-WithHelp([string]$Message) {
    Write-Host ""
    Write-Host "Kiki installation stopped." -ForegroundColor Red
    Write-Host $Message -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Nothing in your existing Hermes data was intentionally deleted."
    exit 1
}

if ($env:OS -ne "Windows_NT") {
    Stop-WithHelp "This installer is for native Windows 10 or Windows 11."
}

$HermesHome = Join-Path $env:LOCALAPPDATA "hermes"
$HermesExe = Join-Path $HermesHome "bin\hermes.exe"
$KikiRoot = Join-Path $env:LOCALAPPDATA "K1-K1"
$SourceRoot = Join-Path $KikiRoot "source"
$StagingRoot = Join-Path $KikiRoot "staging"
$ZipPath = Join-Path $KikiRoot "Agent-K1-K1.zip"
$KikiBranch = "feat/k1k1-v0.1"
$KikiZipUrl = "https://github.com/Azimn/Agent-K1-K1/archive/refs/heads/$KikiBranch.zip"
$HermesInstallerUrl = "https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.ps1"

New-Item -ItemType Directory -Force -Path $KikiRoot | Out-Null

Write-Host ""
Write-Host "K1-K1 Windows Installer" -ForegroundColor Magenta
Write-Host "This will install Hermes Agent if needed, create an isolated agent-k1k1 profile, and keep Kiki separate from Pretorius."

if (-not (Test-Path $HermesExe)) {
    Write-Step "Hermes Agent is not installed. Installing the official native Windows build."
    Write-Host "Hermes will open its normal setup wizard once so you can choose a model/provider."
    try {
        $HermesInstaller = Invoke-RestMethod -Uri $HermesInstallerUrl
        Invoke-Expression $HermesInstaller
    }
    catch {
        Stop-WithHelp "The official Hermes installer failed: $($_.Exception.Message)"
    }
}

if (-not (Test-Path $HermesExe)) {
    Stop-WithHelp "Hermes did not appear at $HermesExe. Close PowerShell, open it again, and rerun this installer."
}

$env:HERMES_HOME = $HermesHome
$env:Path = "$(Join-Path $HermesHome 'bin');$env:Path"

Write-Step "Checking Hermes."
& $HermesExe --version
if ($LASTEXITCODE -ne 0) {
    Stop-WithHelp "Hermes is installed but did not start correctly."
}

$DefaultConfig = Join-Path $HermesHome "config.yaml"
if (-not (Test-Path $DefaultConfig)) {
    Write-Step "Hermes has not been configured yet. Starting the Hermes setup wizard."
    & $HermesExe setup
    if ($LASTEXITCODE -ne 0) {
        Stop-WithHelp "Hermes setup did not finish successfully."
    }
}

Write-Step "Downloading the Kiki v0.1 candidate."
try {
    Invoke-WebRequest -Uri $KikiZipUrl -OutFile $ZipPath
}
catch {
    Stop-WithHelp "Could not download Agent K1-K1 from GitHub: $($_.Exception.Message)"
}

if (Test-Path $StagingRoot) {
    Remove-Item -Recurse -Force $StagingRoot
}
New-Item -ItemType Directory -Force -Path $StagingRoot | Out-Null

Write-Step "Preparing Kiki's source package."
try {
    Expand-Archive -Path $ZipPath -DestinationPath $StagingRoot -Force
}
catch {
    Stop-WithHelp "The Kiki archive could not be extracted: $($_.Exception.Message)"
}

$Extracted = Get-ChildItem -Path $StagingRoot -Directory | Select-Object -First 1
if (-not $Extracted) {
    Stop-WithHelp "The downloaded Kiki archive did not contain the expected source folder."
}

if (Test-Path $SourceRoot) {
    Remove-Item -Recurse -Force $SourceRoot
}
New-Item -ItemType Directory -Force -Path $SourceRoot | Out-Null
Copy-Item -Path (Join-Path $Extracted.FullName "*") -Destination $SourceRoot -Recurse -Force

$PythonCandidates = @(
    (Join-Path $HermesHome "hermes-agent\venv\Scripts\python.exe"),
    (Join-Path $HermesHome "hermes-agent\.venv\Scripts\python.exe")
)
$PythonExe = $null
foreach ($Candidate in $PythonCandidates) {
    if (Test-Path $Candidate) {
        $PythonExe = $Candidate
        break
    }
}
if (-not $PythonExe) {
    $PythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($PythonCommand) {
        $PythonExe = $PythonCommand.Source
    }
}
if (-not $PythonExe) {
    Stop-WithHelp "Hermes is installed, but its Python interpreter could not be located."
}

Write-Step "Running Kiki readiness checks."
Push-Location $SourceRoot
try {
    & $PythonExe "scripts\readiness.py"
    if ($LASTEXITCODE -ne 0) {
        Stop-WithHelp "Kiki's readiness check failed. Please copy the output above into ChatGPT so it can be fixed."
    }

    Write-Step "Running Kiki's local regression tests."
    & $PythonExe -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) {
        Stop-WithHelp "Kiki's tests failed. Please copy the output above into ChatGPT so it can be fixed."
    }

    Write-Step "Installing Kiki as an isolated Hermes profile."
    & $PythonExe "scripts\install.py" --source $SourceRoot --profile "agent-k1k1" --replace-existing --skip-activation
    if ($LASTEXITCODE -ne 0) {
        Stop-WithHelp "The isolated Kiki profile could not be installed."
    }
}
finally {
    Pop-Location
}

Write-Step "Checking the installed Kiki profile."
& $HermesExe profile info agent-k1k1
if ($LASTEXITCODE -ne 0) {
    Stop-WithHelp "Kiki was copied, but Hermes could not read the agent-k1k1 profile."
}

Write-Host ""
Write-Host "Kiki is installed." -ForegroundColor Green
Write-Host "Profile: agent-k1k1"
Write-Host "Persistent Hermes data: $HermesHome"
Write-Host "Kiki distribution source: $SourceRoot"
Write-Host ""
Write-Host "Background autonomy is OFF by default so the first test cannot spend model credits while unattended."

$ShouldEnable = $EnableAutonomy
if (-not $EnableAutonomy) {
    $Answer = Read-Host "Enable Kiki's hourly pulse, nightly reflection, daily brief, and login gateway now? Type Y to enable, or press Enter to leave them off"
    $ShouldEnable = ($Answer -match "^[Yy]")
}

if ($ShouldEnable) {
    Write-Step "Enabling Kiki's bounded background routines and gateway."
    $InstalledProfile = Join-Path $HermesHome "profiles\agent-k1k1"
    $ActivateScript = Join-Path $InstalledProfile "scripts\activate.py"
    if (-not (Test-Path $ActivateScript)) {
        Stop-WithHelp "Kiki is installed, but the activation script is missing at $ActivateScript."
    }
    & $PythonExe $ActivateScript --profile "agent-k1k1" --deliver "local" --install-gateway
    if ($LASTEXITCODE -ne 0) {
        Stop-WithHelp "Kiki is installed, but background autonomy could not be enabled."
    }
    Write-Host "Background autonomy is enabled." -ForegroundColor Green
}
else {
    Write-Host "Background autonomy remains off. You can enable it later." -ForegroundColor DarkYellow
}

if (-not $NoChat) {
    $StartAnswer = Read-Host "Start your first chat with Kiki now? Press Enter for yes, or type N"
    if ($StartAnswer -notmatch "^[Nn]") {
        Write-Step "Starting Kiki."
        & $HermesExe -p agent-k1k1 chat
    }
}

Write-Host ""
Write-Host "To start Kiki later, run:"
Write-Host "  hermes -p agent-k1k1 chat" -ForegroundColor White
Write-Host ""
Write-Host "To check her profile:"
Write-Host "  hermes profile info agent-k1k1" -ForegroundColor White
Write-Host ""
