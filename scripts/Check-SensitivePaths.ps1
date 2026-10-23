[CmdletBinding()]
param(
    [string]$RepositoryRoot = (Split-Path -Parent $PSScriptRoot),
    [switch]$IncludeHistory
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
Import-Module (Join-Path $PSScriptRoot 'SensitivePathPolicy.psm1') -Force

try {
    $null = & git -C $RepositoryRoot rev-parse --show-toplevel 2>$null
    if ($LASTEXITCODE -ne 0) { throw 'Not a Git repository.' }

    $raw = & git -C $RepositoryRoot -c core.quotepath=false ls-files --cached -z
    if ($LASTEXITCODE -ne 0) { throw 'Could not enumerate the Git index.' }
    $paths = @(($raw -join "`n") -split "`0" | Where-Object { $_ -ne '' })

    if ($IncludeHistory) {
        $history = & git -C $RepositoryRoot -c core.quotepath=false log --all --format= --name-only -z
        if ($LASTEXITCODE -ne 0) { throw 'Could not enumerate Git history.' }
        $paths += @(($history -join "`n") -split "`0|`r?`n" | Where-Object { $_ -ne '' })
    }

    $blockedCount = @($paths | Select-Object -Unique | Where-Object {
        Test-ForbiddenSensitivePath -Path $_
    }).Count
    if ($blockedCount -gt 0) {
        # Do not print names: paths may themselves contain personal information.
        [Console]::Error.WriteLine("Blocked: $blockedCount forbidden sensitive path(s) in the index/history. No paths or contents were printed.")
        exit 1
    }
    Write-Output 'Sensitive path check passed. File contents were not scanned.'
    exit 0
}
catch {
    [Console]::Error.WriteLine('Sensitive path check could not complete. Commit/push must stop. Verify Git and repository configuration locally.')
    exit 2
}
