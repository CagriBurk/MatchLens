# MatchLens

A football match probability engine. For every fixture it puts three independent views side by
side: a statistical goal model, "odds twins" (what actually happened in the most similar
historical matches) and the bookmaker's margin-free price. Every model change is accepted or
rejected by an out-of-sample calibration report.

It is a learning project, not a betting tool. Its main finding is a negative one: neither the
model nor the twins beat the market, and no betting rule was profitable historically.
Türkçe özet aşağıda.

## How it works

- **Goal model:** a Dixon-Coles model with two separate ridge penalties: one for team *strength*
  (attack + defence, drives 1X2) and one for *style* (attack − defence, drives goal totals).
  A single penalty made goal totals too spread out (calibration slope 0.77); splitting them
  brought Over 1.5 / 2.5 / 3.5 slopes to 0.95–1.03. The score matrix gives every market:
  1X2, over/under, both teams to score, half-time, HT/FT and combinations.
- **Odds twins:** k-nearest-neighbour search over 145,000 historical matches in margin-free
  1X2 and Over 2.5 price space. The real outcomes of the 200 closest matches give an empirical
  probability for any market.
- **Market:** Bet365 (or DraftKings) prices from ESPN, with the bookmaker margin removed. The
  market price is never a model input; it is only used for comparison.
- **Model health gate:** walk-forward backtest (31,900 predictions), tuned on matches before
  July 2024 and judged on the ~10,000 matches after. A market passes when its bias is within
  1 percentage point and its calibration slope is within 0.85–1.15.
- **Forward tracking:** a daily scheduled job fetches fixtures and prices, logs every
  prediction before kick-off and settles it afterwards, so the scorecard is never back-filled.

## Results (holdout: July 2024 onward, ~10,000 matches)

| | Model | Odds twins | Market (margin-free) |
|---|---|---|---|
| 1X2 log-loss (matches with Bet365 odds) | 1.007 | | **0.988** |
| Over 2.5 log-loss | 0.677 | **0.673** | |
| Markets passing the calibration check | 12 of 19 | | |

- The model is well calibrated on 1X2 but carries less information than the bookmaker.
- Remaining weaknesses are documented: "both teams to score" is under-dispersed (slope 0.75),
  and goal markets drifted in 2026 when scoring rose by ~0.12 goals per match.
- Local pool-betting odds carry a 15–19% margin. No model-based or twin-based rule beat it,
  and forward tracking of 1,000+ selections found no price above fair value.

## Data

- **ESPN:** 12 leagues, 2016–2026, ~20,000 matches with Bet365 odds.
- **Historical pools:** Kaggle and FootyStats match datasets, Understat, ClubElo.
- Everything is merged into one SQLite database through a team-name linking layer.

## Tech stack

Python · pandas · NumPy · SciPy · SQLite · Streamlit · pytest

## Run

```powershell
py -3.14 -m venv .venv; .venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m matchlens.update                 # fetch fixtures, prices, predictions
.venv\Scripts\python -m matchlens.backtest               # walk-forward backtest
.venv\Scripts\python -m matchlens.health --label check   # calibration report -> data/reports/
.venv\Scripts\python -m matchlens.twins backtest
powershell -File scripts\run_ui.ps1                       # Streamlit UI on http://localhost:8501
.venv\Scripts\python -m pytest -q -p no:seleniumbase tests
```

Daily schedule (Windows Task Scheduler):
`powershell -ExecutionPolicy Bypass -File scripts\register_daily_task.ps1`

## Project structure

```text
data_pipeline/   ingestion (ESPN, Kaggle, FootyStats, Understat, Elo), team-name linking, SQLite
matchlens/       Dixon-Coles model, markets, calibration, odds twins, backtest, health report
ui/              Streamlit app: bulletin, match detail, twins, scorecard
scripts/         daily update and research scripts
tests/           pytest suite
```

---

## Türkçe özet

MatchLens, futbol maçları için bir olasılık motorudur. Her maçta üç bağımsız görüşü yan yana
koyar: Dixon-Coles gol modeli, "oran ikizleri" (en benzer 200 geçmiş maçta gerçekte ne olduğu)
ve bahis şirketinin marjı çıkarılmış oranı. Her model değişikliği, ayarlamada kullanılmamış
~10.000 maçlık bir kalibrasyon raporuyla kabul ya da reddedilir.

Bir öğrenme projesidir, bahis aracı değildir. Ana sonuç olumsuzdur: ne model ne de ikizler
piyasayı geçebildi; hiçbir bahis kuralı geçmişte kâr etmedi.
