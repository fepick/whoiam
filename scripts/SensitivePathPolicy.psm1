Set-StrictMode -Version Latest

function Test-ForbiddenSensitivePath {
    [CmdletBinding()]
    param([Parameter(Mandatory = $true)][string]$Path)

    $normalized = $Path.Replace('\', '/') -replace '^(\./)+', ''
    if ($normalized -match '(?i)(^|/)(\.private|data|secrets|credentials|uploads|receipts|backups|exports|logs|sessions|browser-profiles|storage-state)(/|$)') {
        return $true
    }
    $name = ($normalized -split '/')[-1]
    if ($name -match '(?i)^\.env($|\.)' -and $name -cne '.env.example') {
        return $true
    }
    if ($name -match '(?i)^(id_rsa|id_ed25519)$') {
        return $true
    }
    if ($name -match '(?i)\.(pem|key|p12|pfx|keystore|jks|whoiam-recovery|db|sqlite|sqlite3|log|har|bak|dump|zip|7z|tar|gz)$' -or
        $name -match '(?i)\.(db|sqlite|sqlite3)-.+$') {
        return $true
    }
    if ($name -match '(?i)\.sql$' -and $normalized -cnotmatch '^infra/database/migrations/[^/]+\.sql$') {
        return $true
    }
    return $false
}

Export-ModuleMember -Function Test-ForbiddenSensitivePath
