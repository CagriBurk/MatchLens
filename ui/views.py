import re
from html import escape
from pathlib import Path

import numpy as np
import pandas as pd

from data_pipeline.espn.leagues import LEAGUES
from ui import data

THEME = Path(__file__).with_name("theme.css")
COUNTRY = {"eng": "İNG", "esp": "İSP", "ita": "İTA", "ger": "ALM", "fra": "FRA", "tur": "TÜR", "bel": "BEL", "den": "DAN",
           "nor": "NOR", "usa": "ABD", "ned": "HOL", "por": "POR", "sco": "İSK", "gre": "YUN", "aut": "AVU", "sui": "İSV",
           "swe": "İSÇ", "jpn": "JAP", "pol": "POL"}
DAYS = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
DAYS_SHORT = ["PZT", "SAL", "ÇAR", "PER", "CUM", "CMT", "PAZ"]
MONTHS = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
MARKET_LABEL = {"home": "1", "draw": "X", "away": "2", "over_2.5": "Üst 2.5", "btts_yes": "KG Var"}
DOUBLE_CHANCE = {"dc_1x": ("home", "draw"), "dc_12": ("home", "away"), "dc_x2": ("draw", "away")}
MAIN_ROWS = [
    ("{home} kazanır (1)", "home", False), ("Beraberlik (X)", "draw", False), ("{away} kazanır (2)", "away", False),
    ("1X", "dc_1x", True), ("12", "dc_12", False), ("X2", "dc_x2", False),
    ("Üst 1.5", "over_1.5", True), ("Üst 2.5", "over_2.5", False), ("Üst 3.5", "over_3.5", False), ("KG Var", "btts_yes", False),
    ("İlk yarı 0.5 Üst", "ht_over_0.5", True), ("İlk yarı 1.5 Üst", "ht_over_1.5", False),
]
TWIN_ROWS = [
    ("{home} kazanır (1)", "home", False), ("Beraberlik (X)", "draw", False), ("{away} kazanır (2)", "away", False),
    ("Üst 1.5", "over_1.5", True), ("Üst 2.5", "over_2.5", False), ("Üst 3.5", "over_3.5", False), ("KG Var", "btts_yes", False),
    ("İlk yarı 0.5 Üst", "ht_over_0.5", True), ("İlk yarı 1.5 Üst", "ht_over_1.5", False),
]
SURPRISES = [
    ("İki yarıda KG", "both_halves_btts"), ("İki yarıda 1.5 Üst", "both_halves_over_1.5"), ("6+ gol", "goals_6plus"),
    ("0–15 dk gol", "early_goal_0_15"), ("İY/MS 1/2", "htft_1/2"), ("İY/MS 2/1", "htft_2/1"),
]
HTFT = [("İY 1", "1"), ("İY X", "X"), ("İY 2", "2")]
SCORE = re.compile(r"(\d+-\d+)\((\d+)%\)")
SOURCE_SHORT = {"b365": "B365", "dk": "DK"}
SOURCE_NAME = {"b365": "Bet365", "dk": "DraftKings"}

DOT = '<svg width="{s}" height="{s}" viewBox="0 0 12 12" aria-hidden="true"><circle cx="6" cy="6" r="5" fill="#38BDF8"/></svg>'
DIAMOND = '<svg width="{s}" height="{s}" viewBox="0 0 12 12" aria-hidden="true"><rect x="2" y="2" width="8" height="8" transform="rotate(45 6 6)" fill="#F59E0B"/></svg>'
TICK = '<svg width="{s}" height="{s}" viewBox="0 0 12 12" aria-hidden="true"><rect x="5" y="0" width="2" height="12" fill="#F9FAFB"/></svg>'
BAND = '<svg width="22" height="10" viewBox="0 0 22 10" aria-hidden="true"><rect x="0" y="1" width="22" height="8" rx="1" fill="#F59E0B" fill-opacity="0.28"/></svg>'


def theme():
    return f"<style>{THEME.read_text(encoding='utf-8')}</style>"


def page(body):
    return f'<div class="ml">{body}</div>'


def league_short(code):
    country, _, tier = str(code).partition(".")
    return f"{COUNTRY.get(country, country.upper())} {tier}".strip()


def day_long(day):
    return f"{DAYS[day.weekday()]}, {day.day} {MONTHS[day.month - 1]}"


def day_short(day):
    return f"{DAYS_SHORT[day.weekday()]} {day.day}"


def pct(v, digits=0):
    return "—" if v is None or pd.isna(v) else f"{100 * v:.{digits}f}"


def fair_odds(v):
    return "—" if v is None or pd.isna(v) or v <= 0 else f"{1 / v:.2f}"


def signed(v):
    return f"{'+' if v >= 0 else '−'}{abs(100 * v):.1f}"


def teams(record):
    return escape(str(record["home_team"])), escape(str(record["away_team"]))


