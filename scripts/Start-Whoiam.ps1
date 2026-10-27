[CmdletBinding()]
param(
    [switch]$Demo,
    [ValidateRange(1024, 65535)][int]$Port = 4173
)

$ErrorActionPreference = 'Stop'
$repositoryRoot = Split-Path -Parent $PSScriptRoot
$pythonExecutable = Join-Path $repositoryRoot '.venv/Scripts/python.exe'
Push-Location -LiteralPath $repositoryRoot
try {
    $arguments = @('-m', 'apps.server', "--demo=$($Demo.IsPresent)", "--port=$Port")
    if (Test-Path -LiteralPath $pythonExecutable) {
        & $pythonExecutable @arguments
    }
    elseif (Get-Command conda -ErrorAction SilentlyContinue) {
        & conda run --no-capture-output -n rpi python @arguments
    }
    else {
        & python @arguments
    }
    if ($LASTEXITCODE -ne 0) { throw 'Whoiam did not start. Check the Python environment and requirements.txt.' }
}
finally { Pop-Location }
