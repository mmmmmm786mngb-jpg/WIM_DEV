# Загружает расширение FO_DealExecutionParallel из XML-исходников в базу и применяет его к БД,
# затем выгружает его в файл .cfe рядом с исходниками.
# Параметры подключения берутся из реестра баз WIM_DEV (пароль в скрипт не пишется).
# -Version - каталог сборки в Расширения: 1.4.10.0 или 1.4.9.5.
param(
    [string]$Version = '1.4.10.0',
    [string]$BaseId = 'wim_fo',
    [string]$V8Path = 'C:\Program Files\1cv8\8.3.27.2214\bin',
    [switch]$NoDump
)

$ErrorActionPreference = 'Stop'
$verDir = Join-Path (Split-Path $PSScriptRoot -Parent) "Расширения\$Version"
$extDir = Join-Path $verDir 'FO_DealExecutionParallel'
$cfe = Join-Path $verDir 'FO_DealExecutionParallel.cfe'
$registry = Get-Content 'C:\1c\Cursor_1c\WIM_DEV\.v8-project.json' -Raw -Encoding UTF8 | ConvertFrom-Json
$db = $registry.databases | Where-Object id -eq $BaseId
$conn = @('-V8Path', $V8Path)
if ($db.type -eq 'file') { $conn += @('-InfoBasePath', $db.path) } else { $conn += @('-InfoBaseServer', $db.server, '-InfoBaseRef', $db.ref) }
if ($db.user) { $conn += @('-UserName', $db.user, '-Password', $db.password) }

& powershell.exe -NoProfile -File 'C:/Users/Acer/.claude/skills/db-load-xml/scripts/db-load-xml.ps1' @conn `
    -ConfigDir $extDir -Mode Full -Extension 'FO_DealExecutionParallel' -UpdateDB
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
if (-not $NoDump) {
    & powershell.exe -NoProfile -File 'C:/Users/Acer/.claude/skills/db-dump-cf/scripts/db-dump-cf.ps1' @conn `
        -OutputFile $cfe -Extension 'FO_DealExecutionParallel'
}
exit $LASTEXITCODE
