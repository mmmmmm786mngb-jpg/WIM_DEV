# Загружает расширение FO_SendFixStub из XML-исходников (Расширения\FO_SendFixStub) в разработческую базу ФО
# и обновляет конфигурацию БД. Параметры подключения берутся из реестра баз WIM_DEV (пароль в скрипт не пишется).
param(
    [string]$BaseId = 'wim_fo',
    [string]$V8Path = 'C:\Program Files\1cv8\8.3.27.2214\bin'
)

$ErrorActionPreference = 'Stop'
$extDir = Join-Path (Split-Path $PSScriptRoot -Parent) 'Расширения\FO_SendFixStub'
$registry = Get-Content 'C:\1c\Cursor_1c\WIM_DEV\.v8-project.json' -Raw -Encoding UTF8 | ConvertFrom-Json
$db = $registry.databases | Where-Object id -eq $BaseId

& powershell.exe -NoProfile -File 'C:/Users/Acer/.claude/skills/db-load-xml/scripts/db-load-xml.ps1' `
    -V8Path $V8Path -InfoBaseServer $db.server -InfoBaseRef $db.ref -UserName $db.user -Password $db.password `
    -ConfigDir $extDir -Mode Full -Extension 'FO_SendFixStub' -UpdateDB
exit $LASTEXITCODE
