import streamlit as st

from ui import data, views

days = data.snapshot_dates()
if not days:
    st.info("Henüz bülten yok. Günlük güncellemeyi çalıştır: .venv\\Scripts\\python -m matchlens.update")
    st.stop()

top_left, top_right = st.columns([3, 2], vertical_alignment="bottom")
with top_right:
    day = st.segmented_control("Gün", days, default=data.default_day(days), format_func=views.day_short,
                               label_visibility="collapsed", key="day") or data.default_day(days)

records = data.load_day(day)
priced = records[records["market_home"].notna()] if "market_home" in records else records.iloc[0:0]

with top_left:
    st.html(views.page(f'<div class="ml-kicker">Bülten</div><h1 class="ml-h1">{views.day_long(day)}</h1>'))

st.html(views.page(views.legend()))

filter_left, filter_right = st.columns([3, 1], vertical_alignment="center")
leagues = sorted(records["league"].unique())
with filter_left:
    picked = st.pills("Lig", ["all"] + leagues, default="all", format_func=lambda c: "TÜMÜ" if c == "all" else views.league_short(c),
                      label_visibility="collapsed", key="league") or "all"
with filter_right:
    only_odds = st.toggle("Sadece Bet365 oranı olan maçlar", key="only_odds")

shown = records if picked == "all" else records[records["league"].eq(picked)]
if only_odds:
    shown = shown[shown["market_home"].notna()] if "market_home" in shown else shown.iloc[0:0]

st.html(views.page(f'<p class="ml-sub" style="margin:0">{len(records)} maç · {len(priced)} tanesinde Bet365 oranı var · gösterilen {len(shown)}</p>'))
if shown.empty:
    st.html(views.page('<div class="ml-empty"><span>Bu filtreyle maç yok.</span></div>'))
else:
    st.html(views.page(views.bulletin_table(shown, day, data.EDGE)))

hits, near = data.agreements(records)
st.html(views.page(views.agreement_section(hits, near, data.EDGE)))