def source_value(record, prefix, key):
    if key in DOUBLE_CHANCE:
        parts = [data.value(record, f"{prefix}{k}") for k in DOUBLE_CHANCE[key]]
        return None if None in parts else sum(parts)
    return data.value(record, f"{prefix}{key}")


def legend():
    return f"""<section class="ml-legend" aria-label="Kaynaklar">
<div>{DOT.format(s=14)}<div><b class="ml-model">M · Model</b><small>Dixon-Coles. Sadece geçmiş maç verisi, oran görmez.</small></div></div>
<div>{DIAMOND.format(s=14)}<div><b class="ml-twin">İ · Oran İkizleri</b><small>Aynı oranla açılmış 200 geçmiş maçta gerçekte ne oldu. AI yok.</small></div></div>
<div>{TICK.format(s=14)}<div><b>P · Piyasa</b><small>Bet365, yoksa DraftKings; marjı temizlenmiş yüzde. Oranı olmayan maçta İkiz de yok.</small></div></div>
</section>"""


def trio(record, key, edge):
    m, t, p = data.value(record, key), data.value(record, f"twin_{key}"), data.value(record, f"market_{key}")

    def span(v, cls):
        if v is None:
            return '<span class="ml-dim">—</span>'
        up = " ml-up" if p is not None and v - p >= edge else ""
        return f'<span class="{cls}{up}">{pct(v)}</span>'

    approx = "~" if key == "over_2.5" and str(record.get("market_ou_src") or "").endswith("~") else ""
    market = '<span class="ml-dim">—</span>' if p is None else f"<span>{approx}{pct(p)}</span>"
    return f'<div class="ml-trio">{span(m, "ml-model")}{span(t, "ml-twin")}{market}</div>'


def market_prices(record):
    prices = [data.value(record, f"market_odds_{side}") for side in ("home", "draw", "away")]
    return None if None in prices else prices


def market_line(record):
    line, over, under = (data.value(record, f"market_line{k}") for k in ("", "_over", "_under"))
    return None if None in (line, over, under) else (line, over, under, record.get("market_line_src"))


def odds_cell(record):
    prices = market_prices(record)
    if prices is None:
        return '<div class="ml-r ml-mono ml-dim" style="font-size:14px">oran yok</div>'
    tag = SOURCE_SHORT.get(record.get("market_src"), "")
    text = "  ".join(f"{p:.2f}" for p in prices)
    goal = market_line(record)
    sub = ""
    if goal:
        line, over, under, src = goal
        other = f" {SOURCE_SHORT.get(src, '')}" if src != record.get("market_src") else ""
        sub = f"çizgi {line:g} · Ü {over:.2f} A {under:.2f}{other}"
    return (f'<div class="ml-r ml-mono"><div style="font-size:14px;white-space:pre"><span class="ml-muted" style="font-size:11px">{tag}</span>  {text}</div>'
            f'<div class="ml-muted" style="font-size:12px;margin-top:3px">{sub}</div></div>')


def bulletin_table(records, day, edge):
    heads = "".join(
        f'<div class="ml-c"><div style="font-size:16px;color:#F9FAFB">{MARKET_LABEL[k].upper()}</div>'
        f'<div class="ml-trio-head"><span class="ml-model">M</span><span class="ml-twin">İ</span><span>P</span></div></div>'
        for k in data.COMPARE)
    rows, night = [], False
    for _, r in records.iterrows():
        local = r["kickoff_at"]
        if local.date() > day and not night:
            night = True
            next_day = local.date()
            rows.append(f'<div class="ml-divider">Gece · {DAYS[next_day.weekday()]} {next_day.day} {MONTHS[next_day.month - 1]}</div>')
        home, away = teams(r)
        cells = "".join(trio(r, k, edge) for k in data.COMPARE)
        rows.append(
            f'<div class="ml-row"><span class="ml-mono" style="font-size:14px">{local:%H:%M}</span>'
            f'<span class="ml-lg">{league_short(r["league"])}</span>'
            f'<div style="min-width:0"><a class="ml-team" href="mac?event={r["event_id"]}" target="_self">{home} – {away}</a>'
            f'<div class="ml-xg">beklenen gol {r["lam_home"]:.2f} – {r["lam_away"]:.2f}</div></div>'
            f'{cells}{odds_cell(r)}</div>')
    note = (f'<p class="ml-note">Altı çizili kalın sayı: o kaynak piyasanın en az {round(100 * edge)} puan üstünde. '
            f'Piyasa önce Bet365 (B365), yoksa DraftKings (DK). Hiçbir kaynakta 2.5 çizgisi yoksa Üst 2.5 Asya çizgisinden çevrilir (~). '
            f'KG için piyasa oranı yok.</p>')
    return (f'<section class="ml-scroll" aria-label="Maçlar"><div class="ml-bulletin">'
            f'<div class="ml-head"><span>Saat</span><span>Lig</span><span>Maç</span>{heads}<span class="ml-r">Piyasa 1 · X · 2</span></div>'
            f'{"".join(rows)}{note}</div></section>')


