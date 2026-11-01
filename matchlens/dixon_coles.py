from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy.optimize import minimize

XI = 0.0019
RIDGE = 3.0
RIDGE_STYLE = 30.0
WINDOW_DAYS = 1460
NEWCOMER_PRIOR = -0.15
NEWCOMER_DAYS = 300
RHO_BOUNDS = (-0.2, 0.2)
MIN_HALF_MATCHES = 200
DEFAULT_SHARES = {"home_1h": 0.445, "away_1h": 0.44, "early": 0.13}


@dataclass
class DixonColesModel:
    teams: list
    attack: np.ndarray
    defence: np.ndarray
    mu: float
    home: float
    rho: float
    shares: dict = field(default_factory=lambda: dict(DEFAULT_SHARES))
    newcomer_attack: float = NEWCOMER_PRIOR
    newcomer_defence: float = NEWCOMER_PRIOR

    def params(self):
        return np.concatenate([[self.mu, self.home, self.rho], self.attack, self.defence])

    def team_strength(self, team):
        index = {t: i for i, t in enumerate(self.teams)}.get(team)
        if index is None:
            return self.newcomer_attack, self.newcomer_defence
        return self.attack[index], self.defence[index]

    def expected_goals(self, home_team, away_team):
        att_h, def_h = self.team_strength(home_team)
        att_a, def_a = self.team_strength(away_team)
        lam_home = np.exp(self.mu + self.home + att_h - def_a)
        lam_away = np.exp(self.mu + att_a - def_h)
        return float(lam_home), float(lam_away)


def tau_terms(x, y, lam, mu, rho):
    tau = np.ones_like(lam)
    d_lam = np.zeros_like(lam)
    d_mu = np.zeros_like(lam)
    d_rho = np.zeros_like(lam)
    m00 = (x == 0) & (y == 0)
    m01 = (x == 0) & (y == 1)
    m10 = (x == 1) & (y == 0)
    m11 = (x == 1) & (y == 1)
    tau[m00] = 1 - lam[m00] * mu[m00] * rho
    tau[m01] = 1 + lam[m01] * rho
    tau[m10] = 1 + mu[m10] * rho
    tau[m11] = 1 - rho
    d_lam[m00] = -lam[m00] * mu[m00] * rho
    d_mu[m00] = -lam[m00] * mu[m00] * rho
    d_rho[m00] = -lam[m00] * mu[m00]
    d_lam[m01] = lam[m01] * rho
    d_rho[m01] = lam[m01]
    d_mu[m10] = mu[m10] * rho
    d_rho[m10] = mu[m10]
    d_rho[m11] = -1.0
    return tau, d_lam / tau, d_mu / tau, d_rho / tau


def neg_log_likelihood(params, hi, ai, hg, ag, w, n, prior_att, prior_def, ridge, ridge_style=None):
    ridge_style = ridge if ridge_style is None else ridge_style
    mu, home, rho = params[0], params[1], params[2]
    att, dfn = params[3:3 + n], params[3 + n:]
    log_lam = mu + home + att[hi] - dfn[ai]
    log_mu = mu + att[ai] - dfn[hi]
    lam, mu_ = np.exp(log_lam), np.exp(log_mu)
    tau, g_lam_tau, g_mu_tau, g_rho_tau = tau_terms(hg, ag, lam, mu_, rho)
    if np.any(tau <= 0):
        return 1e12, np.zeros_like(params)
    ll = np.log(tau) + hg * log_lam - lam + ag * log_mu - mu_
    att_dev, def_dev = att - prior_att, dfn - prior_def
    strength, style = att_dev + def_dev, att_dev - def_dev
    value = -np.sum(w * ll) + 0.5 * (ridge * np.sum(strength ** 2) + ridge_style * np.sum(style ** 2))
    g_h = w * (hg - lam + g_lam_tau)
    g_a = w * (ag - mu_ + g_mu_tau)
    grad = np.zeros_like(params)
    grad[0] = -(g_h.sum() + g_a.sum())
    grad[1] = -g_h.sum()
    grad[2] = -np.sum(w * g_rho_tau)
    grad[3:3 + n] = -(np.bincount(hi, g_h, n) + np.bincount(ai, g_a, n)) + ridge * strength + ridge_style * style
    grad[3 + n:] = (np.bincount(ai, g_h, n) + np.bincount(hi, g_a, n)) + ridge * strength - ridge_style * style
    return value, grad


