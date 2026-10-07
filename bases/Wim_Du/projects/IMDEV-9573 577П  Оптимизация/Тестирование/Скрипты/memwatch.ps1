param([string]$Out, [int]$Seconds = 120)
$end = (Get-Date).AddSeconds($Seconds)
"time,pid,ws_mb,private_mb" | Out-File $Out -Encoding utf8
while ((Get-Date) -lt $end) {
  $t = (Get-Date).ToString('HH:mm:ss.fff')
  Get-Process rphost -ErrorAction SilentlyContinue | ForEach-Object { "$t,$($_.Id),$([math]::Round($_.WorkingSet64/1MB)),$([math]::Round($_.PrivateMemorySize64/1MB))" } | Out-File $Out -Append -Encoding utf8
  Start-Sleep -Milliseconds 500
}
