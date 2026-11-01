@echo off
cd /d "%~dp0"
set PYTHONUTF8=1

findstr /C:"=== %date%" data\logs\update.log >nul 2>&1
if errorlevel 1 (
    echo No update today yet, running it now. This takes a few minutes...
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts\daily_update.ps1
)

echo.
echo Last update log:
powershell -NoProfile -Command "Get-Content data\logs\update.log -Tail 4"
echo.

netstat -ano | findstr ":8501" | findstr "LISTENING" >nul
if errorlevel 1 (
    echo Starting MatchLens UI...
    start "MatchLens UI" /min .venv\Scripts\python.exe -m streamlit run ui\app.py --server.port 8501 --server.headless true
    timeout /t 8 /nobreak >nul
)

start "" http://localhost:8501
