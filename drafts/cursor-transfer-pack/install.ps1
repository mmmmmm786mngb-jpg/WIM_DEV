#!/usr/bin/env pwsh
# -*- coding: utf-8 -*-
# Установка skills, rules и настроек Cursor на новом компьютере.
# Запуск: правой кнопкой -> "Выполнить с PowerShell" или из терминала:
#   powershell -ExecutionPolicy Bypass -File install.ps1

param(
    [string]$ProjectPath = "C:\1c\Cursor_1c\WIM_DEV",
    [switch]$SkipExtensions,
    [switch]$SkipSettings
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"
chcp 65001 | Out-Null

$PackRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$CursorUserDir = Join-Path $env:APPDATA "Cursor\User"
$SettingsTarget = Join-Path $CursorUserDir "settings.json"

function Write-Step([string]$Text) {
    Write-Host ""
    Write-Host "==> $Text" -ForegroundColor Cyan
}

Write-Host "Cursor Transfer Pack - ustanovka" -ForegroundColor Green
Write-Host "Pack: $PackRoot"
Write-Host "Proekt: $ProjectPath"

# 1. Project .cursor (rules + skills)
Write-Step "Kopirovanie .cursor v proekt"
if (-not (Test-Path $ProjectPath)) {
    New-Item -ItemType Directory -Path $ProjectPath -Force | Out-Null
    Write-Host "Sozdana papka proekta: $ProjectPath"
}

$DotCursorTarget = Join-Path $ProjectPath ".cursor"
New-Item -ItemType Directory -Path $DotCursorTarget -Force | Out-Null
Copy-Item -Path (Join-Path $PackRoot "dot-cursor\*") -Destination $DotCursorTarget -Recurse -Force
Write-Host "OK: rules i skills skopirovany v $DotCursorTarget"

# 2. Skill 1c-bsl-coding (esli net v dot-cursor)
Write-Step "Ustanovka skill 1c-bsl-coding"
$BslSkillTarget = Join-Path $DotCursorTarget "skills\1c-bsl-coding"
New-Item -ItemType Directory -Path $BslSkillTarget -Force | Out-Null
Copy-Item -Path (Join-Path $PackRoot "skills-1c-bsl-coding\*") -Destination $BslSkillTarget -Force
Write-Host "OK: skill 1c-bsl-coding ustanovlen"

# 3. User settings.json
if (-not $SkipSettings) {
    Write-Step "Ustanovka settings.json"
    New-Item -ItemType Directory -Path $CursorUserDir -Force | Out-Null

    if (Test-Path $SettingsTarget) {
        $Backup = "$SettingsTarget.backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
        Copy-Item $SettingsTarget $Backup -Force
        Write-Host "Rezervnaya kopiya: $Backup"
    }

    Copy-Item (Join-Path $PackRoot "user-settings\settings.json") $SettingsTarget -Force
    Write-Host "OK: settings.json ustanovlen"
    Write-Host "VNIMANIE: proverte puti k Java i bsl-language-server.jar v nastrojkah!"
    Write-Host "  Java: C:\Program Files\Eclipse Adoptium\jdk-17...\bin\java.exe"
    Write-Host "  BSL:  C:\bsl\bsl-language-server.jar"
}

# 4. Extensions
if (-not $SkipExtensions) {
    Write-Step "Ustanovka rasshirenij Cursor"
    $CursorCmd = Get-Command cursor -ErrorAction SilentlyContinue
    if (-not $CursorCmd) {
        Write-Host "cursor CLI ne najden v PATH. Ustanovite rasshireniya vruchnuyu po spisku extensions.txt"
    }
    else {
        $ExtensionsFile = Join-Path $PackRoot "extensions.txt"
        Get-Content $ExtensionsFile | ForEach-Object {
            $ext = $_.Trim()
            if ($ext -and -not $ext.StartsWith("#")) {
                Write-Host "  install: $ext"
                & cursor --install-extension $ext 2>&1 | Out-Null
            }
        }
        Write-Host "OK: rasshireniya ustanovleny (ili uzhe byli)"
    }
}

# 5. User Rules - reminder
Write-Step "User Rules (pravila polzovatelya)"
Write-Host "User Rules nelzya skopirovat fajlom avtomaticheski."
Write-Host "Otkrojte Cursor -> Settings -> Rules -> User Rules"
Write-Host "Skopirujte tekst iz fajlov v papke:"
Write-Host "  $PackRoot\user-rules\"
Write-Host ""
Write-Host "Ili otkrojte fajl USER-RULES-COMBINED.md i vstavte odin raz."

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "GOTOVO! Perezapustite Cursor." -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Sleduyushij shag: klonirovat Git repozitorij (sm. INSTRUKCIYA.md)"
