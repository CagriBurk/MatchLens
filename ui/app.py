import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from ui import views

st.set_page_config(page_title="MatchLens", layout="wide", initial_sidebar_state="collapsed")
st.html(views.theme())

PAGES = Path(__file__).with_name("pages")
navigation = st.navigation(
    [
        st.Page(PAGES / "bulletin.py", title="Bülten", url_path="bulten", default=True),
        st.Page(PAGES / "match.py", title="Maç detayı", url_path="mac"),
        st.Page(PAGES / "twins.py", title="Oran İkizleri", url_path="ikizler"),
        st.Page(PAGES / "coupons.py", title="Kuponlar", url_path="kuponlar"),
        st.Page(PAGES / "scorecard.py", title="Karne", url_path="karne"),
    ],
    position="top",
)
navigation.run()
