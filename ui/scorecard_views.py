import pandas as pd

from matchlens.coupons import split_name
from ui.views import SELECTION_LABEL, SOURCE_NAME, pct, scale_head, selection_label, signed

SELECTION_LABEL.update({"both_halves_btts": "İki yarıda KG", "early_goal_0_15": "0–15 dk gol"})
SOURCE_LABEL = {"model": ("Model", "#38BDF8"), "twin": ("İkiz", "#F59E0B"), "market": ("Piyasa", "#F9FAFB")}
COUPON_SHORT = {"blue": ("Mavi", "#38BDF8"), "yellow": ("Sarı", "#F59E0B"), "red": ("Kırmızı", "#EF4444"), "surprise": ("Sürpriz", "#9CA3AF")}
SIDE_SHORT = {"model": "Model", "twin": "İkiz", None: "Eski"}


def coupon_label(name):
    side, tier = split_name(name)
    label, color = COUPON_SHORT[tier]
    return f"{SIDE_SHORT[side]} · {label}", color


STATUS_LABEL = {"won": '<span style="color:#22C55E;font-weight:700">tuttu</span>', "lost": '<span style="color:#EF4444;font-weight:700">yattı</span>',
                "pending": '<span class="ml-muted">bekliyor</span>'}


def grid(columns, head, rows, min_width=760):
    style = f"grid-template-columns:{columns}"
    head_html = f'<div class="ml-head" style="{style}">{"".join(head)}</div>'
    body = "".join(f'<div class="ml-row ml-mono" style="{style};min-height:44px">{"".join(r)}</div>' for r in rows)
    return f'<div class="ml-scroll"><div style="min-width:{min_width}px">{head_html}{body}</div></div>'


def num(v, digits=3):
    return "—" if v is None or pd.isna(v) else f"{v:.{digits}f}"


def r(text, extra=""):
    return f'<span class="ml-r" style="{extra}">{text}</span>'


def section(title, note, body):
    return (f'<section><div class="ml-section-head"><h2 class="ml-h2">{title}</h2>'
            f'<span class="ml-muted" style="font-size:14px">{note}</span></div>{body}</section>')


def empty(text="Veri yok."):
    return f'<div class="ml-empty"><span>{text}</span></div>'


def source_section(table):
    best = table["brier"].idxmin() if table["brier"].notna().any() else None
    rows = []
    for name, row in table.iterrows():
        label, color = SOURCE_LABEL[name]
        tag = ' <span class="ml-agree-tag" style="font-size:13px">EN İYİ</span>' if name == best else ""
        rows.append([f'<span class="ml-label" style="color:{color};font-weight:600">{label}{tag}</span>', r(int(row["n"])),
                     r(pct(row["mean_p"], 1)), r(pct(row["actual"], 1)), r(num(row["brier"], 4), "font-weight:700"), r(num(row["log_loss"], 4))])
    head = ["<span>Kaynak</span>", r("Tahmin"), r("Ort. olasılık"), r("Gerçekleşen"), r("Brier"), r("Log-loss")]
    body = grid("minmax(180px,1.4fr) repeat(5, minmax(90px,1fr))", head, rows, 760) if table["n"].sum() else empty("Üç kaynağın da tahmin verdiği sonuçlanmış satır yok.")
    return section("Üç kaynak, aynı maçlar", "Üçünün de tahmin verdiği aynı satırlar · düşük skor daha iyi", body)


def market_section(table):
    rows = []
    for market, row in table.sort_values("n", ascending=False).iterrows():
        briers = {s: row.get(f"{s}_brier") for s in SOURCE_LABEL}
        valid = {s: b for s, b in briers.items() if b is not None and not pd.isna(b)}
        best = min(valid, key=valid.get) if len(valid) > 1 else None
        cells = [f'<span class="ml-label">{selection_label(market)}</span>', r(int(row["n"])), r(pct(row["actual"], 1))]
        for s, (_, color) in SOURCE_LABEL.items():
            mark = "font-weight:700;text-decoration:underline solid 2px;text-underline-offset:5px" if s == best else ""
            cells += [r(pct(row.get(f"{s}_mean"), 1), f"color:{color}"), r(num(briers[s], 4), mark)]
        rows.append(cells)
    head = ["<span>Market</span>", r("n"), r("Gerçek")]
    for label, color in SOURCE_LABEL.values():
        head += [r(f"{label} %", f"color:{color}"), r("Brier", f"color:{color}")]
    return section("Market bazında", "Ortalama olasılık ve Brier · altı çizili: o markette en iyi kaynak",
                   grid("minmax(200px,1.6fr) 56px 72px repeat(6, minmax(70px,1fr))", head, rows, 980))


def calibration_section(table, source):
    label, color = SOURCE_LABEL[source]
    rows = []
    for _, row in table.iterrows():
        marker = (f'<div class="ml-strip"><div class="t"></div>'
                  f'<div class="band" style="left:{100 * row["low"]:.0f}%;width:{100 * (row["high"] - row["low"]):.0f}%;background:rgba(156,163,175,0.18)"></div>'
                  f'<div class="p" style="left:{100 * row["actual"]:.1f}%;background:#22C55E"></div>'
                  f'<div class="m" style="left:{100 * row["mean_p"]:.1f}%;background:{color}"></div></div>')
        rows.append([f'<span>%{100 * row["low"]:.0f}–{100 * row["high"]:.0f}</span>', r(int(row["n"])), marker,
                     r(pct(row["mean_p"], 1), f"color:{color}"), r(pct(row["actual"], 1), "color:#22C55E")])
    head = ["<span>Dilim</span>", r("n"), scale_head(), r(label, f"color:{color}"), r("Gerçek", "color:#22C55E")]
    body = grid("90px 56px minmax(280px,1fr) 80px 80px", head, rows, 680) if rows else empty()
    return section("Kalibrasyon", f"{label} bir olasılık dediğinde gerçekte ne oldu · nokta tahmin, yeşil çizgi gerçek", body)


