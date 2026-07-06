#!/usr/bin/env pwsh
# -*- coding: utf-8 -*-
<#
.SYNOPSIS
    Eksport i ustanovka rasshirenij Cursor.

.EXAMPLE
    .\cursor-extensions-sync.ps1 -Export
    .\cursor-extensions-sync.ps1 -Install
    .\cursor-extensions-sync.ps1 -Install -SkipInstalled

    Ili dvoynoy klik: install-cursor-extensions.cmd
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

function Find-CursorCli {
    $candidates = @()

    $cursorCmd = Get-Command cursor -ErrorAction SilentlyContinue
    if ($cursorCmd) {
        $candidates += $cursorCmd.Source
    }

    $codeCmd = Get-Command code -ErrorAction SilentlyContinue
    if ($codeCmd) {
        $candidates += $codeCmd.Source
    }

    $knownPaths = @(
        "${env:ProgramFiles}\cursor\resources\app\bin\cursor.cmd",
        "${env:LocalAppData}\Programs\cursor\resources\app\bin\cursor.cmd",
        "${env:ProgramFiles}\Cursor\resources\app\bin\cursor.cmd",
        "${env:LocalAppData}\Programs\Cursor\resources\app\bin\cursor.cmd"
    )

    foreach ($path in $knownPaths) {
        if (Test-Path $path) {
            $candidates += $path
        }
    }

    $unique = $candidates | Select-Object -Unique
    if ($unique.Count -eq 0) {
        return $null
    }

    $path = [string]$unique[0]
    $name = if ($path -match "cursor\.cmd$") { "cursor" } else { "code" }
    return @{ Name = $name; Path = $path }
}

function Get-ExtensionLines {
    param([string]$Path)

    if (-not (Test-Path $Path)) {
        throw "Ne najden fajl so spiskom rasshirenij: $Path"
    }

    $result = New-Object System.Collections.Generic.List[string]
    Get-Content $Path -Encoding UTF8 | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#")) {
            $result.Add($line)
        }
    }
    return $result
}

function Invoke-CursorCli {
    param(
        [hashtable]$Cli,
        [string[]]$Args
    )

    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $Cli.Path
    $psi.Arguments = ($Args -join " ")
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.CreateNoWindow = $true

    $process = [System.Diagnostics.Process]::Start($psi)
    $stdout = $process.StandardOutput.ReadToEnd()
    $stderr = $process.StandardError.ReadToEnd()
    $process.WaitForExit()

    return @{
        ExitCode = $process.ExitCode
        StdOut = $stdout
        StdErr = $stderr
    }
}

