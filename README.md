# MatchLens

Football match probability and value engine.

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m matchlens.update
.venv/bin/python -m matchlens.bulletin --date 2026-11-02
.venv/bin/python -m matchlens.backtest
.venv/bin/python -m pytest -q tests
```
