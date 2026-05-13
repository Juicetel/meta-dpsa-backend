<#
.SYNOPSIS
    Provisions IIS sites, app pool, ACLs, and firewall rules for the DPSA
    chatbot (FastAPI backend + Nuxt frontend) on a Windows Server.

.DESCRIPTION
    Run from an elevated PowerShell session on the target IIS host AFTER
    the package contents have been copied into place (default: C:\inetpub\dpsa).

    Layout expected on the server:
        C:\inetpub\dpsa\backend\           (contains web.config, api\, tools\, ...)
        C:\inetpub\dpsa\frontend\          (contains web.config + .output\)

    Idempotent: safe to re-run; existing objects are reused, not duplicated.

.PARAMETER DeployRoot
    Root directory containing the backend\ and frontend\ subfolders.
    Defaults to C:\inetpub\dpsa.

.PARAMETER BackendPort
    TCP port for the FastAPI site. Default 8080.

.PARAMETER FrontendPort
    TCP port for the Nuxt site. Default 80.

.PARAMETER AppPoolName
    IIS Application Pool name. Default DPSA_Chat_Pool.

.EXAMPLE
    .\setup_iis.ps1
    .\setup_iis.ps1 -DeployRoot D:\Sites\dpsa -BackendPort 8080 -FrontendPort 80
#>
[CmdletBinding()]
param(
    [string]$DeployRoot   = 'C:\inetpub\dpsa',
    [int]$BackendPort     = 8080,
    [int]$FrontendPort    = 80,
    [string]$AppPoolName  = 'DPSA_Chat_Pool',
    [string]$BackendSite  = 'DPSA_Backend',
    [string]$FrontendSite = 'DPSA_Frontend'
)

$ErrorActionPreference = 'Stop'

# -- Elevation check ---------------------------------------------------------
$currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal   = New-Object Security.Principal.WindowsPrincipal($currentUser)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'This script must be run from an elevated (Administrator) PowerShell session.'
}

Write-Host '=== DPSA Chat — IIS provisioning ===' -ForegroundColor Cyan
Write-Host "Deploy root : $DeployRoot"
Write-Host "Backend     : $BackendSite on port $BackendPort"
Write-Host "Frontend    : $FrontendSite on port $FrontendPort"
Write-Host "App pool    : $AppPoolName"
Write-Host ''

# -- Path validation ---------------------------------------------------------
$backendPath        = Join-Path $DeployRoot 'backend'
$frontendPath       = Join-Path $DeployRoot 'frontend'
$frontendPublicPath = Join-Path $frontendPath '.output\public'

foreach ($p in @($backendPath, $frontendPath)) {
    if (-not (Test-Path $p)) {
        throw "Required path not found: $p. Copy the production package here first."
    }
}
if (-not (Test-Path $frontendPublicPath)) {
    Write-Warning "Frontend .output\public not found at $frontendPublicPath. Did you run 'npx nuxi build'?"
}

# -- WebAdministration module -----------------------------------------------
Import-Module WebAdministration -ErrorAction Stop

# -- 1. Application Pool ----------------------------------------------------
Write-Host "[1/5] Ensuring application pool '$AppPoolName' (No Managed Code)..." -ForegroundColor Yellow
if (-not (Test-Path "IIS:\AppPools\$AppPoolName")) {
    New-WebAppPool -Name $AppPoolName | Out-Null
    Write-Host "      Created app pool $AppPoolName"
} else {
    Write-Host "      App pool already exists"
}
Set-ItemProperty -Path "IIS:\AppPools\$AppPoolName" -Name managedRuntimeVersion -Value ''
Set-ItemProperty -Path "IIS:\AppPools\$AppPoolName" -Name processModel.identityType -Value 'ApplicationPoolIdentity'
Set-ItemProperty -Path "IIS:\AppPools\$AppPoolName" -Name startMode -Value 'AlwaysRunning'
Set-ItemProperty -Path "IIS:\AppPools\$AppPoolName" -Name processModel.idleTimeout -Value '00:00:00'

