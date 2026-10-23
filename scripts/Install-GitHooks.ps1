[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$repositoryRoot = Split-Path -Parent $PSScriptRoot
$null = & git -C $repositoryRoot rev-parse --show-toplevel 2>$null
if ($LASTEXITCODE -ne 0) { throw 'Initialize the Git repository before installing hooks.' }

$currentHooksPath = & git -C $repositoryRoot config --local --get core.hooksPath
if ($LASTEXITCODE -notin @(0, 1)) { throw 'Could not read the local hooks configuration.' }
if ($currentHooksPath -and $currentHooksPath -ne '.githooks') {
    throw 'A different hooksPath is configured. Integrate the checks into the existing hooks before changing it.'
}

if ($env:OS -ne 'Windows_NT') {
    & chmod +x -- (Join-Path $repositoryRoot '.githooks/pre-commit') (Join-Path $repositoryRoot '.githooks/pre-push')
    if ($LASTEXITCODE -ne 0) { throw 'Could not make Git hooks executable.' }
}

& git -C $repositoryRoot config --local core.hooksPath .githooks
if ($LASTEXITCODE -ne 0) { throw 'Could not install the local hooks.' }
Write-Output 'Local pre-commit and pre-push path checks installed. These do not scan file contents.'
