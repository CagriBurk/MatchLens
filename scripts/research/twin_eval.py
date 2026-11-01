import sys

import numpy as np
import pandas as pd

pd.set_option("display.width", 250)
pd.set_option("display.max_rows", 200)
z = np.load(sys.argv[1], allow_pickle=False)
KEYS = list(z["keys"])
P0, Y = z["P0"].astype(float), z["Y"].astype(float)
dates = z["dates"]
tune = dates < np.datetime64("2022-07-01")
test = ~tune
names = [n[4:] for n in z.files if n.startswith("est_")]
A_GRID = (0, 25, 50, 100, 200, 400, 800, 1600, 3200, 6400)
EPS = 1e-4


def group(key):
    if "&" in key:
        return "combo"
    if key in ("home", "draw", "away", "dc_1x", "dc_x2"):
        return "result"
    if key.startswith(("over", "under")):
        return "totals"
    if key.startswith("btts"):
        return "btts"
    if key.startswith("ht_"):
        return "first_half"
    return "special"


REQUIRED = {"result": 1.144, "totals": 1.144, "btts": 1.144, "first_half": 1.144, "combo": 1.19, "special": 1.27}


def ll(p, y):
    p = np.clip(p, EPS, 1 - EPS)
    return -(y * np.log(p) + (1 - y) * np.log(1 - p))


def shrunk(e, n, p0, a):
    out = (n[:, None] * e + a * p0) / (n[:, None] + a)
    return np.where(np.isnan(e), p0, out)


rows, best_a, preds = [], {}, {}
for name in names:
    e, n = z[f"est_{name}"].astype(float), z[f"neff_{name}"].astype(float)
    a_by_key = []
    for j, key in enumerate(KEYS):
        m = tune & ~np.isnan(Y[:, j])
        scores = [ll(shrunk(e[m, j:j + 1], n[m], P0[m, j:j + 1], a)[:, 0], Y[m, j]).mean() for a in A_GRID]
        a_by_key.append(A_GRID[int(np.argmin(scores))])
    best_a[name] = a_by_key
    raw = np.where(np.isnan(e), P0, e)
    shr = np.column_stack([shrunk(e[:, j:j + 1], n, P0[:, j:j + 1], a_by_key[j])[:, 0] for j in range(len(KEYS))])
    preds[name], preds[f"{name}+s"] = raw, shr
    for j, key in enumerate(KEYS):
        m = test & ~np.isnan(Y[:, j])
        base = ll(P0[m, j], Y[m, j]).mean()
        rows.append({"method": name, "key": key, "group": group(key), "n": int(m.sum()), "base": base,
                     "raw": 1000 * (ll(raw[m, j], Y[m, j]).mean() - base), "shrunk": 1000 * (ll(shr[m, j], Y[m, j]).mean() - base),
                     "a": a_by_key[j]})
res = pd.DataFrame(rows)
print("=== A. Test log-loss vs Bet365-derived price (x1000; negative = twins add information) ===")
print("mean over markets per group (raw / shrunk toward market):")
g = res.groupby(["method", "group"])[["raw", "shrunk"]].mean().unstack("group").round(2)
print(g.to_string())
print("\nmean over all markets:")
print(res.groupby("method")[["raw", "shrunk"]].mean().round(3).sort_values("shrunk").to_string())
best = res.groupby("method")["shrunk"].mean().idxmin()
print(f"\nbest method (shrunk): {best}")
piv = res[res["method"].isin(["g200", best, "lg50", "wtd"])].pivot_table(index="key", columns="method", values=["raw", "shrunk"]).round(2)
print(piv.to_string())
print("chosen shrink strength a per key for best:", dict(zip(KEYS, best_a[best])))

se_rows = []
for j, key in enumerate(KEYS):
    m = test & ~np.isnan(Y[:, j])
    d = ll(preds[f"{best}+s"][m, j], Y[m, j]) - ll(P0[m, j], Y[m, j])
    se_rows.append({"key": key, "diff_x1000": 1000 * d.mean(), "se_x1000": 1000 * d.std() / np.sqrt(len(d))})
