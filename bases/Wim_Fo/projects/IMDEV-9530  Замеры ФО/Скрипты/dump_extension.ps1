# Выгружает расширение FO_KeyOpsPerf из разработческой базы ФО в файл ЗАМЕРЫ\FO_KeyOpsPerf.cfe.
# Параметры подключения берутся из реестра баз WIM_DEV (пароль в скрипт не пишется).
param(
    [string]$BaseId = 'wim_fo',
    [string]$V8Path = 'C:\Program Files\1cv8\8.3.27.2214\bin'
)

$ErrorActionPreference = 'Stop'
$outFile = Join-Path (Split-Path $PSScriptRoot -Parent) 'ЗАМЕРЫ\FO_KeyOpsPerf.cfe'
$registry = Get-Content 'C:\1c\Cursor_1c\WIM_DEV\.v8-project.json' -Raw -Encoding UTF8 | ConvertFrom-Json
$db = $registry.databases | Where-Object id -eq $BaseId

& powershell.exe -NoProfile -File 'C:/Users/Acer/.claude/skills/db-dump-cf/scripts/db-dump-cf.ps1' `
    -V8Path $V8Path -InfoBaseServer $db.server -InfoBaseRef $db.ref -UserName $db.user -Password $db.password `
    -OutputFile $outFile -Extension 'FO_KeyOpsPerf'
exit $LASTEXITCODE
