import streamlit as st

from ui import data, picker, views

record = picker.selected_match("twins_pick", priced_only=True)
if not data.has_market(record):
    st.html(views.page(views.match_header(record, f"mac?event={record['event_id']}", "Maç detayı")))
    st.info("Bu maç için Bet365 oranı yok, ikiz aranamaz.")
    st.stop()

summary = data.twin_summary(record)
table = data.twin_list(record)

st.html(views.page(views.twin_header(record, summary)))
st.html(views.page(views.twin_outcomes(record, summary)))
st.html(views.page(views.twin_scores_and_pool(record, summary, table, len(data.twin_finder().pool))))

head_left, head_right = st.columns([3, 2], vertical_alignment="bottom")
with head_left:
    st.html(views.page('<div class="ml-section-head" style="padding-bottom:0"><h2 class="ml-h2">İkiz listesi</h2></div>'))
with head_right:
    order = st.segmented_control("Sıralama", ["dist", "date"], default="dist", key="twin_order", label_visibility="collapsed",
                                 format_func={"dist": "EN YAKIN", "date": "EN YENİ"}.get) or "dist"
sorted_table = table.sort_values("distance" if order == "dist" else "date", ascending=order == "dist")
shown = 200 if st.session_state.get("twin_all") else 25
st.html(views.page(views.twin_table(sorted_table, shown)))
if shown < len(table):
    st.button("Tümünü göster", key="twin_all_btn", on_click=lambda: st.session_state.update(twin_all=True))
