#!/usr/bin/env pwsh
# -*- coding: utf-8 -*-
<#
.SYNOPSIS
    Eksport i ustanovka rasshirenij Cursor.

.DESCRIPTION
    Na tekushchem PK:  .\cursor-extensions-sync.ps1 -Export
    Na novom PK:       .\cursor-extensions-sync.ps1 -Install
    Posle ustanovki russkogo paketa: perezapustit Cursor
    (Ctrl+Shift+P -> Configure Display Language -> ru)

.PARAMETER Export
    Sohranit spisok rasshirenij v cursor-extensions.txt

.PARAMETER Install
    Ustanovit rasshireniya iz cursor-extensions.txt (po umolchaniyu)

.PARAMETER ListFile
    Put k fajlu so spiskom (po umolchaniyu: cursor-extensions.txt ryadom so skriptom)

.EXAMPLE
    .\cursor-extensions-sync.ps1 -Export
    .\cursor-extensions-sync.ps1 -Install
    .\cursor-extensions-sync.ps1 -Install -SkipInstalled
#>

param(
    [switch]$Export,
    [switch]$Install,
    [switch]$SkipInstalled,
    [string]$ListFile = ""
)

$ErrorActionPreference = "Continue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $ListFile) {
    $ListFile = Join-Path $ScriptDir "cursor-extensions.txt"
}

function Get-CursorCli {
    $cursor = Get-Command cursor -ErrorAction SilentlyContinue
    if ($cursor) {
        return @{ Name = "cursor"; Path = $cursor.Source }
    }

    $code = Get-Command code -ErrorAction SilentlyContinue
    if ($code) {
        Write-Host "WARN: cursor ne najden, ispolzuetsya code" -ForegroundColor Yellow
        return @{ Name = "code"; Path = $code.Source }
    }

    return $null
}

function Get-ExtensionLines {
    param([string]$Path)

    if (-not (Test-Path $Path)) {
        throw "Fajl ne najden: $Path"
    }

    Get-Content $Path -Encoding UTF8 | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#")) {
            $line
        }
    }
}

function Export-Extensions {
    param($Cli, [string]$Path)

    Write-Host "Eksport rasshirenij v: $Path" -ForegroundColor Cyan

    $output = @(& $Cli.Path --list-extensions --show-versions 2>$null | ForEach-Object { [string]$_ })
    if ($output.Count -eq 0) {
        throw "Ne udalos poluchit spisok rasshirenij (pustoj otvet)"
    }

    $lines = @(
        "# Cursor extensions snapshot"
        "# Format: publisher.extension@version"
        "# Updated: $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
        "# Export: .\cursor-extensions-sync.ps1 -Export"
        ""
    )

    foreach ($ext in $output) {
        $ext = $ext.Trim()
        if ($ext) {
            $lines += $ext
        }
    }

    $lines += ""
    [System.IO.File]::WriteAllLines($Path, $lines, [System.Text.UTF8Encoding]::new($false))
    Write-Host "OK: sohraneno $($lines.Count - 5) rasshirenij" -ForegroundColor Green
}

function Install-Extensions {
    param($Cli, [string]$Path, [bool]$OnlyMissing)

    $extensions = @(Get-ExtensionLines -Path $Path)
    if ($extensions.Count -eq 0) {
        Write-Host "Spisok pust: $Path" -ForegroundColor Yellow
        return
    }

    $installed = @{}
    if ($OnlyMissing) {
        $current = & $Cli.Path --list-extensions --show-versions 2>$null
        foreach ($item in @($current)) {
            $item = [string]$item
            $item = $item.Trim()
            if ($item) {
                $id = ($item -split "@")[0]
                $installed[$id] = $true
            }
        }
    }

    $ok = 0
    $fail = 0
    $skip = 0

    Write-Host "Ustanovka $($extensions.Count) rasshirenij iz: $Path" -ForegroundColor Cyan
    Write-Host ""

    foreach ($ext in $extensions) {
        $extId = ($ext -split "@")[0]

        if ($OnlyMissing -and $installed.ContainsKey($extId)) {
            Write-Host "  SKIP (uzhe est): $ext" -ForegroundColor DarkGray
            $skip++
            continue
        }

        Write-Host "  INSTALL: $ext" -ForegroundColor White
        $null = & $Cli.Path --install-extension $ext --force 2>&1
        $exitCode = $LASTEXITCODE

        if ($exitCode -eq 0) {
            Write-Host "    OK" -ForegroundColor Green
            $ok++
        }
        else {
            Write-Host "    FAIL (exit $exitCode)" -ForegroundColor Red
            $fail++
        }
    }

    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Ustanovleno: $ok | Propushcheno: $skip | Oshibok: $fail" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan

    if ($fail -gt 0) {
        Write-Host ""
        Write-Host "Esli cweijan.vscode-office ne ustanovilsya - on mog byt iz .vsix." -ForegroundColor Yellow
        Write-Host "Ustanovite vruchnuyu: Extensions -> vscode-office" -ForegroundColor Yellow
    }

    Write-Host ""
    Write-Host "Russkij yazyk menyu:" -ForegroundColor Green
    Write-Host "  1. Ctrl+Shift+P -> Configure Display Language -> ru"
    Write-Host "  2. Perezapustit Cursor"
}

# --- main ---

$cli = Get-CursorCli
if (-not $cli) {
    Write-Host "ERROR: Ne najden cursor ili code v PATH." -ForegroundColor Red
    Write-Host "Ustanovite Cursor i dobavte v PATH, ili zapustite iz terminala Cursor." -ForegroundColor Red
    exit 1
}

Write-Host "CLI: $($cli.Path)" -ForegroundColor DarkGray

if ($Export) {
    Export-Extensions -Cli $cli -Path $ListFile
    exit 0
}

if (-not $Install) {
    $Install = $true
}

Install-Extensions -Cli $cli -Path $ListFile -OnlyMissing:$SkipInstalled
exit 0
