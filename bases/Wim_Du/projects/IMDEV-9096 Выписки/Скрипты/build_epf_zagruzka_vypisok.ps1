# IMDEV-9096: build EPF внЗагрузкаВыписокДУ from erf_Оптимизация_Тест1 XML sources.
# Usage: powershell.exe -NoProfile -File "Скрипты/build_epf_zagruzka_vypisok.ps1"
# Default IB (no auth): Srvr="localhost";Ref="WIM_Du"

[CmdletBinding()]
param(
    [string]$V8Path = "C:\Program Files\1cv8\8.3.27.1859\bin",
    [string]$InfoBaseServer = "localhost",
    [string]$InfoBaseRef = "WIM_Du",
    [string]$UserName = "",
    [string]$Password = "",
    [ValidateSet("erf_Оптимизация_Тест1", "erf_Оптимизация")]
    [string]$Variant = "erf_Оптимизация_Тест1"
)

$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ProjectDir = Split-Path -Parent $PSScriptRoot
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..\..\..")).Path
$BuildScript = Join-Path $RepoRoot ".cursor\skills\epf-build\scripts\epf-build.ps1"

$EpfRoot = Join-Path $ProjectDir "$Variant\внЗагрузкаВыписокДУ_epf"
$SourceFile = Join-Path $EpfRoot "внЗагрузкаВыписокДУ.xml"
$OutputFile = Join-Path $ProjectDir "$Variant\внЗагрузкаВыписокДУ.epf"

if (-not (Test-Path -LiteralPath $SourceFile)) {
    Write-Host "ERROR: source xml not found: $SourceFile" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path -LiteralPath $BuildScript)) {
    Write-Host "ERROR: epf-build.ps1 not found: $BuildScript" -ForegroundColor Red
    exit 1
}

Write-Host "Database: $InfoBaseServer/$InfoBaseRef (no auth)"
Write-Host "Variant:  $Variant"
Write-Host "Source:   $SourceFile"
Write-Host "Output:   $OutputFile"

$args = @(
    "-NoProfile",
    "-File", $BuildScript,
    "-V8Path", $V8Path,
    "-InfoBaseServer", $InfoBaseServer,
    "-InfoBaseRef", $InfoBaseRef,
    "-SourceFile", $SourceFile,
    "-OutputFile", $OutputFile
)

if ($UserName) {
    $args += "-UserName", $UserName
    if ($Password) { $args += "-Password", $Password }
}

& powershell.exe @args
exit $LASTEXITCODE
