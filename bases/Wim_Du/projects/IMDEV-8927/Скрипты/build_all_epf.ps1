# Сборка всех EPF из каталога Обработки проекта IMDEV-8927.
# Источники: Обработки/<имя>_epf/<имя>.xml
# Результат:  Обработки/<имя>.epf
#
# Пример:
#   powershell.exe -NoProfile -File "Скрипты/build_all_epf.ps1"
#   powershell.exe -NoProfile -File "Скрипты/build_all_epf.ps1" -InfoBaseServer "localhost" -InfoBaseRef "WIM_DU"

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

# Katalog s *_epf (Obработки) - bez kirillicy v skripte iz-za kodirovki PS 5
$ObrabotkiDir = Get-ChildItem -LiteralPath $ProjectDir -Directory |
    Where-Object {
        @(Get-ChildItem -LiteralPath $_.FullName -Directory -Filter "*_epf" -ErrorAction SilentlyContinue).Count -gt 0
    } |
    Select-Object -First 1 -ExpandProperty FullName

if (-not (Test-Path $BuildScript)) {
    Write-Host "ERROR: epf-build.ps1 not found" -ForegroundColor Red
    exit 1
}

if (-not $ObrabotkiDir) {
    Write-Host "ERROR: no folder with *_epf sources in $ProjectDir" -ForegroundColor Red
    exit 1
}

$dirs = Get-ChildItem -LiteralPath $ObrabotkiDir -Directory | Sort-Object Name
if ($dirs.Count -eq 0) {
    Write-Host "ERROR: no *_epf folders in $ObrabotkiDir" -ForegroundColor Red
    exit 1
}

Write-Host "Project:  $ProjectDir"
Write-Host "Source:   $ObrabotkiDir"
Write-Host "Database: $InfoBaseServer/$InfoBaseRef"
Write-Host "Count:    $($dirs.Count)"
Write-Host ""

$ok = 0
$failed = @()

foreach ($dir in $dirs) {
    $baseName = $dir.Name
    if ($baseName.EndsWith("_epf")) {
        $baseName = $baseName.Substring(0, $baseName.Length - 4)
    }

    $sourceFile = Join-Path $dir.FullName ($baseName + ".xml")
    $outputFile = Join-Path $ObrabotkiDir ($baseName + ".epf")

    if (-not (Test-Path -LiteralPath $sourceFile)) {
        Write-Host "SKIP (no xml): $baseName" -ForegroundColor Yellow
        $failed += $baseName
        continue
    }

    Write-Host "BUILD: $baseName"

    $buildArgs = @(
        "-NoProfile",
        "-File", $BuildScript,
        "-V8Path", $V8Path,
        "-InfoBaseServer", $InfoBaseServer,
        "-InfoBaseRef", $InfoBaseRef,
        "-SourceFile", $sourceFile,
        "-OutputFile", $outputFile
    )
    if ($UserName) { $buildArgs += @("-UserName", $UserName) }
    if ($Password) { $buildArgs += @("-Password", $Password) }

    & powershell.exe @buildArgs

    if ($LASTEXITCODE -eq 0) {
        $ok++
    }
    else {
        $failed += $baseName
        Write-Host "FAILED: $baseName" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "=== SUMMARY ==="
Write-Host "OK: $ok / $($dirs.Count)"
if ($failed.Count -gt 0) {
    Write-Host "FAILED ($($failed.Count)):"
    $failed | ForEach-Object { Write-Host "  $_" }
    exit 1
}

Write-Host "All EPF built successfully."
exit 0