def half_shares(matches):
    consistent = matches[matches["events_consistent"]]
    if len(consistent) < MIN_HALF_MATCHES:
        return dict(DEFAULT_SHARES)
    home_goals = consistent["home_goals"].sum()
    away_goals = consistent["away_goals"].sum()
    return {
        "home_1h": consistent["ht_home"].sum() / home_goals,
        "away_1h": consistent["ht_away"].sum() / away_goals,
        "early": consistent["early_goals"].sum() / (home_goals + away_goals),
    }


def fit(matches: pd.DataFrame, ref_date, xi=XI, ridge=RIDGE, window_days=WINDOW_DAYS, warm_start=None,
        targets=("home_goals", "away_goals"), fixed_rho=None, ridge_style=RIDGE_STYLE):
    ref_date = pd.Timestamp(ref_date)
    days_ago = (ref_date - matches["kickoff"]).dt.total_seconds() / 86400
    train = matches[(days_ago > 0) & (days_ago <= window_days)]
    days_ago = days_ago[train.index].to_numpy()
    if train.empty:
        raise ValueError("No training matches before reference date")

    teams = sorted(set(train["home_team_id"]) | set(train["away_team_id"]))
    index = {t: i for i, t in enumerate(teams)}
    n = len(teams)
    hi = train["home_team_id"].map(index).to_numpy()
    ai = train["away_team_id"].map(index).to_numpy()
    hg = train[targets[0]].to_numpy(dtype=float)
    ag = train[targets[1]].to_numpy(dtype=float)
    w = np.exp(-xi * days_ago)

    first_seen = pd.concat([
        train[["home_team_id", "kickoff"]].rename(columns={"home_team_id": "team"}),
        train[["away_team_id", "kickoff"]].rename(columns={"away_team_id": "team"}),
    ]).groupby("team")["kickoff"].min()
    span_days = days_ago.max()
    newcomer = np.array([
        span_days > NEWCOMER_DAYS * 2 and (ref_date - first_seen[t]).days <= NEWCOMER_DAYS for t in teams
    ])
    prior_att = np.where(newcomer, NEWCOMER_PRIOR, 0.0)
    prior_def = np.where(newcomer, NEWCOMER_PRIOR, 0.0)

    x0 = np.concatenate([[np.log(max(hg.mean(), 0.1)), 0.25, -0.05], prior_att, prior_def])
    if warm_start is not None:
        lookup = {t: i for i, t in enumerate(warm_start.teams)}
        x0[:3] = [warm_start.mu, warm_start.home, warm_start.rho]
        for t, i in index.items():
            if t in lookup:
                x0[3 + i] = warm_start.attack[lookup[t]]
                x0[3 + n + i] = warm_start.defence[lookup[t]]

    rho_bounds = RHO_BOUNDS if fixed_rho is None else (fixed_rho, fixed_rho)
    if fixed_rho is not None:
        x0[2] = fixed_rho
    bounds = [(None, None), (None, None), rho_bounds] + [(-3, 3)] * (2 * n)
    result = minimize(
        neg_log_likelihood, x0, jac=True, method="L-BFGS-B", bounds=bounds,
        args=(hi, ai, hg, ag, w, n, prior_att, prior_def, ridge, ridge_style),
    )
    params = result.x
    attack, defence = params[3:3 + n], params[3 + n:]
    newcomer_attack = float(np.percentile(attack, 15)) if n >= 6 else NEWCOMER_PRIOR
    newcomer_defence = float(np.percentile(defence, 15)) if n >= 6 else NEWCOMER_PRIOR
    return DixonColesModel(
        teams=teams, attack=attack, defence=defence,
        mu=float(params[0]), home=float(params[1]), rho=float(params[2]),
        shares=half_shares(train),
        newcomer_attack=newcomer_attack, newcomer_defence=newcomer_defence,
    )
