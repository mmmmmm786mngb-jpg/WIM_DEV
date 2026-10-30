# Возвращает учетной записи службы SQL Server доступ к файлам баз и запускает службы.
# 30.10.2026 05:32 у всех *.mdf/*.ldf/*.ndf в каталоге DATA остались права только BUILTIN\Администраторы,
# служба NT SERVICE\MSSQLSERVER получает "Отказано в доступе" к master.mdf, SQL не стартует, 1С обрывает сеансы.
# Запускать в PowerShell от имени администратора.

$data = 'C:\Program Files\Microsoft SQL Server\MSSQL14.MSSQLSERVER\MSSQL\DATA'

foreach ($mask in '*.mdf', '*.ldf', '*.ndf') {
    icacls (Join-Path $data $mask) /grant 'NT SERVICE\MSSQLSERVER:(F)'
}

Start-Service -Name MSSQLSERVER
Start-Service -Name SQLSERVERAGENT -ErrorAction SilentlyContinue
Get-Service MSSQLSERVER, SQLSERVERAGENT | Format-Table Name, Status
