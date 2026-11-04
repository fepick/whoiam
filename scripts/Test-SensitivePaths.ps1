$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
Import-Module (Join-Path $PSScriptRoot 'SensitivePathPolicy.psm1') -Force

$blocked = @(
    '.private/vault/fake.json', 'apps/web/.private/fake.txt', '.PRIVATE/vault/fake.json',
    'data/fake.json', 'nested/backups/fake.bin', 'uploads/fake.pdf', 'sessions/fake.json',
    '.env', '.env.local', 'apps/api/.env.production', '.env.EXAMPLE', 'fake.pem', 'fake.pfx',
    'fake.key', 'id_ed25519', 'database.db', 'database.sqlite3-wal', 'fake.har', 'fake.zip',
    'fake.dump', 'export.sql', '.\credentials\fake.json', 'fake.whoiam-recovery'
)
$allowed = @(
    'README.md', 'docs/security.md', 'packages/modules/sensitive/README.md',
    'packages/modules/purchasing/domain/order.ts', '.env.example',
    'apps/api/.env.example', 'docs/data-model.md', 'infra/database/migrations/0001_initial.sql'
)
foreach ($path in $blocked) {
    if (-not (Test-ForbiddenSensitivePath $path)) { throw 'A forbidden fixture path was accepted.' }
}
foreach ($path in $allowed) {
    if (Test-ForbiddenSensitivePath $path) { throw 'A safe fixture path was rejected.' }
}

# Integration fixtures contain no real personal information or credentials.
$repositoryRoot = Split-Path -Parent $PSScriptRoot
$tempBase = Join-Path $repositoryRoot '.tmp'
$testRoot = Join-Path $tempBase ('policy-tests-' + [Guid]::NewGuid().ToString('N'))
$shellExecutable = (Get-Process -Id $PID).Path
$checker = Join-Path $PSScriptRoot 'Check-SensitivePaths.ps1'

function Assert-GitSuccess {
    if ($LASTEXITCODE -ne 0) { throw 'A fixture Git operation failed.' }
}

function Invoke-FixtureCheck {
    param([switch]$IncludeHistory)
    $arguments = @('-NoProfile', '-File', $checker, '-RepositoryRoot', $testRoot)
    if ($IncludeHistory) { $arguments += '-IncludeHistory' }
    $previousPreference = $ErrorActionPreference
    try {
        # Windows PowerShell emits native stderr as ErrorRecords. Expected
        # checker failures must be evaluated by exit code, without logging it.
        $ErrorActionPreference = 'Continue'
        $null = & $shellExecutable @arguments 2>&1
        return $LASTEXITCODE
    }
    finally { $ErrorActionPreference = $previousPreference }
}

try {
    $null = New-Item -ItemType Directory -Path $testRoot -Force
    & git init --quiet $testRoot
    Assert-GitSuccess
    Copy-Item -LiteralPath (Join-Path $repositoryRoot '.gitignore') -Destination $testRoot
    Set-Content -LiteralPath (Join-Path $testRoot 'safe.txt') -Value 'synthetic fixture only'
    & git -C $testRoot add -- safe.txt
    Assert-GitSuccess
    if ((Invoke-FixtureCheck -IncludeHistory) -ne 0) { throw 'A clean index/unborn history was rejected.' }

    # The guard is case-insensitive on every OS; Git ignore matching is not.
    # Case-variant fixtures above exercise the guard, not portable ignore rules.
    foreach ($path in $blocked | Where-Object {
        $_ -cne '.env.EXAMPLE' -and $_ -cne '.PRIVATE/vault/fake.json' -and $_ -notlike '.\*'
    }) {
        $null = & git -C $testRoot check-ignore -- $path
        if ($LASTEXITCODE -ne 0) { throw 'A forbidden fixture path was not ignored by Git.' }
    }
    foreach ($path in $allowed) {
        $null = & git -C $testRoot check-ignore -- $path
        if ($LASTEXITCODE -ne 1) { throw 'A safe fixture path was unexpectedly ignored by Git.' }
    }

    # Force-add only a synthetic ignored fixture inside the isolated test repo.
    $null = New-Item -ItemType Directory -Path (Join-Path $testRoot '.private')
    Set-Content -LiteralPath (Join-Path $testRoot '.private/fake.txt') -Value 'synthetic fixture only'
    & git -C $testRoot add -f -- .private/fake.txt
    Assert-GitSuccess
    if ((Invoke-FixtureCheck) -ne 1) { throw 'A force-added forbidden fixture was not blocked.' }

    & git -C $testRoot -c user.name='Policy Test' -c user.email='policy@example.invalid' -c commit.gpgsign=false commit --quiet -m 'Synthetic policy fixture'
    Assert-GitSuccess
    & git -C $testRoot rm --quiet --cached -- .private/fake.txt
    Assert-GitSuccess
    & git -C $testRoot -c user.name='Policy Test' -c user.email='policy@example.invalid' -c commit.gpgsign=false commit --quiet -m 'Remove synthetic fixture from index'
    Assert-GitSuccess
    if ((Invoke-FixtureCheck) -ne 0) { throw 'A clean index was rejected.' }
    if ((Invoke-FixtureCheck -IncludeHistory) -ne 1) { throw 'A forbidden historical fixture was not blocked.' }

    Write-Output "Passed: $($blocked.Count) forbidden and $($allowed.Count) allowed paths, Git ignore checks, forced-index rejection, and historical-path rejection."
}
finally {
    if (Test-Path -LiteralPath $testRoot) {
        # Verify the resolved recursive-delete target remains in this test workspace.
        $resolvedTarget = (Resolve-Path -LiteralPath $testRoot).Path
        $resolvedBase = (Resolve-Path -LiteralPath $tempBase).Path.TrimEnd('\', '/') + [IO.Path]::DirectorySeparatorChar
        if (-not $resolvedTarget.StartsWith($resolvedBase, [StringComparison]::OrdinalIgnoreCase) -or
            (Split-Path -Leaf $resolvedTarget) -notlike 'policy-tests-*') {
            throw 'Refusing to remove a fixture outside the verified test directory.'
        }
        Remove-Item -LiteralPath $resolvedTarget -Recurse -Force
    }
}

# Expected rejection checks leave a native exit code of 1. Report the overall
# successful test result explicitly so the GitHub Actions pwsh wrapper agrees.
exit 0
