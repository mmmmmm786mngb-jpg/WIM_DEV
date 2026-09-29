# Сборка обработок стенда из XML-исходников выгрузок ПРОД (запускать в PowerShell 7: pwsh -File build_epf.ps1).
#   ФО: внУдалениеБлокировок, внПерерасчетСтоимостиФактическойПозицииИ_РСА_СЧА, внОперацииПослеОбмена - против WIN_FO_server;
#   МО: внВыгрузкаОстатковМО_ФО (версия из выгрузки ПРОД) - против WIM_MO.
# Можно передать имена обработок аргументами, чтобы собрать только их.
# Предварительная проверка отключена (-Checks off): временная база-заглушка не загружает формы обработок,
# ссылающиеся на типы конфигурации; исходники взяты из выгрузки ПРОД и собираются против полных баз.
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$out = Join-Path $here 'epf'
New-Item -ItemType Directory -Force $out | Out-Null
$registry = Get-Content 'C:\1c\Cursor_1c\WIM_DEV\.v8-project.json' -Raw -Encoding UTF8 | ConvertFrom-Json
$build = Join-Path $env:USERPROFILE '.claude\skills\epf-build\scripts\epf-build.ps1'
$v8 = 'C:\Program Files\1cv8\8.3.27.2214\bin'
$targets = [ordered]@{
    'внУдалениеБлокировок' = @{ Src = 'C:\1c\Cursor_1c\WORK\WIM_Fo\SRC\epf'; Db = 'wim_fo' }
    'внПерерасчетСтоимостиФактическойПозицииИ_РСА_СЧА' = @{ Src = 'C:\1c\Cursor_1c\WORK\WIM_Fo\SRC\epf'; Db = 'wim_fo' }
    'внОперацииПослеОбмена' = @{ Src = 'C:\1c\Cursor_1c\WORK\WIM_Fo\SRC\epf'; Db = 'wim_fo' }
    'внВыгрузкаОстатковМО_ФО' = @{ Src = 'C:\1c\Cursor_1c\WORK\Wim_Mo\SRC\epf'; Db = 'wim_mo' }
}
$names = if ($args.Count -gt 0) { $args } else { $targets.Keys }
foreach ($name in $names) {
    $t = $targets[$name]
    $db = $registry.databases | Where-Object { $_.id -eq $t.Db }
    $xml = Join-Path $t.Src "$($name)_epf\$name.xml"
    $epf = Join-Path $out "$name.epf"
    $auth = @()
    if ($t.Db -ne 'wim_mo' -and $db.user) { $auth = @('-UserName', $db.user, '-Password', $db.password) }
    & powershell.exe -NoProfile -File $build -V8Path $v8 -InfoBaseServer $db.server -InfoBaseRef $db.ref @auth `
        -SourceFile $xml -OutputFile $epf -Checks off
    if ($LASTEXITCODE -ne 0) { throw "Сборка $name завершилась с кодом $LASTEXITCODE" }
    Write-Host "Собрано: $epf"
}
