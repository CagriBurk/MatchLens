import streamlit as st

from matchlens import coupons, scorecard
from ui import scorecard_views as sv
from ui import views

log = scorecard.load_predictions()
legs = scorecard.load_coupons()
results = scorecard.coupon_results(legs)

events = log["event_id"].nunique() if len(log) else 0
st.html(views.page(f'<div class="ml-kicker">Karne</div><h1 class="ml-h1">İleriye dönük isabet</h1>'
                   f'<p class="ml-sub">{len(log)} sonuçlanmış tahmin · {events} maç · {len(results)} kupon. '
                   f'Tahminler maç başlamadan kaydedilip donduruluyor; burada sonradan gerçekleşenle kıyaslanıyor.</p>'))

if log.empty:
    st.html(views.page('<div class="ml-empty"><span style="font-size:17px">Henüz sonuçlanan tahmin yok.</span>'
                       '<span class="ml-muted">Maçlar bittikçe sabah güncellemesi sonuçlandırır; ilk satırlar burada belirecek.</span></div>'))
else:
    st.html(views.page(sv.source_section(scorecard.source_table(log))))
    st.html(views.page(sv.market_section(scorecard.market_table(log))))
    source = st.segmented_control("Kaynak", list(sv.SOURCE_LABEL), default="model", key="calib_source",
                                  format_func=lambda s: sv.SOURCE_LABEL[s][0], label_visibility="collapsed") or "model"
    st.html(views.page(sv.calibration_section(scorecard.calibration(log, scorecard.SOURCES[source]), source)))
    st.html(views.page(sv.market_source_section(scorecard.market_source_table(log))))

st.html(views.page(sv.rule_section(scorecard.rule_table(coupons.load_selections()))))
st.html(views.page(sv.coupon_summary_section(scorecard.coupon_summary(results), scorecard.leg_summary(legs))))
st.html(views.page(sv.coupon_history_section(results)))
st.html(views.page('<p class="ml-note">Brier: (olasılık − sonuç)² ortalaması; her zaman %50 diyen bir tahmin 0.25 alır. '
                   'Birkaç yüz tahmin birikmeden kaynaklar arasındaki küçük farklar şans olabilir.</p>'))
