# Загрузка тестового расширения IMDEV-9573 в WIM_DU, обновление БД и проверка модулей.
param([Parameter(Mandatory)][string]$Name, [switch]$NoCheck)
$T = Join-Path $PSScriptRoot '..\Расширения' | Resolve-Path
$V8 = 'C:\Program Files\1cv8\8.3.27.2214\bin'
powershell.exe -NoProfile -File 'C:/Users/Acer/.claude/skills/db-load-xml/scripts/db-load-xml.ps1' -V8Path $V8 -InfoBaseServer localhost -InfoBaseRef WIM_DU -ConfigDir (Join-Path $T $Name) -Mode Full -Extension $Name -UpdateDB 2>&1 | Select-Object -Last 2
if (-not $NoCheck) {
  powershell.exe -NoProfile -File 'C:/Users/Acer/.claude/skills/db-cfe-admin/scripts/db-cfe-admin.ps1' -Command check -V8Path $V8 -InfoBaseServer localhost -InfoBaseRef WIM_DU -Name $Name -Context 'ThinClient,WebClient,Server,ExternalConnection' 2>&1 | Select-Object -Last 6
}
