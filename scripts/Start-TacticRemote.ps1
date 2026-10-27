[CmdletBinding()]
param(
    [string]$TacticExecutable = '',
    [string]$CodexExecutable = '',
    [switch]$Preview
)

$ErrorActionPreference = 'Stop'
if ($env:OS -ne 'Windows_NT') { throw 'This launcher requires Windows.' }
$repositoryRoot = Split-Path -Parent $PSScriptRoot

if (-not $TacticExecutable) {
    $TacticExecutable = Join-Path $env:LOCALAPPDATA 'Programs/Tactic Remote/Tactic Remote.exe'
}
if (-not (Test-Path -LiteralPath $TacticExecutable -PathType Leaf)) {
    throw 'Install the official Tactic Remote Windows companion or specify -TacticExecutable.'
}

if (-not $CodexExecutable) {
    # IDE가 추가한 임시 PATH보다 독립 설치본의 고정 진입 경로를 우선한다.
    $standaloneCodex = Join-Path $env:LOCALAPPDATA 'Programs/OpenAI/Codex/bin/codex.exe'
    if (Test-Path -LiteralPath $standaloneCodex -PathType Leaf) {
        $CodexExecutable = $standaloneCodex
    }
    else {
        $codexCommand = Get-Command codex.exe -ErrorAction SilentlyContinue
        if ($codexCommand) { $CodexExecutable = $codexCommand.Source }
    }
    if (-not $CodexExecutable) {
        # VS Code 확장 버전이 바뀌어도 실행 파일을 다시 찾는다. 인증 파일은 열지 않는다.
        $extensionRoot = Join-Path $env:USERPROFILE '.vscode/extensions'
        if (Test-Path -LiteralPath $extensionRoot -PathType Container) {
            $extensions = Get-ChildItem -LiteralPath $extensionRoot -Directory |
                Where-Object Name -Like 'openai.chatgpt-*-win32-x64' |
                Sort-Object LastWriteTimeUtc -Descending
            foreach ($extension in $extensions) {
                $candidate = Join-Path $extension.FullName 'bin/windows-x86_64/codex.exe'
                if (Test-Path -LiteralPath $candidate -PathType Leaf) {
                    $CodexExecutable = $candidate
                    break
                }
            }
        }
    }
}
if (-not $CodexExecutable -or -not (Test-Path -LiteralPath $CodexExecutable -PathType Leaf)) {
    throw 'Install Codex CLI or the VS Code Codex extension, or specify -CodexExecutable.'
}

$tacticPath = (Resolve-Path -LiteralPath $TacticExecutable).Path
$codexPath = (Resolve-Path -LiteralPath $CodexExecutable).Path
$toolDirectories = @((Split-Path -Parent $codexPath))
$pythonTools = Join-Path $repositoryRoot '.venv/Scripts'
if (Test-Path -LiteralPath $pythonTools -PathType Container) { $toolDirectories += $pythonTools }
$bundledPowerShell = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell'
if (-not (Get-Command pwsh -ErrorAction SilentlyContinue) -and
    (Test-Path -LiteralPath (Join-Path $bundledPowerShell 'pwsh.exe') -PathType Leaf)) {
    $toolDirectories += $bundledPowerShell
}

if ($Preview) {
    Write-Output "Tactic Remote: $tacticPath"
    Write-Output "Codex: $codexPath"
    Write-Output "Select this project in Tactic Remote: $repositoryRoot"
    Write-Output 'If the companion is already running, fully quit it before launching with this environment.'
    Write-Output 'Preview only. No app, account, network, or persistent environment settings were changed.'
    return
}

# 이 앱의 자식 프로세스에만 도구 경로를 전달하고 호출한 셸의 환경은 복구한다.
$previousPath = $env:PATH
$previousPreCommitHome = $env:PRE_COMMIT_HOME
try {
    $env:PATH = ($toolDirectories -join ';') + ';' + $previousPath
    if (-not $previousPreCommitHome) {
        $env:PRE_COMMIT_HOME = Join-Path $repositoryRoot '.tmp/pre-commit-cache'
    }
    Start-Process -FilePath $tacticPath -WorkingDirectory $repositoryRoot -WindowStyle Normal
}
finally {
    $env:PATH = $previousPath
    $env:PRE_COMMIT_HOME = $previousPreCommitHome
}
Write-Output 'Tactic Remote launched. Select the project folder and Codex in the companion/mobile app.'
