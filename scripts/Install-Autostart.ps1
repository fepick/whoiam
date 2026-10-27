[CmdletBinding()]
param(
    [ValidateSet('production', 'development')][string]$Profile = 'production',
    [ValidateRange(1024, 65535)][int]$Port = 4173,
    [string]$DataHome = '',
    [switch]$Remove,
    [switch]$Preview,
    [switch]$Status
)

$ErrorActionPreference = 'Stop'
if ($env:OS -ne 'Windows_NT') { throw 'Windows Task Scheduler is required.' }
$repositoryRoot = Split-Path -Parent $PSScriptRoot
$launcher = Join-Path $PSScriptRoot 'Start-Whoiam.ps1'
$pythonExecutable = Join-Path $repositoryRoot '.venv/Scripts/python.exe'
if (-not $Remove -and -not $Status -and -not (Test-Path -LiteralPath $pythonExecutable)) {
    throw 'Prepare .venv and install requirements.txt before registering startup.'
}
if ($DataHome -and -not [IO.Path]::IsPathRooted($DataHome)) { throw 'DataHome must be absolute.' }
if ($DataHome -match '["\r\n]') { throw 'DataHome contains unsupported characters.' }
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$sid = $identity.User.Value
$taskName = "Whoiam-$Profile-$sid"
$description = "Whoiam personal runtime; profile=$Profile"

function Quote-TaskArgument {
    param([string]$Value)
    $escaped = [regex]::Replace($Value, '(\\*)"', '$1$1\"')
    $escaped = [regex]::Replace($escaped, '(\\+)$', '$1$1')
    return '"' + $escaped + '"'
}

$taskArguments = @('-NoProfile', '-NonInteractive', '-WindowStyle', 'Hidden', '-File', $launcher, '-Profile', $Profile, '-Port', [string]$Port)
if ($DataHome) { $taskArguments += @('-DataHome', $DataHome) }
$arguments = ($taskArguments | ForEach-Object { Quote-TaskArgument $_ }) -join ' '
if ($Preview) {
    Write-Output "Validated startup definition: profile=$Profile; port=$Port; current user at logon; limited privileges; hidden launcher. No task was changed."
    exit 0
}
$existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existing -and $existing.Description -ne $description) { throw 'Refusing to replace an unrelated task.' }
if ($Status) {
    @{enabled=[bool]($existing -and $existing.State -ne 'Disabled')} | ConvertTo-Json -Compress
    exit 0
}
if ($Remove) {
    if ($existing) {
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    }
    Write-Output 'Whoiam startup registration removed. Data and keys were not deleted.'
    exit 0
}
$shellPath = Join-Path $env:SystemRoot 'System32/WindowsPowerShell/v1.0/powershell.exe'
$action = New-ScheduledTaskAction -Execute $shellPath -Argument $arguments -WorkingDirectory $repositoryRoot
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $sid
$principal = New-ScheduledTaskPrincipal -UserId $sid -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$null = Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description $description -Force
Write-Output 'Whoiam will start at the current user logon. No password or administrator privilege was stored. The running app was not started or unlocked.'
