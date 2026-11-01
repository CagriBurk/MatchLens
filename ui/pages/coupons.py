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
st.html(views.page(
    f'<p class="ml-sub" style="margin:0 0 4px">{when}Seçim şartı: Model ve İkiz\'in küçüğü (güvenli olasılık) İddaa\'nın marjsız '
    f'yüzdesinden düşük değil. DEĞER: güvenli olasılık × oran ≥ 1. Tahmini tutma, seçimlerin bağımsız olduğu varsayımıyla çarpım.</p>'))

for name in ("blue", "yellow", "red"):
    st.html(views.page(views.coupon_card(name, legs[legs["coupon"].eq(name)])))
st.html(views.page(views.surprise_list(legs[legs["coupon"].eq("surprise")])))
st.html(views.page('<p class="ml-note">Bilgi amaçlı. Backtest\'lerde ne model ne ikizler piyasayı yendi; İddaa marjı (~%15-19) '
                   'her seçimde yeniden ödenir. Kuponların gerçek isabeti Karne\'de izlenecek.</p>'))