def market_source_section(table):
    rows = []
    for _, row in table.iterrows():
        src = str(row["source"])
        name = SOURCE_NAME.get(src.rstrip("~"), src) + (" (çevrilmiş)" if src.endswith("~") else "")
        rows.append([f'<span class="ml-label">{name}</span>', r(int(row["n"])), r(pct(row["actual"], 1)),
                     r(num(row["brier"], 4)), r(num(row["model_brier_same"], 4), "color:#38BDF8")])
    head = ["<span>Piyasa kaynağı</span>", r("n"), r("Gerçek"), r("Piyasa Brier"), r("Model Brier", "color:#38BDF8")]
    body = grid("minmax(200px,1.4fr) repeat(4, minmax(90px,1fr))", head, rows, 640) if rows else empty()
    return section("Bet365 ve DraftKings", "Aynı satırlarda modelin skoru yanında", body)


def coupon_summary_section(summary, legs):
    rows = []
    for coupon, row in summary.iterrows():
        label, color = coupon_label(coupon)
        leg = legs.loc[coupon] if coupon in legs.index else None
        rows.append([f'<span class="ml-label" style="color:{color};font-weight:600">{label}</span>', r(int(row["coupons"])),
                     r(f'{int(row["won"])}/{int(row["settled"])}'), r(pct(row["hit_rate"], 1), "font-weight:700"),
                     r(pct(row["expected"], 1), "color:#9CA3AF"), r(num(row["avg_odds"], 2)),
                     r(signed(row["roi"]) if pd.notna(row["roi"]) else "—"),
                     r(pct(leg["hit_rate"], 1) if leg is not None else "—"), r(pct(leg["p_safe"], 1) if leg is not None else "—", "color:#9CA3AF")])
    head = ["<span>Kupon</span>", r("Üretilen"), r("Tuttu"), r("Tutma %"), r("Beklenen"), r("Ort. oran"), r("ROI (puan)"),
            r("Seçim isabeti"), r("Beklenen")]
    return section("Kupon karnesi", "Düz 1 birim · beklenen = kuponu seçen kaynağın olasılıkları · Eski = 01.11 kuralı (Model/İkiz küçüğü, İddaa referansı)",
                   grid("minmax(150px,1.2fr) repeat(8, minmax(80px,1fr))", head, rows, 990))


RULE_LABEL = {"model": ("Model ≥ Piyasa", "#38BDF8"), "twin": ("İkiz ≥ Piyasa", "#F59E0B"), "all": ("Hepsi (kural yok)", "#9CA3AF")}
GROUP_LABEL = {"all": "Toplam", "result": "MS 1X2", "double_chance": "Çifte şans", "totals": "Alt/Üst", "btts": "KG",
               "combo": "Kombo", "first_half": "İlk yarı", "special": "İY/MS, 6+, iki yarı"}


def rule_section(table):
    rows = []
    for _, row in table.iterrows():
        label, color = RULE_LABEL[row["rule"]]
        total = row["group"] == "all"
        weight = "font-weight:700" if total else ""
        rows.append([f'<span class="ml-label" style="color:{color};{weight}">{label if total else ""}</span>',
                     f'<span style="font-family:var(--ml-body);{weight}">{GROUP_LABEL[row["group"]]}</span>', r(int(row["n"])),
                     r(pct(row["mean_p"], 1), f"color:{color}"), r(pct(row["mean_ref"], 1)), r(pct(row["actual"], 1), "color:#22C55E;font-weight:700"),
                     r(signed(row["roi"]) if pd.notna(row["roi"]) else "—")])
    head = ["<span>Kural</span>", "<span>Market</span>", r("n"), r("Kaynak %"), r("Piyasa %"), r("Gerçek %", "color:#22C55E"), r("ROI (puan)")]
    body = grid("minmax(150px,1.2fr) minmax(150px,1.2fr) 64px repeat(4, minmax(80px,1fr))", head, rows, 860) if rows else empty(
        "Henüz sonuçlanmış seçim yok. Her sabah İddaa'daki tüm seçimler kaydediliyor; maçlar bittikçe burada birikecek.")
    return section("Kural karnesi: tüm İddaa seçimleri",
                   "Kuponlara girsin girmesin, o günün tüm seçimleri · kaynak piyasadan yüksek dediğinde gerçekte ne oldu · ROI İddaa oranıyla düz 1 birim",
                   body)


def coupon_history_section(results):
    rows = []
    for _, row in results.sort_values(["day", "coupon"], ascending=[False, True]).head(42).iterrows():
        label, color = coupon_label(row["coupon"])
        rows.append([f'<span class="ml-muted">{row["day"]}</span>', f'<span style="color:{color};font-weight:600;font-family:var(--ml-body)">{label}</span>',
                     r(int(row["legs"])), r(f'{row["odds"]:.2f}'), r(pct(row["expected"], 1), "color:#9CA3AF"), r(STATUS_LABEL[row["status"]])])
    head = ["<span>Gün</span>", "<span>Kupon</span>", r("Maç"), r("Oran"), r("Tahmini tutma"), r("Durum")]
    body = grid("110px minmax(140px,1fr) 64px 80px 110px 100px", head, rows, 640) if rows else empty("Henüz kupon yok.")
    return section("Kupon geçmişi", "Son 14 gün", body)
