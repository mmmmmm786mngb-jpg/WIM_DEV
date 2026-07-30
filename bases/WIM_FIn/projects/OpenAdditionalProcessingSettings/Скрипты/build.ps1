# Build EPF OpenAdditionalProcessingSettings against WIM_FIN (no auth).
# ASCII-only script to avoid PowerShell encoding issues with Cyrillic paths.

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$RepoRoot = Resolve-Path (Join-Path $ProjectRoot "..\..\..\..")
$SrcDir = Join-Path $ProjectRoot "epf\src"
$BuildDir = Join-Path $ProjectRoot "epf\build"
$BuildScript = Join-Path $RepoRoot ".cursor\skills\epf-build\scripts\epf-build.ps1"
$V8Path = "C:\Program Files\1cv8\8.3.27.1859\bin"

$SourceFile = Get-ChildItem -Path $SrcDir -Filter "*.xml" -File | Select-Object -First 1
if (-not $SourceFile) {
	throw "Source XML not found in $SrcDir"
}

$ProcessorName = [System.IO.Path]::GetFileNameWithoutExtension($SourceFile.Name)
$OutputFile = Join-Path $BuildDir ($ProcessorName + ".epf")

New-Item -ItemType Directory -Force -Path $BuildDir | Out-Null

Write-Host "Source: $($SourceFile.FullName)"
Write-Host "Output: $OutputFile"
Write-Host "IB: localhost/WIM_FIN"

& powershell.exe -NoProfile -File $BuildScript `
	-V8Path $V8Path `
	-InfoBaseServer "localhost" `
	-InfoBaseRef "WIM_FIN" `
	-SourceFile $SourceFile.FullName `
	-OutputFile $OutputFile