print("\nbest shrunk vs market, per key with standard error:")
print(pd.DataFrame(se_rows).round(3).to_string(index=False))


def rule(p, label, thresholds=(0.05, 0.10, 0.20)):
    out = []
    for j, key in enumerate(KEYS):
        m = test & ~np.isnan(Y[:, j])
        ratio = p[m, j] / np.maximum(P0[m, j], EPS) - 1
        for t in thresholds:
            for side, pick in (("value", ratio >= t), ("trap", ratio <= -t)):
                if pick.sum() < 30:
                    continue
                p0, y = P0[m, j][pick], Y[m, j][pick]
                lift = y.mean() / p0.mean()
                zscore = (y.sum() - p0.sum()) / np.sqrt((p0 * (1 - p0)).sum())
                out.append({"est": label, "key": key, "group": group(key), "thr": t, "side": side, "n": int(pick.sum()),
                            "p_mkt": p0.mean(), "actual": y.mean(), "lift": lift, "z": zscore, "need": REQUIRED[group(key)]})
    return pd.DataFrame(out)


print("\n=== B. Value rule: twin >= market x (1+thr). lift = actual / market-implied; need = lift required to profit at Kral Oran ===")
for label in ("g200", best, f"{best}+s", "lg50"):
    r = rule(preds[label], label)
    v = r[r["side"].eq("value")]
    agg = v.groupby(["group", "thr"]).apply(lambda d: pd.Series({"n": d["n"].sum(), "lift": (d["actual"] * d["n"]).sum() / (d["p_mkt"] * d["n"]).sum(),
                                                                  "need": d["need"].iloc[0]})).round(3)
    print(f"\n-- {label} (value side, pooled by group) --")
    print(agg.unstack("thr").to_string())
    top = v[(v["thr"] == 0.10)].sort_values("z", ascending=False).head(8)
    print("strongest single markets at thr 0.10:")
    print(top[["key", "n", "p_mkt", "actual", "lift", "z", "need"]].round(3).to_string(index=False))
    t = r[r["side"].eq("trap") & r["thr"].eq(0.10)]
    print("trap side (twin <= market x 0.9), pooled lift:", round((t["actual"] * t["n"]).sum() / (t["p_mkt"] * t["n"]).sum(), 3), "n", int(t["n"].sum()))

print("\n=== C. Double agreement combos (twin above market on both legs) ===")
for label in ("g200", f"{best}+s"):
    p = preds[label]
    for legs, combo in ((("over_2.5", "btts_yes"), "btts_yes&over_2.5"), (("home", "btts_yes"), "home&btts_yes"),
                        (("away", "btts_yes"), "away&btts_yes"), (("home", "over_2.5"), "home&over_2.5"), (("under_2.5", "btts_no"), "btts_no&under_2.5")):
        a, b, c = (KEYS.index(k) for k in (*legs, combo))
        for t in (0.0, 0.05, 0.10):
            pick = test & (p[:, a] >= P0[:, a] * (1 + t)) & (p[:, b] >= P0[:, b] * (1 + t))
            p0, y = P0[pick, c], Y[pick, c]
            if len(y) < 30:
                continue
            zscore = (y.sum() - p0.sum()) / np.sqrt((p0 * (1 - p0)).sum())
            print(f"  {label:10s} {combo:20s} thr {t:.2f}: n={len(y):5d} market {p0.mean():.3f} actual {y.mean():.3f} lift {y.mean() / p0.mean():.3f} z {zscore:+.2f} (need {REQUIRED['combo']})")

print("\n=== D. Market-implied price itself: calibration on test (is the baseline honest?) ===")
cal = []
for j, key in enumerate(KEYS):
    m = test & ~np.isnan(Y[:, j])
    cal.append({"key": key, "n": int(m.sum()), "market": P0[m, j].mean(), "actual": Y[m, j].mean()})
print(pd.DataFrame(cal).assign(gap_pts=lambda d: 100 * (d["actual"] - d["market"])).round(3).to_string(index=False))
