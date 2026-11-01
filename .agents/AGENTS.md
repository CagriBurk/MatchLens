# MatchLens Project Rules

## 1. Working Mode
- Decisions (architecture, data sources, models, scope) are made together with the user; once agreed, the agent writes the code directly.
- Keep responses short and in Turkish. No step-by-step tutorials unless asked.

## 2. Code Style
- All strings, prints and logs inside code are in English. Exception: user-facing UI copy under `ui/` is Turkish.
- Terminal output is minimal and informational (no decorative banners or emojis).
- No inline comments or docstrings; code should be self-explanatory.
- Paths come from `data_pipeline/config.py`; DB access goes through `data_pipeline/db.py`.
- Every feature that uses past matches must be leakage-free (only data strictly before kickoff).

## 3. Documentation
- `docs/03_roadmap.md` is the living roadmap: update it whenever a decision is made or a task is completed.
- `docs/06_master_architecture_and_audit.md` is the architecture reference.
