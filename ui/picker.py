import pandas as pd
import streamlit as st

from ui import data, views


def label(record):
    home, away = record["home_team"], record["away_team"]
    return f'{views.day_short(record["kickoff_at"].date())} {record["kickoff_at"]:%H:%M} · {views.league_short(record["league"])} · {home} – {away}'


def selected_match(key, priced_only=False):
    matches = data.upcoming_matches()
    event = st.query_params.get("event")
    if event and (matches.empty or event not in set(matches["event_id"])):
        past = data.find_match(event)
        if past is not None:
            matches = pd.concat([pd.DataFrame([past]), matches], ignore_index=True)
    if priced_only and not matches.empty and "market_home" in matches:
        matches = matches[matches["market_home"].notna() | matches["event_id"].eq(event)]
    if matches.empty:
        st.info("Gösterilecek maç yok. Günlük güncellemeyi çalıştır: .venv\\Scripts\\python -m matchlens.update")
        st.stop()
    options = list(matches["event_id"])
    labels = {r["event_id"]: label(r) for _, r in matches.iterrows()}
    choice = st.selectbox("Maç", options, index=options.index(event) if event in options else 0,
                          format_func=labels.get, key=key, label_visibility="collapsed")
    if choice != event:
        st.query_params["event"] = choice
    return matches[matches["event_id"].eq(choice)].iloc[0]
