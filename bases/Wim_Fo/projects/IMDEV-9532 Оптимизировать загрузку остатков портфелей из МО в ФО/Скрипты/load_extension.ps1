# Загружает расширение FO_PositionLoadOpt из XML-исходников в разработческую базу ФО и применяет его к БД.
# Параметры подключения берутся из реестра баз WIM_DEV (пароль в скрипт не пишется).
# Платформа - версии сервера 1С (8.3.27.2214), а не v8path реестра: конфигуратор должен совпадать с сервером.
# -ExtDir - другой каталог исходников с тем же расширением (диагностический вариант для замеров).
param(
    [string]$BaseId = 'wim_fo',
    [string]$V8Path = 'C:\Program Files\1cv8\8.3.27.2214\bin',
    [string]$ExtDir = ''
)

$ErrorActionPreference = 'Stop'
$extDir = $ExtDir
if (-not $extDir) {
    $extDir = Join-Path (Split-Path $PSScriptRoot -Parent) 'Расширения\FO_PositionLoadOpt'
}
$registry = Get-Content 'C:\1c\Cursor_1c\WIM_DEV\.v8-project.json' -Raw -Encoding UTF8 | ConvertFrom-Json
$db = $registry.databases | Where-Object id -eq $BaseId

& powershell.exe -NoProfile -File 'C:/Users/Acer/.claude/skills/db-load-xml/scripts/db-load-xml.ps1' `
    -V8Path $V8Path -InfoBaseServer $db.server -InfoBaseRef $db.ref -UserName $db.user -Password $db.password `
    -ConfigDir $extDir -Mode Full -Extension 'FO_PositionLoadOpt' -UpdateDB
exit $LASTEXITCODE