def agreement_section(hits, near, edge):
    points = round(100 * edge)
    head = (f'<div class="ml-section-head" style="border-top:1px solid #374151;margin-top:28px">'
            f'<h2 class="ml-h2">İki kaynak birden piyasanın üstünde</h2>'
            f'<span class="ml-muted" style="font-size:14px">Model ve İkiz, piyasayı en az {points} puan aşıyor</span></div>')

    def label(row):
        home, away = teams(row["record"])
        return f"{home} – {away} · {MARKET_LABEL[row['key']]}"

    if hits:
        body = "".join(
            f'<div class="ml-agree-row"><span class="ml-agree-tag">UYUM</span><span style="font-weight:600;min-width:300px">{label(h)}</span>'
            f'<span class="ml-mono" style="font-size:14px"><span class="ml-model">M {pct(h["model"])}</span> &nbsp; '
            f'<span class="ml-twin">İ {pct(h["twin"])}</span> &nbsp; P {pct(h["market"])}</span></div>' for h in hits)
    else:
        closest = "yok" if near is None else (
            f'{label(near)} · M {pct(near["model"])} ({signed(near["model"] - near["market"])}) '
            f'İ {pct(near["twin"])} ({signed(near["twin"] - near["market"])}) P {pct(near["market"])}')
        body = (f'<div class="ml-empty"><span style="font-size:17px">Bu gün için uyum yok.</span>'
                f'<span class="ml-muted ml-mono" style="font-size:14px">en yakın: {closest}</span></div>')
    foot = ('<p class="ml-note">Bilgi amaçlı. Bu kural 2019–2026 backtest\'inde, Bet365 ve piyasa ortalaması oranlarıyla '
            'negatif ROI verdi (yaklaşık marj kadar).</p>')
    return f"<section>{head}{body}{foot}</section>"


def match_header(record, back_href, back_label):
    home, away = teams(record)
    local = record["kickoff_at"]
    league = LEAGUES.get(record["league"], "").upper()
    kicker = f'{league_short(record["league"])} · {league} · {DAYS[local.weekday()].upper()} {local:%H:%M}'
    prices = market_prices(record)
    if prices is None:
        market = '<div class="ml-muted" style="font-size:15px">Bu maç için Bet365 ya da DraftKings oranı yok: İkiz ve Piyasa gösterilemiyor.</div>'
    else:
        boxes = "".join(f"<div><span>{lab}</span><b>{p:.2f}</b></div>" for lab, p in zip(("1", "X", "2"), prices))
        margin = sum(1 / p for p in prices) - 1
        goal_line = market_line(record)
        goal = ""
        if goal_line:
            line, over, under, src = goal_line
            other = f" ({SOURCE_NAME.get(src, src)})" if src != record.get("market_src") else ""
            goal = f"gol çizgisi {line:g} · Ü {over:.2f} · A {under:.2f}{other} · "
        provider = SOURCE_NAME.get(record.get("market_src"), "Piyasa")
        market = (f'<div style="display:flex;flex-direction:column;gap:10px;align-items:flex-end">'
                  f'<span class="ml-kicker" style="font-size:14px">{provider} · maç öncesi</span><div class="ml-odds">{boxes}</div>'
                  f'<span class="ml-mono ml-muted" style="font-size:13px">{goal}marj %{100 * margin:.1f}</span></div>')
    return (f'<a href="{back_href}" target="_self" class="ml-muted" style="display:inline-flex;align-items:center;gap:8px;min-height:44px">'
            f'<svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"><path d="M10 3 5 8l5 5" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>{back_label}</a>'
            f'<div class="ml-match-head"><div><div class="ml-kicker">{kicker}</div>'
            f'<h1 class="ml-teams"><span>{home}</span><i aria-label="karşı">–</i><span>{away}</span></h1>'
            f'<span class="ml-mono ml-muted" style="font-size:14px">model beklenen gol <span class="ml-model">{record["lam_home"]:.2f} – {record["lam_away"]:.2f}</span></span></div>'
            f'{market}</div>')


def strip(m=None, t=None, p=None, band=None):
    parts = ['<div class="t"></div>', '<div class="g" style="left:25%"></div>', '<div class="g" style="left:50%;top:4px;height:14px"></div>', '<div class="g" style="left:75%"></div>']
    if band is not None:
        lo, hi = max(0.0, band[0]), min(1.0, band[1])
        parts.append(f'<div class="band" style="left:{100 * lo:.1f}%;width:{100 * (hi - lo):.1f}%"></div>')
    if p is not None:
        parts.append(f'<div class="p" style="left:{100 * p:.1f}%"></div>')
    if t is not None:
        parts.append(f'<div class="i" style="left:{100 * t:.1f}%"></div>')
    if m is not None:
        parts.append(f'<div class="m" style="left:{100 * m:.1f}%"></div>')
    return f'<div class="ml-strip">{"".join(parts)}</div>'