function Export-Extensions {
    param($Cli, [string]$Path)

    Write-Host "Eksport rasshirenij v: $Path" -ForegroundColor Cyan

    $result = Invoke-CursorCli -Cli $Cli -Args @("--list-extensions", "--show-versions")
    if ($result.ExitCode -ne 0) {
        throw "Ne udalos poluchit spisok rasshirenij. Oshibka: $($result.StdErr)"
    }

    $output = @($result.StdOut -split "`r?`n" | Where-Object { $_.Trim() })
    if ($output.Count -eq 0) {
        throw "Spisok rasshirenij pust. Zapustite Cursor i povtorite."
    }

    $lines = New-Object System.Collections.Generic.List[string]
    $lines.Add("# Cursor extensions snapshot")
    $lines.Add("# Format: publisher.extension@version")
    $lines.Add("# Updated: $(Get-Date -Format 'yyyy-MM-dd HH:mm')")
    $lines.Add("# Export: .\cursor-extensions-sync.ps1 -Export")
    $lines.Add("")

    foreach ($ext in $output) {
        $ext = $ext.Trim()
        if ($ext) {
            $lines.Add($ext)
        }
    }

    $lines.Add("")
    [System.IO.File]::WriteAllLines($Path, $lines.ToArray(), [System.Text.UTF8Encoding]::new($false))
    Write-Host "OK: sohraneno $($output.Count) rasshirenij" -ForegroundColor Green
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
        $result = Invoke-CursorCli -Cli $Cli -Args @("--list-extensions", "--show-versions")
        if ($result.ExitCode -eq 0) {
            $current = @($result.StdOut -split "`r?`n" | Where-Object { $_.Trim() })
            foreach ($item in $current) {
                $item = $item.Trim()
                if ($item) {
                    $id = ($item -split "@")[0]
                    $installed[$id] = $true
                }
            }
        }
    }

    $ok = 0
    $fail = 0
    $skip = 0

    Write-Host "Ustanovka $($extensions.Count) rasshirenij iz: $Path" -ForegroundColor Cyan
    Write-Host "CLI: $($Cli.Path)" -ForegroundColor DarkGray
    Write-Host ""

    foreach ($ext in $extensions) {
        $extId = ($ext -split "@")[0]

        if ($OnlyMissing -and $installed.ContainsKey($extId)) {
            Write-Host "  SKIP (uzhe est): $ext" -ForegroundColor DarkGray
            $skip++
            continue
        }

        Write-Host "  INSTALL: $ext" -ForegroundColor White
        $result = Invoke-CursorCli -Cli $Cli -Args @("--install-extension", $ext, "--force")

        if ($result.ExitCode -eq 0) {
            Write-Host "    OK" -ForegroundColor Green
            $ok++
        }
        else {
            $err = ($result.StdErr + " " + $result.StdOut).Trim()
            if ($err) {
                Write-Host "    FAIL: $err" -ForegroundColor Red
            }
            else {
                Write-Host "    FAIL (kod $($result.ExitCode))" -ForegroundColor Red
            }
            $fail++
        }
    }

    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Ustanovleno: $ok | Propushcheno: $skip | Oshibok: $fail" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan

    if ($fail -gt 0) {
        Write-Host ""
        Write-Host "Chastye prichiny oshibok:" -ForegroundColor Yellow
        Write-Host "  - net dostupa k internetu / blokirovka marketplejsa na rabochem PK"
        Write-Host "  - cweijan.vscode-office - ustanovite vruchnuyu cherez Extensions"
        Write-Host "  - zapustite skript iz terminala Cursor (Terminal -> New Terminal)"
    }

    Write-Host ""
    Write-Host "Russkij yazyk menyu:" -ForegroundColor Green
    Write-Host "  Ctrl+Shift+P -> Configure Display Language -> ru -> Restart"
}

try {
    $cli = Find-CursorCli
    if (-not $cli) {
        Write-Host ""
        Write-Host "OSHIBKA: Ne najden Cursor CLI." -ForegroundColor Red
        Write-Host ""
        Write-Host "Reshenie 1 (luchshe):" -ForegroundColor Yellow
        Write-Host "  Otkrojte Cursor -> Terminal -> New Terminal"
        Write-Host "  cd put_k_papke_drafts"
        Write-Host "  powershell -ExecutionPolicy Bypass -File .\cursor-extensions-sync.ps1 -Install"
        Write-Host ""
        Write-Host "Reshenie 2:" -ForegroundColor Yellow
        Write-Host "  Dvoynoy klik po fajlu install-cursor-extensions.cmd"
        Write-Host ""
        exit 1
    }

    if ($Export) {
        Export-Extensions -Cli $cli -Path $ListFile
        exit 0
    }

    if (-not $Install) {
        $Install = $true
    }

    Install-Extensions -Cli $cli -Path $ListFile -OnlyMissing:$SkipInstalled
    exit 0
}
catch {
    Write-Host ""
    Write-Host "OSHIBKA: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "Esli v tekste est 'running scripts is disabled':" -ForegroundColor Yellow
    Write-Host "  Zapuskajte cherez install-cursor-extensions.cmd"
    Write-Host "  ili: powershell -ExecutionPolicy Bypass -File .\cursor-extensions-sync.ps1 -Install"
    Write-Host ""
    exit 1
}
