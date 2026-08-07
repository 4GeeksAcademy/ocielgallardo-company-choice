# Mata todos los uvicorn/python workers de este proyecto que escuchan auth API.
# Uso (PowerShell, desde la raíz del repo):
#   powershell -NoProfile -File scripts/kill-uvicorn.ps1

$procs = Get-CimInstance Win32_Process -Filter "Name = 'python.exe'"
$killed = 0
foreach ($p in $procs) {
  $cmd = $p.CommandLine
  if ($null -eq $cmd) { continue }
  if ($cmd -like '*uvicorn*services.app.main*' -or $cmd -like '*multiprocessing.spawn*') {
    Write-Host "Killing PID $($p.ProcessId)"
    Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
    $killed++
  }
}
Start-Sleep -Seconds 2
Write-Host "Killed $killed process(es)."
$conn = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($conn) {
  Write-Host "Port 8000 still has connections:"
  $conn | Format-Table OwningProcess, State
} else {
  Write-Host "Port 8000 is free. Start ONE server:"
  Write-Host '  uv run python -m uvicorn services.app.main:app --reload'
}
