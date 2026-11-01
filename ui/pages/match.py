import streamlit as st

from ui import data, picker, views

record = picker.selected_match("match_pick")
summary = data.twin_summary(record) if data.has_market(record) else None
grid, tops = data.score_grid(record)

st.html(views.page(views.match_header(record, "bulten", "Bülten")))
st.html(views.page(views.three_sources(record)))
st.html(views.page(views.surprise_section(record, summary)))
st.html(views.page(f'<section class="ml-two" style="padding-top:32px">{views.score_section(record, grid, tops)}{views.htft_section(record)}</section>'))
if summary is not None:
    st.page_link("pages/twins.py", label=f"{summary['n']} ikizi incele", icon=":material/arrow_forward:", query_params={"event": record["event_id"]})