def scale_head():
    return '<div class="ml-scale"><span>0</span><span>25</span><span>50</span><span>75</span><span>100</span></div>'


def keys(*items):
    return f'<div class="ml-keys">{"".join(f"<span class=ml-key>{icon}{text}</span>" for icon, text in items)}</div>'


def three_sources(record):
    home, away = teams(record)
    rows = []
    for label, key, gap in MAIN_ROWS:
        m, t, p = source_value(record, "", key), source_value(record, "twin_", key), source_value(record, "market_", key)
        if gap:
            rows.append('<div class="ml-gap"></div>')
        rows.append(f'<div class="ml-row"><span class="ml-label">{label.format(home=home, away=away)}</span>{strip(m, t, p)}'
                    f'<span class="ml-r ml-model">{pct(m, 1)}</span><span class="ml-r ml-twin">{pct(t, 1)}</span>'
                    f'<span class="ml-r {"ml-dim" if p is None else ""}">{pct(p, 1)}</span></div>')
    head = (f'<div class="ml-section-head"><h2 class="ml-h2">Üç kaynak, aynı ölçek</h2>'
            f'{keys((DOT.format(s=12), "Model"), (DIAMOND.format(s=12), "İkiz (200 maç)"), (TICK.format(s=12), "Piyasa (marjsız)"))}</div>')
    note = f"Piyasa: {SOURCE_NAME.get(record.get('market_src'), 'yok')}. Çifte şans piyasa yüzdesi marjsız 1X2'den."
    ou_src = str(record.get("market_ou_src") or "")
    goal_line = market_line(record)
    if ou_src.endswith("~") and goal_line:
        note += f" Üst 2.5 piyasası {SOURCE_NAME.get(goal_line[3], '')} {goal_line[0]:g} Asya çizgisinden çevrildi."
    elif ou_src and ou_src != record.get("market_src"):
        note += f" Üst 2.5 piyasası {SOURCE_NAME.get(ou_src, ou_src)} 2.5 çizgisinden."
    note += " Diğer gol marketlerinde piyasa oranı yok."
    return (f'<section>{head}<div class="ml-scroll"><div class="ml-strips">'
            f'<div class="ml-head"><span>Market</span>{scale_head()}<span class="ml-r ml-model">Model</span>'
            f'<span class="ml-r ml-twin">İkiz</span><span class="ml-r">Piyasa</span></div>{"".join(rows)}</div></div>'
            f'<p class="ml-note">{note}</p></section>')


def twin_hits(summary, key):
    if summary is None:
        return None, None
    n = summary.get(f"{key}_n", 0)
    p = summary.get(key)
    return (None, n) if not n or p is None or pd.isna(p) else (int(round(p * n)), n)


def surprise_section(record, summary):
    rows = []
    for label, key in SURPRISES:
        m, t = data.value(record, key), data.value(record, f"twin_{key}")
        hits, n = twin_hits(summary, key)
        seen = "—" if hits is None else f"{hits} / {n}"
        rows.append(f'<div class="ml-row"><span class="ml-label">{label}</span><span class="ml-r ml-model">{pct(m, 1)}</span>'
                    f'<span class="ml-r ml-big">{fair_odds(m)}</span><span class="ml-r ml-twin">{pct(t, 1)}</span>'
                    f'<span class="ml-r ml-big">{fair_odds(t)}</span><span class="ml-r ml-muted" style="font-size:13px">{seen}</span></div>')
    return (f'<section><div class="ml-section-head"><h2 class="ml-h2">Sürpriz marketler</h2>'
            f'<span class="ml-muted" style="font-size:14px">Bet365\'te karşılığı yok · olasılık ve adil oran</span></div>'
            f'<div class="ml-scroll"><div class="ml-surprise"><div class="ml-head"><span>Market</span>'
            f'<span class="ml-r ml-model">Model %</span><span class="ml-r ml-model">Adil oran</span>'
            f'<span class="ml-r ml-twin">İkiz %</span><span class="ml-r ml-twin">Adil oran</span><span class="ml-r">İkizde olan</span></div>'
            f'{"".join(rows)}</div></div><p class="ml-note">Birkaç kez görülmüş bir olay için ikiz yüzdesi kaba bir sinyal; '
            f'birkaç maç farkla adil oranı çok oynar.</p></section>')


def heat_cell(v, peak):
    a = min(1.0, v / peak) if peak else 0.0
    bright = a > 0.55
    fg, weight = ("#0B1120", 700) if bright else ("#E5E7EB", 400)
    text = "·" if v < 0.0005 else f"{100 * v:.1f}"
    return f'<span style="background:rgba(56,189,248,{0.06 + a * 0.84:.2f});color:{fg};font-weight:{weight}">{text}</span>'


