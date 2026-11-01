$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$env:PYTHONUTF8 = "1"
New-Item -ItemType Directory -Force -Path (Join-Path $root "data\logs") | Out-Null
$mutex = New-Object System.Threading.Mutex($false, "Global\MatchLensDailyUpdate")
if (-not $mutex.WaitOne(0)) { exit 0 }
try {
    cmd /c "echo === %date% %time% >> data\logs\update.log & .venv\Scripts\python.exe -W ignore -m matchlens.update >> data\logs\update.log 2>&1"
}
finally {
    $mutex.ReleaseMutex()
}
