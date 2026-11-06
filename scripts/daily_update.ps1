$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$env:PYTHONUTF8 = "1"
$logs = Join-Path $root "data\logs"
New-Item -ItemType Directory -Force -Path $logs | Out-Null
$marker = Join-Path $logs "last_success.txt"
$today = Get-Date -Format "yyyy-MM-dd"
if ((Test-Path $marker) -and ((Get-Content $marker -Raw).Trim() -eq $today)) { exit 0 }
$mutex = New-Object System.Threading.Mutex($false, "Global\MatchLensDailyUpdate")
if (-not $mutex.WaitOne(0)) { exit 0 }
$code = 1
try {
    cmd /c "echo === %date% %time% >> data\logs\update.log & .venv\Scripts\python.exe -u -W ignore -m matchlens.update >> data\logs\update.log 2>&1"
    $code = $LASTEXITCODE
    if ($code -eq 0) { Set-Content -Path $marker -Value $today -Encoding ascii }
}
finally {
    $mutex.ReleaseMutex()
}
exit $code
