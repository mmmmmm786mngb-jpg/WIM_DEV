# -*- coding: utf-8 -*-
# Load extension NDFL_RDU from project XML into server IB, then dump to CFE.
# Usage (optional user): .\load_ndfl_rdu_to_wim_fin_and_dump_cfe.ps1 -UserName Admin -Password ""

[CmdletBinding()]
param(
    [string]$InfoBaseServer = "localhost",
    [string]$InfoBaseRef = "WIM_FIN",
    [string]$UserName,
    [string]$Password
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$ExtensionName = "NDFL_RDU"

$cfg = Get-ChildItem -LiteralPath $ProjectRoot -Recurse -Filter "Configuration.xml" -ErrorAction SilentlyContinue |
    Where-Object { $_.Directory.Name -eq $ExtensionName } | Select-Object -First 1
if (-not $cfg) {
    Write-Error "Extension folder NDFL_RDU not found under $ProjectRoot"
}
$ExtDir = $cfg.Directory.FullName
$OutCfe = Join-Path $cfg.Directory.Parent.FullName ($ExtensionName + ".cfe")

$RepoRoot = "c:\1c\Cursor_1c\WIM_DEV"
$LoadScript = Join-Path $RepoRoot ".cursor\skills\db-load-xml\scripts\db-load-xml.ps1"
$DumpScript = Join-Path $RepoRoot ".cursor\skills\db-dump-cf\scripts\db-dump-cf.ps1"

if (-not (Test-Path $ExtDir)) {
    Write-Error "Extension folder not found: $ExtDir"
}

$loadArgs = @{
    InfoBaseServer = $InfoBaseServer
    InfoBaseRef    = $InfoBaseRef
    ConfigDir      = $ExtDir
    Extension      = $ExtensionName
    Mode           = "Full"
}
if ($UserName) { $loadArgs.UserName = $UserName }
if ($Password) { $loadArgs.Password = $Password }

Write-Host "Step 1: LoadConfigFromFiles -> $InfoBaseServer\$InfoBaseRef extension $ExtensionName"
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