def score_section(record, grid, tops):
    home, away = teams(record)
    size = grid.shape[0]
    labels = [str(g) for g in range(size - 1)] + [f"{size - 1}+"]
    peak = grid.max()
    head = '<div class="ml-heat-row ml-muted" style="font-size:12px"><span class="ax"></span>' + "".join(f"<span style='padding:0'>{l}</span>" for l in labels) + "</div>"
    rows = "".join(f'<div class="ml-heat-row"><span class="ax">{labels[g]}</span>{"".join(heat_cell(v, peak) for v in grid[g])}</div>' for g in range(size))
    model_top = "".join(f'<div class="row"><b>{h}-{a}</b><span class="ml-muted">{100 * p:.1f}%</span></div>' for h, a, p in tops)
    twin_scores = SCORE.findall(str(record.get("twin_scores", "")))
    twin_top = "".join(f'<div class="row"><b>{s}</b><span class="ml-muted">{p}%</span></div>' for s, p in twin_scores) or '<span class="ml-dim">—</span>'
    return (f'<div><div class="ml-section-head" style="padding-top:0"><h2 class="ml-h2">Skor matrisi</h2><span class="ml-muted" style="font-size:14px">model · %</span></div>'
            f'<div style="display:flex;gap:10px"><div class="ml-axis" style="writing-mode:vertical-rl;transform:rotate(180deg);text-align:center">{home} golü</div>'
            f'<div class="ml-heat" style="flex:1">{head}{rows}<div class="ml-axis" style="text-align:center;padding-top:6px">{away} golü</div></div></div>'
            f'<div class="ml-tops"><div><div class="ml-kicker ml-model" style="font-size:14px;color:#38BDF8">En olası · model</div>{model_top}</div>'
            f'<div><div class="ml-kicker" style="font-size:14px;color:#F59E0B">En sık · ikiz</div>{twin_top}</div></div></div>')


def htft_section(record):
    head = ('<div class="ml-htft-row ml-axis" style="text-align:center"><span style="text-align:left">İY ↓ MS →</span>'
            '<span>MS 1</span><span>MS X</span><span>MS 2</span></div>')
    rows = []
    for label, first in HTFT:
        cells = []
        for final in ("1", "X", "2"):
            key = f"htft_{first}/{final}"
            m, t = data.value(record, key), data.value(record, f"twin_{key}")
            flip = " flip" if {first, final} == {"1", "2"} else ""
            twin = '<small class="ml-dim">ikiz —</small>' if t is None else f'<small class="ml-twin">ikiz {pct(t, 1)}</small>'
            cells.append(f'<div class="ml-htft-cell{flip}"><b>{pct(m, 1)}</b>{twin}</div>')
        rows.append(f'<div class="ml-htft-row"><span class="ml-axis" style="align-self:center">{label}</span>{"".join(cells)}</div>')
    return (f'<div><div class="ml-section-head" style="padding-top:0"><h2 class="ml-h2">İlk yarı / Maç sonu</h2>'
            f'<span class="ml-muted" style="font-size:14px"><span class="ml-model">model</span> · <span class="ml-twin">ikiz</span> · %</span></div>'
            f'<div class="ml-htft">{head}{"".join(rows)}</div><p class="ml-note">Çerçeveli hücreler geri dönüşler (1/2, 2/1). '
            f'İkinci yarı λ\'sı devre skoruna göre düzeltilmiş.</p></div>')


def twin_header(record, summary):
    home, away = teams(record)
    point = [("1", data.value(record, "market_home")), ("2", data.value(record, "market_away"))]
    if summary["used_over"]:
        point.append(("Ü2.5", data.value(record, "market_over_2.5")))
    values = "".join(f'<span><span class="ml-muted" style="font-size:13px">{k} </span>{100 * v:.1f}</span>' for k, v in point)
    local = record["kickoff_at"]
    return (f'<a href="mac?event={record["event_id"]}" target="_self" class="ml-muted" style="display:inline-flex;align-items:center;gap:8px;min-height:44px">'
            f'<svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"><path d="M10 3 5 8l5 5" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>Maç detayı</a>'
            f'<div class="ml-match-head"><div><div class="ml-kicker ml-twin" style="color:#F59E0B">Oran İkizleri · {summary["n"]} maç</div>'
            f'<h1 class="ml-teams"><span>{home}</span><i aria-label="karşı">–</i><span>{away}</span></h1>'
            f'<span class="ml-muted" style="font-size:16px">{SOURCE_NAME.get(record.get("market_src"), "Piyasa")} fiyatına en çok benzeyen, {local.day} {MONTHS[local.month - 1]}\'dan '
            f'önce oynanmış {summary["n"]} maç. Model yok, sadece gerçek sonuçlar.</span></div>'
            f'<div style="display:flex;flex-direction:column;gap:8px;align-items:flex-end"><span class="ml-kicker" style="font-size:14px">Arama noktası · {SOURCE_NAME.get(record.get("market_src"), "piyasa")} marjsız</span>'
            f'<div class="ml-mono" style="display:flex;gap:28px;font-size:22px">{values}</div></div></div>')


