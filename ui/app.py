import html
from typing import Any

import pandas as pd
import requests
import streamlit as st


st.set_page_config(
    page_title="MatchLens Analiz Merkezi",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)


DEFAULT_API_BASE_URL = "http://127.0.0.1:8000"


TEXT = {
    "tr": {
        "app_name": "MatchLens",
        "tagline": "Futbol Veri & Analiz Platformu",
        "overview": "Genel Bakış",
        "match_analysis": "Detaylı Maç Analizi",
        "team_form": "Takım Form Merkezi",
        "settings": "Ayarlar",
        "api_url": "FastAPI adresi",
        "menu": "Menü",
        "limit": "Maç limiti",
        "refresh": "Verileri yenile",
    },
    "en": {
        "app_name": "MatchLens",
        "tagline": "Football Data & Analysis Platform",
        "overview": "Overview",
        "match_analysis": "Match Analysis",
        "team_form": "Team Form Center",
        "settings": "Settings",
        "api_url": "FastAPI URL",
        "menu": "Menu",
        "limit": "Match limit",
        "refresh": "Refresh data",
    },
}


def inject_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --ml-bg: #0b1120;
            --ml-surface: #111827;
            --ml-surface-2: #1f2937;
            --ml-border: #273244;
            --ml-text: #f9fafb;
            --ml-muted: #9ca3af;
            --ml-green: #22c55e;
            --ml-blue: #38bdf8;
            --ml-amber: #f59e0b;
            --ml-red: #ef4444;
        }

        .stApp {
            background:
                radial-gradient(circle at top left, rgba(34, 197, 94, 0.10), transparent 34rem),
                radial-gradient(circle at top right, rgba(56, 189, 248, 0.10), transparent 30rem),
                var(--ml-bg);
        }

        section[data-testid="stSidebar"] {
            background: #070d19;
            border-right: 1px solid var(--ml-border);
        }

        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            max-width: 1400px;
        }

        h1, h2, h3 {
            letter-spacing: 0;
        }

        div[data-testid="stMetric"] {
            background: linear-gradient(180deg, rgba(31, 41, 55, 0.96), rgba(17, 24, 39, 0.96));
            border: 1px solid var(--ml-border);
            border-radius: 8px;
            padding: 16px 18px;
            min-height: 116px;
            box-shadow: 0 18px 38px rgba(0, 0, 0, 0.20);
        }

        div[data-testid="stMetricLabel"] {
            color: var(--ml-muted);
        }

        div[data-testid="stMetricValue"] {
            color: var(--ml-text);
            font-weight: 750;
        }

        .ml-hero {
            border: 1px solid var(--ml-border);
            border-radius: 8px;
            padding: 22px 24px;
            background:
                linear-gradient(135deg, rgba(34, 197, 94, 0.14), rgba(56, 189, 248, 0.08)),
                rgba(17, 24, 39, 0.88);
            margin-bottom: 18px;
        }

        .ml-kicker {
            color: var(--ml-green);
            font-size: 0.78rem;
            font-weight: 800;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            margin-bottom: 6px;
        }

        .ml-hero h1 {
            font-size: 2.1rem;
            margin: 0;
            line-height: 1.15;
        }

        .ml-hero p {
            margin: 8px 0 0;
            color: var(--ml-muted);
            max-width: 780px;
        }

        .ml-panel {
            border: 1px solid var(--ml-border);
            border-radius: 8px;
            padding: 18px;
            background: rgba(17, 24, 39, 0.92);
            min-height: 100%;
        }

        .ml-card {
            border: 1px solid var(--ml-border);
            border-radius: 8px;
            padding: 16px;
            background: rgba(15, 23, 42, 0.92);
            margin-bottom: 12px;
        }

        .ml-card-title {
            color: var(--ml-text);
            font-weight: 750;
            font-size: 1rem;
            margin-bottom: 6px;
        }

        .ml-muted {
            color: var(--ml-muted);
            font-size: 0.92rem;
        }

        .ml-pill {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            border-radius: 999px;
            padding: 4px 10px;
            font-size: 0.78rem;
            font-weight: 800;
            border: 1px solid transparent;
            white-space: nowrap;
        }

        .ml-pill-green {
            color: #bbf7d0;
            background: rgba(34, 197, 94, 0.15);
            border-color: rgba(34, 197, 94, 0.30);
        }

        .ml-pill-blue {
            color: #bae6fd;
            background: rgba(56, 189, 248, 0.14);
            border-color: rgba(56, 189, 248, 0.28);
        }

        .ml-pill-amber {
            color: #fde68a;
            background: rgba(245, 158, 11, 0.14);
            border-color: rgba(245, 158, 11, 0.28);
        }

        .ml-pill-red {
            color: #fecaca;
            background: rgba(239, 68, 68, 0.14);
            border-color: rgba(239, 68, 68, 0.28);
        }

        .ml-analysis-box {
            border-left: 4px solid var(--ml-green);
            border-radius: 8px;
            padding: 18px;
            background: rgba(34, 197, 94, 0.10);
            margin: 8px 0 18px;
        }

        .ml-analysis-box.warning {
            border-left-color: var(--ml-amber);
            background: rgba(245, 158, 11, 0.10);
        }

        .ml-analysis-box.info {
            border-left-color: var(--ml-blue);
            background: rgba(56, 189, 248, 0.10);
        }

        .ml-scoreboard {
            display: grid;
            grid-template-columns: 1fr auto 1fr;
            align-items: center;
            gap: 18px;
            border: 1px solid var(--ml-border);
            border-radius: 8px;
            padding: 18px;
            background: rgba(17, 24, 39, 0.94);
            margin: 14px 0;
        }

        .ml-team {
            font-size: 1.35rem;
            font-weight: 800;
            line-height: 1.2;
        }

        .ml-vs {
            color: var(--ml-muted);
            font-weight: 800;
            border: 1px solid var(--ml-border);
            border-radius: 999px;
            padding: 8px 12px;
            background: rgba(31, 41, 55, 0.88);
        }

        div[data-testid="stDataFrame"] {
            border: 1px solid var(--ml-border);
            border-radius: 8px;
            overflow: hidden;
        }

        .stButton > button {
            border-radius: 8px;
            font-weight: 750;
            min-height: 42px;
        }

        @media (max-width: 800px) {
            .ml-scoreboard {
                grid-template-columns: 1fr;
                text-align: center;
            }
            .ml-hero h1 {
                font-size: 1.65rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def esc(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def as_percent(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "-"
    if number <= 1:
        number *= 100
    return f"%{number:.0f}"


def as_number(value: Any, digits: int = 2) -> str:
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return "-"


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def get_first(data: dict[str, Any], keys: list[str], default: Any = "-") -> Any:
    for key in keys:
        if key in data and data[key] not in (None, ""):
            return data[key]
    return default


def api_get(base_url: str, endpoint: str, params: dict[str, Any] | None = None) -> Any:
    response = requests.get(
        f"{base_url.rstrip('/')}{endpoint}",
        params=params,
        timeout=8,
    )
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=60, show_spinner=False)
def cached_api_get(base_url: str, endpoint: str, params: tuple[tuple[str, Any], ...]) -> Any:
    return api_get(base_url, endpoint, dict(params))


def render_hero(title: str, subtitle: str, kicker: str = "MATCHLENS") -> None:
    st.markdown(
        f"""
        <div class="ml-hero">
            <div class="ml-kicker">{esc(kicker)}</div>
            <h1>{esc(title)}</h1>
            <p>{esc(subtitle)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_card(title: str, body: str, pill: str | None = None, tone: str = "blue") -> None:
    pill_html = ""
    if pill:
        pill_html = f'<span class="ml-pill ml-pill-{esc(tone)}">{esc(pill)}</span>'
    st.markdown(
        f"""
        <div class="ml-card">
            <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;">
                <div class="ml-card-title">{esc(title)}</div>
                {pill_html}
            </div>
            <div class="ml-muted">{esc(body)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_scoreboard(data: dict[str, Any]) -> None:
    home = get_first(data, ["home_club_name", "home_team_name", "home_name"], f"Ev Sahibi #{get_first(data, ['home_club_id'])}")
    away = get_first(data, ["away_club_name", "away_team_name", "away_name"], f"Deplasman #{get_first(data, ['away_club_id'])}")
    score = get_first(data, ["score", "result", "final_score"], "VS")
    league = get_first(data, ["league", "competition_name", "competition"], "Lig bilgisi yok")
    date = get_first(data, ["date", "match_date", "game_date"], "Tarih yok")

    st.markdown(
        f"""
        <div class="ml-scoreboard">
            <div>
                <div class="ml-muted">Ev Sahibi</div>
                <div class="ml-team">{esc(home)}</div>
            </div>
            <div class="ml-vs">{esc(score)}</div>
            <div style="text-align:right;">
                <div class="ml-muted">Deplasman</div>
                <div class="ml-team">{esc(away)}</div>
            </div>
        </div>
        <div class="ml-muted" style="margin-top:-6px;margin-bottom:14px;">{esc(league)} Â· {esc(date)}</div>
        """,
        unsafe_allow_html=True,
    )


def analysis_tone(text: str) -> str:
    lowered = text.lower()
    if any(word in lowered for word in ["risk", "denk", "belirsiz", "dikkat"]):
        return "warning"
    if any(word in lowered for word in ["favori", "avantaj", "güçlü", "guclu"]):
        return "success"
    return "info"


def render_analysis(text: str) -> None:
    tone = analysis_tone(text)
    st.markdown(
        f"""
        <div class="ml-analysis-box {tone if tone != "success" else ""}">
            <div class="ml-kicker">Kural Tabanlı Analiz</div>
            <div style="font-size:1.05rem;line-height:1.55;">{esc(text)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def prepare_dataframe(rows: list[dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    if df.empty:
        return df

    preferred = [
        "match_id",
        "game_id",
        "date",
        "match_date",
        "league",
        "competition_name",
        "home_club_name",
        "home_team_name",
        "away_club_name",
        "away_team_name",
        "score",
        "form_advantage",
        "form_advantage_score",
        "btts_tendency",
        "over_2_5_tendency",
        "analysis",
    ]
    ordered = [column for column in preferred if column in df.columns]
    remaining = [column for column in df.columns if column not in ordered]
    return df[ordered + remaining]


def page_overview(api_base_url: str, match_limit: int) -> None:
    render_hero(
        "Genel Bakış",
        "Maç havuzunu, form avantajlarını ve gol eğilimlerini tek ekranda tarayın.",
    )

    try:
        rows = cached_api_get(api_base_url, "/features", (("limit", match_limit),))
    except requests.RequestException as exc:
        st.error(f"API bağlantı hatası: {exc}")
        return

    if not rows:
        st.warning("Seçili filtrelerle eŞleŞen maç bulunamadı.")
        return

    df = prepare_dataframe(rows)

    total_matches = len(df)
    analyzed_matches = int(df["analysis"].notna().sum()) if "analysis" in df.columns else 0
    high_form = 0
    risky = 0

    form_column = "form_advantage_score" if "form_advantage_score" in df.columns else "form_advantage"
    if form_column in df.columns:
        numeric_form = pd.to_numeric(df[form_column], errors="coerce")
        high_form = int((numeric_form.abs() >= 0.4).sum())

    if "analysis" in df.columns:
        risky = int(df["analysis"].astype(str).str.lower().str.contains("risk|denk|belirsiz", regex=True).sum())

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Toplam Maç", total_matches)
    col2.metric("Analiz Hazır", analyzed_matches)
    col3.metric("Güçlü Form Sinyali", high_form)
    col4.metric("Riskli / Denk", risky)

    left, right = st.columns([2.2, 1], gap="large")

    with left:
        st.subheader("Maç Listesi")
        st.dataframe(df, use_container_width=True, height=560, hide_index=True)

    with right:
        st.subheader("Hızlı Sinyaller")
        tabs = st.tabs(["Favoriler", "Gol", "Risk"])

        with tabs[0]:
            if form_column in df.columns:
                top = df.assign(_form=pd.to_numeric(df[form_column], errors="coerce")).sort_values("_form", ascending=False).head(4)
                for _, row in top.iterrows():
                    match_id = get_first(row.to_dict(), ["match_id", "game_id"])
                    form_value = as_number(row.get(form_column), 2)
                    render_card(f"Maç #{match_id}", f"Form avantaj skoru: {form_value}", "FORM", "green")
            else:
                st.info("Form avantaj kolonu bulunamadı.")

        with tabs[1]:
            goal_column = "over_2_5_tendency"
            if goal_column in df.columns:
                top = df.assign(_goal=pd.to_numeric(df[goal_column], errors="coerce")).sort_values("_goal", ascending=False).head(4)
                for _, row in top.iterrows():
                    match_id = get_first(row.to_dict(), ["match_id", "game_id"])
                    render_card(f"Maç #{match_id}", f"2.5 üst eğilimi: {as_percent(row.get(goal_column))}", "ÜST", "blue")
            else:
                st.info("2.5 üst eğilimi kolonu bulunamadı.")

        with tabs[2]:
            if "analysis" in df.columns:
                risk_rows = df[df["analysis"].astype(str).str.lower().str.contains("risk|denk|belirsiz", regex=True)].head(4)
                if risk_rows.empty:
                    st.success("Belirgin risk etiketi bulunmadı.")
                for _, row in risk_rows.iterrows():
                    match_id = get_first(row.to_dict(), ["match_id", "game_id"])
                    render_card(f"Maç #{match_id}", str(row.get("analysis", "-")), "RİSK", "amber")
            else:
                st.info("Analiz özeti kolonu bulunamadı.")


def page_match_analysis(api_base_url: str) -> None:
    render_hero(
        "Detaylı Maç Analizi",
        "Maç ID girin; form avantajı, gol eğilimleri ve kural tabanlı yorumu aynı ekranda okuyun.",
    )

    input_col, hint_col = st.columns([1, 2], gap="large")
    with input_col:
        game_id = st.text_input("Maç ID", value="2225443", placeholder="Örn: 2225443")
        analyze = st.button("Analizi Getir", type="primary", use_container_width=True)

    with hint_col:
        st.markdown(
            """
            <div class="ml-panel">
                <div class="ml-card-title">Okuma sırası</div>
                <div class="ml-muted">
                    Önce form avantajını, sonra KG Var ve 2.5 Üst eğilimlerini kontrol edin.
                    En sonda MatchLens yorumunu veriyle birlikte değerlendirin.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if not analyze:
        st.info("Analiz ekranını açmak için bir maç ID girip butona basın.")
        return

    if not game_id.strip():
        st.warning("Lütfen geçerli bir maç ID girin.")
        return

    try:
        data = api_get(api_base_url, f"/matches/{game_id.strip()}/analysis")
    except requests.RequestException as exc:
        st.error(f"API bağlantı hatası: {exc}")
        return

    if data is None:
        st.error("Bu ID'ye ait bir maç bulunamadı.")
        return

    render_scoreboard(data)

    form_advantage = get_first(data, ["form_advantage_score", "form_advantage"])
    btts = get_first(data, ["btts_tendency", "btts_rate"])
    over_25 = get_first(data, ["over_2_5_tendency", "total_over_2_5"])

    col1, col2, col3 = st.columns(3)
    col1.metric("Form Avantajı", as_number(form_advantage, 2), help="Pozitif değer ev sahibi lehine, negatif değer deplasman lehine yorumlanabilir.")
    col2.metric("KG Var Eğilimi", as_percent(btts))
    col3.metric("2.5 Üst Eğilimi", as_percent(over_25))

    analysis = str(get_first(data, ["analysis", "ai_analysis", "comment"], "Analiz metni bulunamadı."))
    render_analysis(analysis)

    tab1, tab2, tab3 = st.tabs(["Özet", "Ham Veri", "Kural Okuması"])

    with tab1:
        c1, c2 = st.columns(2)
        with c1:
            render_card("Ev Sahibi", f"Club ID: {get_first(data, ['home_club_id'])}", "HOME", "green")
        with c2:
            render_card("Deplasman", f"Club ID: {get_first(data, ['away_club_id'])}", "AWAY", "blue")

    with tab2:
        st.dataframe(pd.DataFrame([data]), use_container_width=True, hide_index=True)

    with tab3:
        st.markdown(
            """
            - Form avantajı yüksekse favori etiketi güçlenir.
            - KG Var eğilimi yüksekse iki tarafın da skor üretme ihtimali öne çıkar.
            - 2.5 Üst eğilimi yüksekse maçın gol potansiyeli artar.
            - Metrikler birbirini desteklemiyorsa analiz riskli olarak okunmalıdır.
            """
        )


def page_team_form(api_base_url: str) -> None:
    render_hero(
        "Takım Form Merkezi",
        "Takımların son dönem performansını, puan üretimini ve gol eğilimlerini inceleyin.",
    )

    col1, col2 = st.columns([1, 2], gap="large")
    with col1:
        club_id = st.text_input("Takım / Club ID", value="289", placeholder="Örn: 289")
        fetch = st.button("Form Durumunu Getir", type="primary", use_container_width=True)

    with col2:
        st.markdown(
            """
            <div class="ml-panel">
                <div class="ml-card-title">Form yorumu</div>
                <div class="ml-muted">
                    Bu ekran takımın puan ritmini, maç başı üretimini ve gol marketlerine yatkınlığını
                    hızlıca okumak için tasarlandı.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if not fetch:
        st.info("Bir takım ID girip form raporunu çağırın.")
        return

    if not club_id.strip():
        st.warning("Lütfen geçerli bir takım ID girin.")
        return

    try:
        data = api_get(api_base_url, f"/teams/{club_id.strip()}/form")
    except requests.RequestException as exc:
        st.error(f"API bağlantı hatası: {exc}")
        return

    if data is None:
        st.error("Bu ID'ye ait takım form verisi bulunamadı.")
        return

    st.subheader(f"Takım #{get_first(data, ['club_id'], club_id)} Form Raporu")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Oynanan Maç", get_first(data, ["matches_played"]))
    c2.metric("Galibiyet", get_first(data, ["wins"]))
    c3.metric("Beraberlik", get_first(data, ["draws"]))
    c4.metric("Mağlubiyet", get_first(data, ["loses", "losses"]))

    e1, e2, e3 = st.columns(3)
    e1.metric("Maç BaŞı Puan", as_number(get_first(data, ["average_point_per_game", "ppg"]), 2))
    e2.metric("KG Var Oranı", as_percent(get_first(data, ["btts_rate", "btts_tendency"])))
    e3.metric("2.5 Üst Oranı", as_percent(get_first(data, ["total_over_2_5", "over_2_5_tendency"])))

    tab1, tab2 = st.tabs(["Eğilimler", "Ham Veri"])

    with tab1:
        ppg = get_first(data, ["average_point_per_game", "ppg"], 0)
        btts = get_first(data, ["btts_rate", "btts_tendency"], 0)
        over_25 = get_first(data, ["total_over_2_5", "over_2_5_tendency"], 0)
        chart_df = pd.DataFrame(
            {
                "Metrik": ["PPG", "KG Var", "2.5 Üst"],
                "Değer": [
                    to_float(ppg),
                    to_float(btts) * 100 if to_float(btts) <= 1 else to_float(btts),
                    to_float(over_25) * 100 if to_float(over_25) <= 1 else to_float(over_25),
                ],
            }
        )
        st.bar_chart(chart_df, x="Metrik", y="Değer", use_container_width=True)

    with tab2:
        st.dataframe(pd.DataFrame([data]), use_container_width=True, hide_index=True)


def page_settings(api_base_url: str) -> None:
    render_hero(
        "Ayarlar",
        "API bağlantısını ve oturum tercihlerini buradan kontrol edin.",
    )

    st.code(f"Mevcut API adresi: {api_base_url}", language="text")

    try:
        api_get(api_base_url, "/features", {"limit": 1})
        st.success("API bağlantısı baŞarılı.")
    except requests.RequestException as exc:
        st.error(f"API bağlantısı baŞarısız: {exc}")


def render_sidebar() -> tuple[str, str, int]:
    st.sidebar.markdown(
        """
        <div style="padding:10px 0 14px;">
            <div style="font-size:1.45rem;font-weight:850;color:#f9fafb;">MatchLens</div>
            <div style="color:#9ca3af;font-size:0.88rem;">Futbol Veri & Analiz Platformu</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    language = st.sidebar.radio(
        "Dil",
        options=["tr", "en"],
        index=0,
        horizontal=True,
        format_func=lambda value: "Türkçe" if value == "tr" else "English",
    )
    t = TEXT[language]

    page = st.sidebar.radio(
        t["menu"],
        [t["overview"], t["match_analysis"], t["team_form"], t["settings"]],
    )

    st.sidebar.divider()
    api_base_url = st.sidebar.text_input(t["api_url"], value=DEFAULT_API_BASE_URL)
    match_limit = st.sidebar.slider(t["limit"], min_value=10, max_value=200, value=50, step=10)

    if st.sidebar.button(t["refresh"], use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.sidebar.divider()
    st.sidebar.caption("FastAPI açık değilse ekranlar veri yerine bağlantı uyarısı gösterir.")

    return page, api_base_url, match_limit


def main() -> None:
    inject_css()
    page, api_base_url, match_limit = render_sidebar()

    labels = TEXT["tr"]
    if page in (TEXT["tr"]["overview"], TEXT["en"]["overview"]):
        page_overview(api_base_url, match_limit)
    elif page in (TEXT["tr"]["match_analysis"], TEXT["en"]["match_analysis"]):
        page_match_analysis(api_base_url)
    elif page in (TEXT["tr"]["team_form"], TEXT["en"]["team_form"]):
        page_team_form(api_base_url)
    elif page in (TEXT["tr"]["settings"], TEXT["en"]["settings"]):
        page_settings(api_base_url)
    else:
        st.error(f"Bilinmeyen sayfa: {labels['overview']}")


if __name__ == "__main__":
    main()