# Helper to create or update a site bound to a specific port + physical path
function Set-DpsaSite {
    param(
        [string]$Name,
        [string]$PhysicalPath,
        [int]$Port,
        [string]$Pool
    )

    if (-not (Test-Path "IIS:\Sites\$Name")) {
        New-Website -Name $Name `
                    -PhysicalPath $PhysicalPath `
                    -Port $Port `
                    -ApplicationPool $Pool `
                    -Force | Out-Null
        Write-Host "      Created site $Name -> $PhysicalPath (port $Port)"
    } else {
        Set-ItemProperty "IIS:\Sites\$Name" -Name physicalPath -Value $PhysicalPath
        Set-ItemProperty "IIS:\Sites\$Name" -Name applicationPool -Value $Pool
        # Reset bindings to a single http binding on the requested port
        Clear-ItemProperty "IIS:\Sites\$Name" -Name bindings -ErrorAction SilentlyContinue
        New-ItemProperty "IIS:\Sites\$Name" -Name bindings `
            -Value @{ protocol = 'http'; bindingInformation = "*:${Port}:" } | Out-Null
        Write-Host "      Updated site $Name -> $PhysicalPath (port $Port)"
    }
    Start-Website -Name $Name -ErrorAction SilentlyContinue
}

# -- 2. Backend site --------------------------------------------------------
Write-Host "[2/5] Provisioning backend site..." -ForegroundColor Yellow
Set-DpsaSite -Name $BackendSite -PhysicalPath $backendPath -Port $BackendPort -Pool $AppPoolName

# -- 3. Frontend site -------------------------------------------------------
Write-Host "[3/5] Provisioning frontend site..." -ForegroundColor Yellow
# The Nitro server (Node) needs the .output folder; IIS serves
# requests by handing them off to node.exe via HttpPlatformHandler defined
# in frontend\web.config. The site's physical path is the frontend folder
# itself (which contains both web.config and .output\).
Set-DpsaSite -Name $FrontendSite -PhysicalPath $frontendPath -Port $FrontendPort -Pool $AppPoolName

# -- 4. NTFS ACLs -----------------------------------------------------------
Write-Host "[4/5] Granting IIS_IUSRS and IUSR read/execute on deploy paths..." -ForegroundColor Yellow
function Grant-IisAcl {
    param([string]$Path)
    if (-not (Test-Path $Path)) { return }
    $acl = Get-Acl $Path
    foreach ($identity in @('IIS_IUSRS', 'IUSR')) {
        try {
            $rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
                $identity,
                'ReadAndExecute,ListDirectory',
                'ContainerInherit,ObjectInherit',
                'None',
                'Allow'
            )
            $acl.SetAccessRule($rule)
        } catch {
            Write-Warning "Could not add rule for $identity on $Path : $($_.Exception.Message)"
        }
    }
    Set-Acl -Path $Path -AclObject $acl
    Write-Host "      ACLs applied: $Path"
}
Grant-IisAcl -Path $backendPath
Grant-IisAcl -Path $frontendPath

# Backend needs a writable logs/ folder for HttpPlatformHandler stdout
$backendLogs = Join-Path $backendPath 'logs'
if (-not (Test-Path $backendLogs)) { New-Item -ItemType Directory -Path $backendLogs | Out-Null }
$frontendLogs = Join-Path $frontendPath 'logs'
if (-not (Test-Path $frontendLogs)) { New-Item -ItemType Directory -Path $frontendLogs | Out-Null }
foreach ($logDir in @($backendLogs, $frontendLogs)) {
    $acl = Get-Acl $logDir
    $rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
        'IIS_IUSRS', 'Modify', 'ContainerInherit,ObjectInherit', 'None', 'Allow'
    )
    $acl.SetAccessRule($rule)
    Set-Acl -Path $logDir -AclObject $acl
}
Write-Host "      Logs dirs writable by IIS_IUSRS"

# -- 5. Firewall rules ------------------------------------------------------
Write-Host "[5/5] Adding Windows Firewall inbound rules..." -ForegroundColor Yellow
function Add-DpsaFirewallRule {
    param([string]$Name, [int]$Port)
    $existing = Get-NetFirewallRule -DisplayName $Name -ErrorAction SilentlyContinue
    if ($existing) {
        Write-Host "      Rule already present: $Name"
        return
    }
    New-NetFirewallRule -DisplayName $Name `
                       -Direction Inbound `
                       -Action Allow `
                       -Protocol TCP `
                       -LocalPort $Port `
                       -Profile Any | Out-Null
    Write-Host "      Created firewall rule: $Name (TCP $Port)"
}
Add-DpsaFirewallRule -Name "DPSA Chat — HTTP $FrontendPort"  -Port $FrontendPort
Add-DpsaFirewallRule -Name "DPSA Chat — API $BackendPort"    -Port $BackendPort

Write-Host ''
Write-Host '=== Done ===' -ForegroundColor Green
Write-Host ''
Write-Host 'Next steps:' -ForegroundColor Cyan
Write-Host '  1. Set required env vars in IIS Manager:'
Write-Host '       - For DPSA_Backend:  GROQ_API_KEY, GOOGLE_CREDENTIALS_JSON,'
Write-Host '                            AWS_SEARCH_URL, ALLOWED_ORIGINS'
Write-Host '       - For DPSA_Frontend: NUXT_SESSION_PASSWORD (>= 32 chars)'
Write-Host '     Configuration Editor -> system.webServer/httpPlatform/environmentVariables'
Write-Host '  2. iisreset, then browse to:'
Write-Host "       Frontend: http://localhost:$FrontendPort/"
Write-Host "       Backend:  http://localhost:$BackendPort/health"
