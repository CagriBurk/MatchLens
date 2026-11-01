import numpy as np
import pandas as pd
import pytest
from scipy.optimize import check_grad

from matchlens import dixon_coles


def synthetic_league(seed=0, n_teams=10, rounds=6):
    rng = np.random.default_rng(seed)
    attack = np.linspace(-0.4, 0.4, n_teams)
    defence = np.linspace(-0.3, 0.3, n_teams)[::-1]
    rows = []
    start = pd.Timestamp("2024-01-01", tz="UTC")
    day = 0
    for _ in range(rounds):
        for h in range(n_teams):
            for a in range(n_teams):
                if h == a:
                    continue
                lam_h = np.exp(0.2 + 0.3 + attack[h] - defence[a])
                lam_a = np.exp(0.2 + attack[a] - defence[h])
                rows.append({
                    "home_team_id": str(h), "away_team_id": str(a),
                    "home_goals": rng.poisson(lam_h), "away_goals": rng.poisson(lam_a),
                    "kickoff": start + pd.Timedelta(days=day),
                    "events_consistent": False, "ht_home": 0, "ht_away": 0, "early_goals": 0,
                })
                day += 1 if len(rows) % 5 == 0 else 0
    return pd.DataFrame(rows), attack


def test_gradient_matches_numeric():
    rng = np.random.default_rng(1)
    n, m = 6, 80
    hi, ai = rng.integers(0, n, m), rng.integers(0, n, m)
    hg, ag = rng.poisson(1.4, m).astype(float), rng.poisson(1.1, m).astype(float)
    w = rng.uniform(0.3, 1.0, m)
    prior = np.zeros(n)
    x0 = np.concatenate([[0.1, 0.25, -0.05], rng.normal(0, 0.2, 2 * n)])
    f = lambda x: dixon_coles.neg_log_likelihood(x, hi, ai, hg, ag, w, n, prior, prior, 1.0)[0]
    g = lambda x: dixon_coles.neg_log_likelihood(x, hi, ai, hg, ag, w, n, prior, prior, 1.0)[1]
    assert check_grad(f, g, x0) < 1e-3


def test_fit_recovers_team_order_and_home_advantage():
    matches, attack = synthetic_league()
    ref = matches["kickoff"].max() + pd.Timedelta(days=1)
    model = dixon_coles.fit(matches, ref, xi=0.0, ridge=0.1)
    fitted = np.array([model.attack[model.teams.index(str(i))] for i in range(len(attack))])
    assert np.corrcoef(fitted, attack)[0, 1] > 0.8
    assert 0.1 < model.home < 0.5


def test_fit_ignores_future_matches():
    matches, _ = synthetic_league()
    ref = matches["kickoff"].iloc[len(matches) // 2]
    model = dixon_coles.fit(matches, ref)
    future = matches[matches["kickoff"] >= ref]
    poisoned = matches.copy()
    poisoned.loc[future.index, "home_goals"] = 9
    model_poisoned = dixon_coles.fit(poisoned, ref)
    assert model.mu == pytest.approx(model_poisoned.mu)


def test_unknown_team_gets_newcomer_strength():
    matches, _ = synthetic_league()
    model = dixon_coles.fit(matches, matches["kickoff"].max() + pd.Timedelta(days=1))
    lam_known, _ = model.expected_goals("9", "0")
    lam_new, _ = model.expected_goals("unknown", "0")
    assert lam_new < lam_known


def test_custom_targets_and_fixed_rho():
    matches, attack = synthetic_league()
    matches["home_mix"] = 0.5 * matches["home_goals"] + 0.5 * matches["home_goals"].mean()
    matches["away_mix"] = 0.5 * matches["away_goals"] + 0.5 * matches["away_goals"].mean()
    ref = matches["kickoff"].max() + pd.Timedelta(days=1)
    model = dixon_coles.fit(matches, ref, xi=0.0, ridge=0.1, targets=("home_mix", "away_mix"), fixed_rho=-0.07)
    assert model.rho == pytest.approx(-0.07)
    goals_model = dixon_coles.fit(matches, ref, xi=0.0, ridge=0.1)
    assert np.std(model.attack) < np.std(goals_model.attack)
