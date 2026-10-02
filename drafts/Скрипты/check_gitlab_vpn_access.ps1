#Requires -Version 5.1
<#
.SYNOPSIS
    Proverka dostupa k korporativnomu GitLab cherez DNS tekuschego VPN.

.DESCRIPTION
    Skript beret DNS-servery podnyatyh adapterov (Check Point, tun i prochie),
    sprashivaet imya hosta bez DNS-suffiksa i, esli adres est, proveryaet port 443
    i git ls-remote.

.EXAMPLE
    .\check_gitlab_vpn_access.ps1
    .\check_gitlab_vpn_access.ps1 -RepoUrl "https://git.corp.vtbcapital.internal/wiminvest/ent1s/front/fo.git"
#>
param(
    [string]$RepoUrl = "https://git.corp.vtbcapital.internal/wiminvest/ent1s/front/fo.git"
)

$ErrorActionPreference = "Continue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

function Write-Step {
    param([string]$Text)
    Write-Host ""
    Write-Host ("== " + $Text)
}

try {
    $Uri = [Uri]$RepoUrl
}
catch {
    Write-Host ("ERROR: nekorrektnyy URL: " + $RepoUrl)
    exit 2
}

$HostName = $Uri.Host
$FqdnQuery = $HostName.TrimEnd(".") + "."

Write-Step "Cel"
Write-Host ("URL:  " + $RepoUrl)
Write-Host ("Host: " + $HostName)

Write-Step "Adaptery"
$UpAdapters = @(Get-NetAdapter -ErrorAction SilentlyContinue | Where-Object { $_.Status -eq "Up" })
if ($UpAdapters.Count -eq 0) {
    Write-Host "ERROR: net podnyatyh setevyh adapterov"
    exit 2
}

foreach ($Adapter in $UpAdapters) {
    Write-Host ("UP  " + $Adapter.Name + " | " + $Adapter.InterfaceDescription)
}

Write-Step "DNS"
$DnsRows = @(Get-DnsClientServerAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object { $_.ServerAddresses -and $_.ServerAddresses.Count -gt 0 })

$DnsServers = New-Object System.Collections.Generic.List[string]
foreach ($Row in $DnsRows) {
    $Joined = ($Row.ServerAddresses -join ", ")
    Write-Host ($Row.InterfaceAlias + " -> " + $Joined)
    foreach ($Server in $Row.ServerAddresses) {
        if (-not $DnsServers.Contains($Server)) {
            $DnsServers.Add($Server)
        }
    }
}

if ($DnsServers.Count -eq 0) {
    Write-Host "ERROR: DNS-servery ne naydeny"
    exit 2
}

Write-Step ("Razreshenie " + $FqdnQuery + " (bez search-suffiksa)")
$Addresses = New-Object System.Collections.Generic.List[string]

foreach ($Dns in $DnsServers) {
    Write-Host ("DNS " + $Dns)
    try {
        $Answers = @(Resolve-DnsName -Name $FqdnQuery -Server $Dns -DnsOnly -Type A -ErrorAction Stop |
            Where-Object { $_.Type -eq "A" -and $_.IPAddress })
        if ($Answers.Count -eq 0) {
            Write-Host "  net A-zapisi"
            continue
        }
        foreach ($Answer in $Answers) {
            Write-Host ("  A " + $Answer.IPAddress)
            if (-not $Addresses.Contains($Answer.IPAddress)) {
                $Addresses.Add($Answer.IPAddress)
            }
        }
    }
    catch {
        $Message = $_.Exception.Message
        if ($Message -match "DNS name does not exist|Non-existent|NXDOMAIN|9003") {
            Write-Host "  NXDOMAIN: imeni net v etoy zone"
        }
        else {
            Write-Host ("  ERROR: " + $Message)
        }
    }
}

if ($Addresses.Count -eq 0) {
    Write-Host ""
    Write-Host "RESULT: host ne rezolvitsya ni na odnom DNS podnyatyh adapterov."
    Write-Host "VPN-adapter mozhet byt vklyuchen, no zapisi git v zone net, libo nuzhen drugoy DNS."
    exit 1
}

Write-Step "TCP 443"
$Reachable = New-Object System.Collections.Generic.List[string]
foreach ($Ip in $Addresses) {
    $Tcp = Test-NetConnection -ComputerName $Ip -Port 443 -WarningAction SilentlyContinue
    if ($Tcp.TcpTestSucceeded) {
        Write-Host ("OK   " + $Ip + ":443")
        $Reachable.Add($Ip)
    }
    else {
        Write-Host ("FAIL " + $Ip + ":443")
    }
}

if ($Reachable.Count -eq 0) {
    Write-Host ""
    Write-Host "RESULT: imya razreshilos, no port 443 nedostupen."
    exit 1
}

Write-Step "git ls-remote"
$Git = Get-Command git -ErrorAction SilentlyContinue
if (-not $Git) {
    Write-Host "ERROR: git ne nayden v PATH"
    exit 2
}

& git ls-remote $RepoUrl HEAD
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "RESULT: host dostupen po 443, no git ls-remote zavershilsya s oshibkoy."
    Write-Host "Chasto eto uchetnaya zapis, sertifikat ili otsutstvie prava na repo."
    exit 1
}

Write-Host ""
Write-Host "RESULT: dostup k repo est, HEAD prochitan."
exit 0
