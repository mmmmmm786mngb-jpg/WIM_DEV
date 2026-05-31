# -*- coding: utf-8 -*-
# IMDEV-8899: validate rev2 extension, load XML into WIM_DU, update extension DB, dump CFE.
# Usage: .\load_rev2_to_wim_du_and_dump_cfe.ps1
# With 1C user: .\load_rev2_to_wim_du_and_dump_cfe.ps1 -UserName Admin -Password "..."
# Without IB auth (default): omit -UserName / -Password -> Srvr=localhost;Ref=WIM_DU

[CmdletBinding()]
param(
    [string]$InfoBaseServer = "localhost",
    [string]$InfoBaseRef = "WIM_DU",
    [string]$UserName,
    [string]$Password,
    [switch]$SkipValidate
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$ExtensionName = "rev2"

$cfg = Get-ChildItem -LiteralPath $ProjectRoot -Recurse -Filter "Configuration.xml" -ErrorAction SilentlyContinue |
    Where-Object { $_.Directory.Name -eq $ExtensionName } | Select-Object -First 1
if (-not $cfg) {
    Write-Error "Extension folder $ExtensionName not found under $ProjectRoot"
}
$ExtDir = $cfg.Directory.FullName
$OutCfe = Join-Path $cfg.Directory.Parent.FullName ($ExtensionName + ".cfe")

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..\..\..")).Path
$ValidateScript = Join-Path $RepoRoot ".cursor\skills\cfe-validate\scripts\cfe-validate.ps1"
$LoadScript = Join-Path $RepoRoot ".cursor\skills\db-load-xml\scripts\db-load-xml.ps1"
$DumpScript = Join-Path $RepoRoot ".cursor\skills\db-dump-cf\scripts\db-dump-cf.ps1"

if (-not (Test-Path $ExtDir)) {
    Write-Error "Extension folder not found: $ExtDir"
}

if (-not $SkipValidate) {
    Write-Host "Step 0: cfe-validate -> $ExtDir"
    & $ValidateScript -ExtensionPath $ExtDir
    if ($LASTEXITCODE -ne 0) {
        Write-Error "cfe-validate failed with exit $LASTEXITCODE"
    }
}

$loadArgs = @{
    InfoBaseServer = $InfoBaseServer
    InfoBaseRef    = $InfoBaseRef
    ConfigDir      = $ExtDir
    Extension      = $ExtensionName
    Mode           = "Full"
    UpdateDB       = $true
}
if ($UserName) { $loadArgs.UserName = $UserName }
if ($Password) { $loadArgs.Password = $Password }

Write-Host "Step 1: LoadConfigFromFiles + UpdateDBCfg -> $InfoBaseServer\$InfoBaseRef extension $ExtensionName"
& $LoadScript @loadArgs
if ($LASTEXITCODE -ne 0) {
    Write-Error "db-load-xml failed with exit $LASTEXITCODE"
}

$dumpArgs = @{
    InfoBaseServer = $InfoBaseServer
    InfoBaseRef    = $InfoBaseRef
    OutputFile     = $OutCfe
    Extension      = $ExtensionName
}
if ($UserName) { $dumpArgs.UserName = $UserName }
if ($Password) { $dumpArgs.Password = $Password }

Write-Host "Step 2: DumpCfg -> $OutCfe"
& $DumpScript @dumpArgs
if ($LASTEXITCODE -ne 0) {
    Write-Error "db-dump-cf failed with exit $LASTEXITCODE"
}

Write-Host "OK: $OutCfe"
exit 0
