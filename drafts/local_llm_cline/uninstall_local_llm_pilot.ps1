#!/usr/bin/env pwsh
# -*- coding: utf-8 -*-
<#
.SYNOPSIS
  Полный откат пилота LM Studio + Cline на ноутбуке.
.DESCRIPTION
  Удаляет LM Studio, скачанные модели, расширение Cline и артефакты
  пилота в репозитории WIM_DEV. Cursor и его MCP/навыки не трогает.
#>

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Continue"

Write-Host "=== Rollback LM Studio + Cline pilot ===" -ForegroundColor Cyan

# 1. Stop LM Studio and local server
Write-Host "`n[1/6] Stop LM Studio processes..."
Get-Process -Name "LM Studio","lm-studio","lms" -ErrorAction SilentlyContinue |
    ForEach-Object {
        Write-Host ("  stop PID {0} ({1})" -f $_.Id, $_.ProcessName)
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
    }

# 2. Uninstall LM Studio via winget
Write-Host "`n[2/6] Uninstall LM Studio (winget)..."
if (Get-Command winget -ErrorAction SilentlyContinue) {
    winget uninstall --id ElementLabs.LMStudio --silent --accept-source-agreements 2>&1 |
        ForEach-Object { Write-Host "  $_" }
} else {
    Write-Host "  winget not found, skip app uninstall"
}

# 3. Delete model weights and LM Studio data
Write-Host "`n[3/6] Delete model weights and LM Studio data..."
$paths = @(
    "$env:USERPROFILE\.lmstudio",
    "$env:USERPROFILE\.lmstudio\pilot-downloads",
    "$env:LOCALAPPDATA\LM Studio",
    "$env:LOCALAPPDATA\Programs\LM Studio",
    "$env:APPDATA\LM Studio",
    "$env:USERPROFILE\.cache\lm-studio"
)
foreach ($p in $paths) {
    if (Test-Path $p) {
        $size = (Get-ChildItem $p -Recurse -Force -ErrorAction SilentlyContinue |
            Measure-Object -Property Length -Sum).Sum
        Write-Host ("  remove {0} ({1:N1} GB)" -f $p, ($size / 1GB))
        Remove-Item $p -Recurse -Force -ErrorAction SilentlyContinue
    } else {
        Write-Host "  skip (not found): $p"
    }
}

# 4. Uninstall Cline extension from VS Code
Write-Host "`n[4/6] Uninstall Cline from VS Code..."
$code = Get-Command code -ErrorAction SilentlyContinue
if ($code) {
    & code --uninstall-extension saoudrizwan.claude-dev 2>&1 |
        ForEach-Object { Write-Host "  $_" }
} else {
    Write-Host "  code CLI not found"
}

# Optional: Cline global storage (settings, history). Does not touch Cursor.
$clineStorage = Join-Path $env:APPDATA "Code\User\globalStorage\saoudrizwan.claude-dev"
if (Test-Path $clineStorage) {
    Write-Host "  remove Cline globalStorage: $clineStorage"
    Remove-Item $clineStorage -Recurse -Force -ErrorAction SilentlyContinue
}

# 5. Remove pilot artifacts in WIM_DEV (only what this pilot created)
Write-Host "`n[5/6] Remove pilot folders in WIM_DEV..."
$repo = "c:\1c\Cursor_1c\WIM_DEV"
$pilotPaths = @(
    (Join-Path $repo ".cline"),
    (Join-Path $repo ".clinerules")
)
foreach ($p in $pilotPaths) {
    if (Test-Path $p) {
        Write-Host "  remove $p"
        Remove-Item $p -Recurse -Force -ErrorAction SilentlyContinue
    } else {
        Write-Host "  skip (not found): $p"
    }
}

# 6. Free space summary
Write-Host "`n[6/6] Free space on C: {0:N1} GB" -f ((Get-PSDrive C).Free / 1GB)
Write-Host "`nDone. Cursor skills/MCP and Ollama (if any) were NOT touched." -ForegroundColor Green
Write-Host "Reboot is not required."
