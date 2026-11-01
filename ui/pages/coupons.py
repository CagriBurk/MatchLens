from datetime import date

import pandas as pd
import streamlit as st

from matchlens import coupons
from ui import data, views

options = [date.fromisoformat(d) for d in coupons.days()]
if not options:
    st.info("Henüz kupon yok. Kuponlar sabah güncellemesinde üretilir: .venv\\Scripts\\python -m matchlens.update")
    st.stop()

default = data.today() if data.today() in options else options[-1]
left, right = st.columns([3, 2], vertical_alignment="bottom")
with right:
    day = st.segmented_control("Gün", options[-7:], default=default, format_func=views.day_short, key="coupon_day",
                               label_visibility="collapsed") or default
with left:
    st.html(views.page(f'<div class="ml-kicker">Kuponlar</div><h1 class="ml-h1">{views.day_long(day)}</h1>'))

legs = coupons.load(day)
created = pd.Timestamp(legs["created_at"].min()).tz_convert(data.LOCAL_TZ) if len(legs) else None
when = f"Oranlar Nesine/İddaa, kuponun üretildiği an ({created:%H:%M}) itibarıyla. " if created is not None else ""
legacy = legs["coupon"].isin(coupons.LEGACY).any()


def coupon_set(side):
    prefix = "" if side is None else f"{side}_"
    for tier in coupons.TIERS:
        st.html(views.page(views.coupon_card(tier, legs[legs["coupon"].eq(f"{prefix}{tier}")], side)))
    st.html(views.page(views.surprise_list(legs[legs["coupon"].eq(f"{prefix}surprise")], side)))


if legacy:
    st.html(views.page(
        f'<p class="ml-sub" style="margin:0 0 4px">{when}Eski kural (01.11): Model ve İkiz\'in küçüğü İddaa\'nın marjsız yüzdesinden '
        f'düşük değil. Bu günün kuponları eski modelle (ridge 5) üretildi.</p>'))
    coupon_set(None)
else:
    st.html(views.page(
        f'<p class="ml-sub" style="margin:0 0 4px">{when}İki ayrı set: her biri sadece kendi kaynağının olasılığına bakar. '
        f'Seçim şartı: kaynağın olasılığı, Bet365\'in (yoksa DraftKings) marjsız yüzdesinden düşük değil. Bet365 sadece 1X2 ve 2.5 Üst/Alt '
        f'fiyatlıyor; diğer marketlerde piyasa yüzdesi bu oranlardan çözülen gol beklentisiyle hesaplanır (~, yaklaşık). '
        f'DEĞER: olasılık × İddaa oranı ≥ 1. Tahmini tutma, seçimlerin bağımsız olduğu varsayımıyla çarpım.</p>'))
    model_tab, twin_tab = st.tabs(["Modelin seçtikleri", "İkiz oran"])
    with model_tab:
        coupon_set("model")
    with twin_tab:
        coupon_set("twin")

st.html(views.page('<p class="ml-note">Bilgi amaçlı. Backtest\'lerde ne model ne ikizler piyasayı yendi; Bet365 modelden isabetli. '
                   '"Model Bet365\'ten yüksek diyor" çoğu zaman modelin yanıldığı yer olabilir. İddaa marjı (~%15-19) her seçimde '
                   'yeniden ödenir. Kuponların gerçek isabeti Karne\'de izleniyor.</p>'))
