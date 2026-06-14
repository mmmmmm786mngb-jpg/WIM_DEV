# IMDEV-8899: build EPF from XML sources.
# Usage: powershell.exe -NoProfile -File "Scripts/build_epf_delete_plans.ps1"
# Default IB (no auth): Srvr=localhost;Ref=WIM_DU

[CmdletBinding()]
param(
    [string]$V8Path = "C:\Program Files\1cv8\8.3.27.1859\bin",
    [string]$InfoBaseServer = "localhost",
    [string]$InfoBaseRef = "WIM_DU",
    [string]$UserName = "",
    [string]$Password = ""
)

$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ProjectDir = Split-Path -Parent $PSScriptRoot
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..\..\..")).Path
$BuildScript = Join-Path $RepoRoot ".cursor\skills\epf-build\scripts\epf-build.ps1"

$EpfDir = Get-ChildItem -LiteralPath $ProjectDir -Directory -Recurse -Depth 1 -Filter "*_epf" |
    Where-Object { (Get-ChildItem -LiteralPath $_.FullName -Filter "*.xml" -ErrorAction SilentlyContinue).Count -gt 0 } |
    Select-Object -First 1

if (-not $EpfDir) {
    Write-Host "ERROR: no *_epf folder with xml under $ProjectDir" -ForegroundColor Red
    exit 1
}

$SourceFile = Get-ChildItem -LiteralPath $EpfDir.FullName -Filter "*.xml" | Select-Object -First 1 -ExpandProperty FullName
$BaseName = [System.IO.Path]::GetFileNameWithoutExtension($SourceFile)
$OutputFile = Join-Path $EpfDir.FullName ($BaseName + ".epf")

if (-not (Test-Path -LiteralPath $BuildScript)) {
    Write-Host "ERROR: epf-build.ps1 not found: $BuildScript" -ForegroundColor Red
    exit 1
}

Write-Host "Database: $InfoBaseServer/$InfoBaseRef"
Write-Host "Source:   $SourceFile"
Write-Host "Output:   $OutputFile"
Write-Host ""

$buildArgs = @(
    "-NoProfile",
    "-File", $BuildScript,
    "-V8Path", $V8Path,
    "-InfoBaseServer", $InfoBaseServer,
    "-InfoBaseRef", $InfoBaseRef,
    "-SourceFile", $SourceFile,
    "-OutputFile", $OutputFile
)
if ($UserName) {
    $buildArgs += "-UserName"
    $buildArgs += $UserName
}
if ($Password) {
    $buildArgs += "-Password"
    $buildArgs += $Password
}

& powershell.exe @buildArgs
exit $LASTEXITCODE