def twin_outcomes(record, summary):
    home, away = teams(record)
    rows, priced, inside = [], 0, 0
    for label, key, gap in TWIN_ROWS:
        t = summary.get(key)
        n = summary.get(f"{key}_n", 0)
        if t is None or pd.isna(t) or not n:
            continue
        ci = data.interval(t, n)
        p = data.value(record, f"market_{key}")
        diff = ""
        if p is not None:
            priced += 1
            inside += abs(t - p) <= ci
            diff = signed(t - p)
        if gap:
            rows.append('<div class="ml-gap"></div>')
        rows.append(f'<div class="ml-row"><span class="ml-label">{label.format(home=home, away=away)}</span>{strip(None, t, p, (t - ci, t + ci))}'
                    f'<span class="ml-r ml-twin" style="font-weight:700">{pct(t, 1)}</span><span class="ml-r ml-muted" style="font-size:13px">±{100 * ci:.1f}</span>'
                    f'<span class="ml-r ml-muted" style="font-size:13px">{int(round(t * n))}/{n}</span>'
                    f'<span class="ml-r {"ml-dim" if p is None else ""}">{pct(p, 1)}</span><span class="ml-r" style="color:#D1D5DB">{diff}</span></div>')
    if priced and inside == priced:
        verdict = "Fiyatı olan tüm sonuçlarda piyasa yüzdesi ikiz belirsizlik bandının içinde: ikizler bu maçta piyasadan ayrışmıyor."
    elif priced:
        verdict = f"{priced - inside} sonuçta piyasa yüzdesi ikiz bandının dışında."
    else:
        verdict = ""
    head = (f'<div class="ml-section-head"><h2 class="ml-h2">{summary["n"]} ikizde ne oldu</h2>'
            f'{keys((DIAMOND.format(s=12), "İkizlerde gerçekleşen"), (BAND, "%95 belirsizlik"), (TICK.format(s=12), "Piyasa beklentisi"))}</div>')
    return (f'<section>{head}<div class="ml-scroll"><div class="ml-twinout"><div class="ml-head"><span>Sonuç</span>{scale_head()}'
            f'<span class="ml-r ml-twin">İkiz</span><span class="ml-r">±</span><span class="ml-r">Maç</span><span class="ml-r">Piyasa</span><span class="ml-r">Fark</span></div>'
            f'{"".join(rows)}</div></div><p style="margin:14px 0 0;font-size:16px;max-width:860px">{verdict}</p>'
            f'<p class="ml-note" style="margin-top:4px">200 maçlık örneklemde bir yüzdenin belirsizliği yaklaşık ±6–7 puan. '
            f'Piyasa çizgisi bandın içindeyse ikizler piyasadan farklı bir şey söylemiyor.</p></section>')


def twin_scores_and_pool(record, summary, table, pool_size):
    scores = SCORE.findall(summary.get("top_scores", ""))
    peak = max((int(p) for _, p in scores), default=1)
    bars = "".join(f'<div class="row"><b style="font-size:17px">{s}</b><div class="track"><div class="fill" style="width:{100 * int(p) / peak:.0f}%"></div></div>'
                   f'<span class="ml-r ml-muted">{p}%</span></div>' for s, p in scores)
    same = int(table["league"].eq(record["league"]).sum())
    axes = "1 · 2 · Ü2.5" if summary["used_over"] else "1 · 2"
    facts = [("Aranan havuz", f"{pool_size:,} maç".replace(",", ".")), ("Uzaklık ölçüsü", axes),
             ("Aynı ligden ikiz", f"{same} / {len(table)}"), ("En uzak ikiz", f"{100 * summary['radius']:.2f} puan")]
    facts_html = "".join(f"<div><span>{k}</span><b>{v}</b></div>" for k, v in facts)
    return (f'<section class="ml-two" style="padding-top:32px"><div><h2 class="ml-h2" style="margin-bottom:14px">En sık skorlar</h2><div class="ml-bars">{bars}</div></div>'
            f'<div><h2 class="ml-h2" style="margin-bottom:14px">Havuz</h2><div class="ml-facts">{facts_html}</div></div></section>')


def result_code(home_goals, away_goals):
    return "1" if home_goals > away_goals else "2" if home_goals < away_goals else "X"


def score_text(h, a):
    return "—" if pd.isna(h) or pd.isna(a) else f"{int(h)}–{int(a)}"


