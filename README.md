# MatchLens

Football match probability engine: odds twins, AI goal model and Bet365 market side by side.

```powershell
py -3.14 -m venv .venv; .venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m matchlens.update
.venv\Scripts\python -m matchlens.bulletin --date 2026-11-08
.venv\Scripts\python -m matchlens.twins backtest
.venv\Scripts\python -m pytest -q -p no:seleniumbase tests
```

Daily schedule: `powershell -ExecutionPolicy Bypass -File scripts\register_daily_task.ps1`
