$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$env:PYTHONUTF8 = "1"
.venv\Scripts\python.exe -m streamlit run ui\app.py --server.port 8501