def twin_table(table, shown):
    colors = {"1": "#38BDF8", "X": "#9CA3AF", "2": "#F59E0B"}
    rows = []
    for _, t in table.head(shown).iterrows():
        res = result_code(t["home_goals"], t["away_goals"])
        prices = [t[c] for c in ("o_home", "o_draw", "o_away")]
        odds = " ".join("—" if pd.isna(p) else f"{p:.2f}" for p in prices)
        over = "—" if pd.isna(t["o_over25"]) else f"{t['o_over25']:.2f}"
        home = escape(str(t["home_team"])) if pd.notna(t["home_team"]) else "?"
        away = escape(str(t["away_team"])) if pd.notna(t["away_team"]) else "?"
        rows.append(f'<div class="ml-row"><span class="ml-muted">{t["date"]:%d.%m.%Y}</span><span class="ml-lg">{league_short(t["league"])}</span>'
                    f'<span style="font-family:var(--ml-body);font-size:15px">{home} – {away}</span><span class="ml-r">{odds}</span><span class="ml-r">{over}</span>'
                    f'<span class="ml-r ml-muted">{score_text(t["ht_home"], t["ht_away"])}</span>'
                    f'<span class="ml-r" style="font-weight:700">{score_text(t["home_goals"], t["away_goals"])} <span style="font-weight:500;color:{colors[res]}">{res}</span></span>'
                    f'<span class="ml-r ml-muted">{100 * t["distance"]:.2f}</span></div>')
    return (f'<div class="ml-scroll"><div class="ml-twins"><div class="ml-head"><span>Tarih</span><span>Lig</span><span>Maç</span>'
            f'<span class="ml-r">1 · X · 2</span><span class="ml-r">Ü2.5</span><span class="ml-r">İY</span><span class="ml-r">MS</span><span class="ml-r">Uzaklık</span></div>'
            f'{"".join(rows)}</div></div>'
            f'<p class="ml-note">{min(shown, len(table))} / {len(table)} gösteriliyor · uzaklık: marjsız yüzdeler arasında, puan · '
            f'oranlar kaynağına göre Bet365, piyasa ortalaması veya FootyStats</p>')


RESULT_LABEL = {"home": "MS 1", "draw": "MS X", "away": "MS 2"}
SELECTION_LABEL = {
    **RESULT_LABEL, "dc_1x": "ÇŞ 1-X", "dc_12": "ÇŞ 1-2", "dc_x2": "ÇŞ X-2",
    "btts_yes": "KG Var", "btts_no": "KG Yok", "ht_home": "İY 1", "ht_draw": "İY X", "ht_away": "İY 2",
    "ht_over_0.5": "İY 0.5 Üst", "ht_over_1.5": "İY 1.5 Üst", "goals_6plus": "6+ Gol", "both_halves_over_1.5": "İki yarıda 1.5 Üst",
}
SIDE_NAME = {"model": "Model", "twin": "İkiz", None: "Model ve İkiz"}
COUPON_STYLE = {
    "blue": ("Mavi kupon", "Düşük oran, yüksek güven", "#38BDF8"),
    "yellow": ("Sarı kupon", "Orta oran", "#F59E0B"),
    "red": ("Kırmızı kupon", "Yüksek oran, zor", "#EF4444"),
}


def selection_label(key):
    if key in SELECTION_LABEL:
        return SELECTION_LABEL[key]
    if key.startswith("htft_"):
        return f"İY/MS {key[5:]}"
    if key.startswith(("over_", "under_")):
        side, line = key.split("_")
        return f"{line} {'Üst' if side == 'over' else 'Alt'}"
    if "&" in key:
        return " & ".join(selection_label(part) for part in key.split("&"))
    return key


def leg_status(outcome):
    if outcome is None or pd.isna(outcome):
        return '<span class="ml-dim">—</span>'
    return '<span style="color:#22C55E;font-weight:700">tuttu</span>' if outcome == 1 else '<span style="color:#EF4444;font-weight:700">yattı</span>'


def coupon_status(legs):
    outcomes = legs["outcome"]
    if (outcomes == 0).any():
        return '<span style="color:#EF4444">yattı</span>'
    if outcomes.notna().all() and (outcomes == 1).all():
        return '<span style="color:#22C55E">tuttu</span>'
    return f'<span class="ml-muted">{int(outcomes.notna().sum())}/{len(legs)} sonuçlandı</span>'


