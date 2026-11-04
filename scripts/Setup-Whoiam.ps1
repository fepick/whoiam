[CmdletBinding()]
param(
    [string]$PythonExecutable = '',
    [switch]$Dev,
    [switch]$CheckOnly
)

$ErrorActionPreference = 'Stop'
$repositoryRoot = Split-Path -Parent $PSScriptRoot
$environmentPython = Join-Path $repositoryRoot '.venv/Scripts/python.exe'
$pythonArguments = @()
if (Test-Path -LiteralPath $environmentPython) {
    $pythonCommand = $environmentPython
}
elseif ($PythonExecutable) {
    $pythonCommand = (Get-Command $PythonExecutable -ErrorAction Stop).Source
}
elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $pythonCommand = (Get-Command py).Source
    $pythonArguments = @('-3')
}
elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonCommand = (Get-Command python).Source
}
else {
    throw 'Install Python 3.11 or newer, then run this script again. No system settings were changed.'
}

& $pythonCommand @pythonArguments -c "import sys; print('Python', sys.version.split()[0]); sys.exit(0 if sys.version_info >= (3, 11) else 1)"
if ($LASTEXITCODE -ne 0) { throw 'Python 3.11 or newer is required.' }
if ($CheckOnly) {
    Write-Output "Project: $repositoryRoot"
    Write-Output "Virtual environment exists: $(Test-Path -LiteralPath $environmentPython)"
    Write-Output 'Check only: nothing was installed or started. No operational data or OS keys were accessed.'
    return
}

if (-not (Test-Path -LiteralPath $environmentPython)) {
    & $pythonCommand @pythonArguments -m venv (Join-Path $repositoryRoot '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the project virtual environment.' }
}
$requirements = if ($Dev) { 'requirements-dev.txt' } else { 'requirements.txt' }
& $environmentPython -m pip install -r (Join-Path $repositoryRoot $requirements)
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed. Check network access and the package index policy.' }
& $environmentPython -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Dependency verification failed.' }
Write-Output 'Setup completed. No server, operational data store, or OS key storage was opened.'
Write-Output 'Demo: .\.venv\Scripts\python.exe -m apps.server --demo=True'
Write-Output 'Local use: .\.venv\Scripts\python.exe -m apps.server'
