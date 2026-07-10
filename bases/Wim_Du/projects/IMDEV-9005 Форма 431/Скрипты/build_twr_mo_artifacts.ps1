# Build 6 EPF + 4 ERF from Wim_Mo SRC using WIM_MO (localhost, no auth)
param(
    [string]$Manifest = "",
    [string]$V8Path = "C:\Program Files\1cv8\8.3.27.1859\bin",
    [string]$Server = "localhost",
    [string]$Ref = "WIM_MO"
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ProjectRoot = Split-Path $PSScriptRoot -Parent
$BuildRoot = Join-Path $ProjectRoot "twr_mo_build"
if (-not $Manifest) {
    $Manifest = Join-Path $BuildRoot "artifacts.json"
}

$cfg = Get-Content $Manifest -Raw -Encoding UTF8 | ConvertFrom-Json
$ErfOut = Join-Path $BuildRoot "erf"
$EpfOut = Join-Path $BuildRoot "epf"
$BuildScript = "c:\1c\Cursor_1c\WIM_DEV\.cursor\skills\epf-build\scripts\epf-build.ps1"
$LogFile = Join-Path $BuildRoot "build_log.txt"

New-Item -ItemType Directory -Path $ErfOut -Force | Out-Null
New-Item -ItemType Directory -Path $EpfOut -Force | Out-Null

$ok = 0
$fail = 0
$lines = @(
    "Build started: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')",
    "Base: $Server/$Ref",
    ""
)

foreach ($item in $cfg.items) {
    $sourceFile = Join-Path $cfg.srcMo $item.source
    $outDir = if ($item.type -eq "erf") { $ErfOut } else { $EpfOut }
    $outFile = Join-Path $outDir $item.output
    $line = "[$($item.type)] $($item.output)"
    Write-Host $line
    $lines += $line

    if (-not (Test-Path $sourceFile)) {
        $msg = "FAIL source not found: $sourceFile"
        Write-Host $msg -ForegroundColor Red
        $lines += $msg
        $fail++
        continue
    }

    $proc = Start-Process -FilePath "powershell.exe" -ArgumentList @(
        "-NoProfile",
        "-File", "`"$BuildScript`"",
        "-V8Path", "`"$V8Path`"",
        "-InfoBaseServer", "`"$Server`"",
        "-InfoBaseRef", "`"$Ref`"",
        "-SourceFile", "`"$sourceFile`"",
        "-OutputFile", "`"$outFile`""
    ) -NoNewWindow -Wait -PassThru

    if ($proc.ExitCode -eq 0 -and (Test-Path $outFile)) {
        $size = (Get-Item $outFile).Length
        $msg = "OK $outFile size=$size"
        Write-Host $msg -ForegroundColor Green
        $lines += $msg
        $ok++
    } else {
        $msg = "FAIL exit=$($proc.ExitCode)"
        Write-Host $msg -ForegroundColor Red
        $lines += $msg
        $fail++
    }
    $lines += ""
}

$summary = "Done OK=$ok FAIL=$fail"
Write-Host $summary
$lines += $summary
$lines | Set-Content -Path $LogFile -Encoding UTF8

if ($fail -gt 0) { exit 1 }
exit 0