def leg_rows(legs, show_status=True):
    rows = []
    for _, leg in legs.iterrows():
        local = pd.Timestamp(leg["kickoff_utc"]).tz_convert(data.LOCAL_TZ)
        value = leg["p_safe"] * leg["odds"]
        tag = '<span class="ml-agree-tag" style="font-size:13px">DEĞER</span>' if value >= 1 else f'<span class="ml-dim" style="font-size:12px">×{value:.2f}</span>'
        book = "—" if pd.isna(leg.get("p_book")) else pct(leg["p_book"])
        ref = leg.get("p_ref")
        approx = '<span class="ml-dim">~</span>' if str(leg.get("ref_src") or "").endswith("~") else ""
        reference = "—" if ref is None or pd.isna(ref) else f"{approx}{pct(ref)}"
        status = leg_status(leg.get("outcome")) if show_status else ""
        rows.append(
            f'<div class="ml-row" style="min-height:52px"><span class="ml-mono ml-muted" style="font-size:13px">{local:%H:%M}</span>'
            f'<span class="ml-lg">{league_short(leg["league"])}</span>'
            f'<a href="mac?event={leg["event_id"]}" target="_self" style="font-weight:600">{escape(str(leg["home_team"]))} – {escape(str(leg["away_team"]))}</a>'
            f'<span style="font-weight:600">{selection_label(leg["key"])}</span>'
            f'<span class="ml-r ml-mono ml-big">{leg["odds"]:.2f}</span>'
            f'<span class="ml-r ml-mono ml-model">{pct(leg["p_model"])}</span><span class="ml-r ml-mono ml-twin">{pct(leg["p_twin"])}</span>'
            f'<span class="ml-r ml-mono">{reference}</span><span class="ml-r ml-mono ml-muted">{book}</span><span class="ml-r">{tag}</span><span class="ml-r">{status}</span></div>')
    return "".join(rows)


def leg_head():
    return ('<div class="ml-head"><span>Saat</span><span>Lig</span><span>Maç</span><span>Seçim</span><span class="ml-r">İddaa</span>'
            '<span class="ml-r ml-model">Model</span><span class="ml-r ml-twin">İkiz</span><span class="ml-r">Piyasa %</span><span class="ml-r">İddaa %</span>'
            '<span class="ml-r">P×O</span><span class="ml-r">Sonuç</span></div>')


def coupon_card(tier, legs, side=None):
    title, subtitle, color = COUPON_STYLE[tier]
    reference = "İddaa'nın" if side is None else "Bet365/DraftKings'in"
    head = (f'<div style="display:flex;flex-wrap:wrap;align-items:baseline;justify-content:space-between;gap:8px 24px;padding:18px 0 12px;border-top:3px solid {color}">'
            f'<div><h2 class="ml-h2" style="color:{color}">{title}</h2><span class="ml-muted" style="font-size:14px">{subtitle}</span></div>')
    if legs.empty:
        return (f'<section style="padding-top:28px">{head}</div><div class="ml-empty"><span>Bugün bu kupon için uygun seçim çıkmadı.</span>'
                f'<span class="ml-muted" style="font-size:14px">{SIDE_NAME[side]}, oran aralığındaki hiçbir seçimde {reference} marjsız yüzdesine ulaşmadı.</span></div></section>')
    odds = float(np.prod(legs["odds"]))
    hit = float(np.prod(legs["p_safe"]))
    valued = int((legs["p_safe"] * legs["odds"] >= 1).sum())
    stats = (f'<div class="ml-mono" style="display:flex;flex-wrap:wrap;gap:8px 32px;font-size:15px">'
             f'<span><span class="ml-muted" style="font-size:13px">toplam oran </span><b style="font-size:22px">{odds:.2f}</b></span>'
             f'<span><span class="ml-muted" style="font-size:13px">tahmini tutma </span><b style="font-size:22px">%{100 * hit:.1f}</b></span>'
             f'<span><span class="ml-muted" style="font-size:13px">maç </span><b style="font-size:22px">{len(legs)}</b></span>'
             f'<span><span class="ml-muted" style="font-size:13px">değerli </span><b style="font-size:22px">{valued}/{len(legs)}</b></span>'
             f'<span style="align-self:center">{coupon_status(legs)}</span></div></div>')
    return (f'<section style="padding-top:28px">{head}{stats}<div class="ml-scroll"><div class="ml-coupon">'
            f'{leg_head()}{leg_rows(legs)}</div></div></section>')


def surprise_list(legs, side=None):
    basis = "Model ve İkiz'in güvenli olasılığı" if side is None else f"{SIDE_NAME[side]} olasılığı (Bet365/DK'dan düşük değil)"
    head = ('<div class="ml-section-head" style="border-top:3px solid #9CA3AF;margin-top:28px"><div><h2 class="ml-h2">Sürpriz adaylar</h2>'
            f'<span class="ml-muted" style="font-size:14px">Kupon değil; sistem kuponu için havuz. {basis} × İddaa oranına göre sıralı.</span></div></div>')
    if legs.empty:
        return f'<section>{head}<div class="ml-empty"><span>Bugün aday yok.</span></div></section>'
    return f'<section>{head}<div class="ml-scroll"><div class="ml-coupon">{leg_head()}{leg_rows(legs)}</div></div></section>'
