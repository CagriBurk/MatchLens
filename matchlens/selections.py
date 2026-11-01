import numpy as np

RESULTS = ("home", "draw", "away")
LINES = (1.5, 2.5, 3.5, 4.5)
COMBOS = (
    [f"{r}&btts_{s}" for r in RESULTS for s in ("yes", "no")]
    + [f"{r}&{side}_{line}" for r in RESULTS for line in (1.5, 2.5) for side in ("over", "under")]
    + [f"btts_{s}&{side}_2.5" for s in ("yes", "no") for side in ("over", "under")]
)
HTFT = [f"htft_{a}/{b}" for a in ("1", "X", "2") for b in ("1", "X", "2")]


def full_time(hg, ag):
    total = hg + ag
    out = {"home": hg > ag, "draw": hg == ag, "away": hg < ag}
    out.update({"dc_1x": hg >= ag, "dc_12": hg != ag, "dc_x2": hg <= ag})
    for line in LINES:
        out[f"over_{line}"] = total > line
        out[f"under_{line}"] = total < line
    out["btts_yes"] = (hg > 0) & (ag > 0)
    out["btts_no"] = ~out["btts_yes"] if isinstance(out["btts_yes"], np.ndarray) else not out["btts_yes"]
    out["goals_6plus"] = total >= 6
    for combo in COMBOS:
        left, right = combo.split("&")
        out[combo] = out[left] & out[right]
    return out


def half_time(hg, ag, ht_h, ht_a):
    sh_h, sh_a = hg - ht_h, ag - ht_a
    ht_sign, ft_sign = np.sign(ht_h - ht_a), np.sign(hg - ag)
    out = {"ht_home": ht_h > ht_a, "ht_draw": ht_h == ht_a, "ht_away": ht_h < ht_a,
           "ht_over_0.5": ht_h + ht_a > 0.5, "ht_over_1.5": ht_h + ht_a > 1.5,
           "both_halves_over_1.5": (ht_h + ht_a >= 2) & (sh_h + sh_a >= 2),
           "both_halves_btts": (ht_h > 0) & (ht_a > 0) & (sh_h > 0) & (sh_a > 0)}
    signs = {"1": 1, "X": 0, "2": -1}
    for key in HTFT:
        first, final = key[5:].split("/")
        out[key] = (ht_sign == signs[first]) & (ft_sign == signs[final])
    return out


def matrix_probs(matrix, keys=COMBOS):
    goals = np.arange(matrix.shape[0])
    outcomes = full_time(goals[:, None], goals[None, :])
    return {key: float((matrix * outcomes[key]).sum()) for key in keys}
