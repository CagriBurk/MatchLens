
import streamlit as st
import requests
import pandas as pd

# --- Sayfa Ayarları ---
st.set_page_config(page_title="MatchLens Analiz Merkezi", page_icon="⚽", layout="wide")

# API Adresimiz
API_BASE_URL = "http://127.0.0.1:8000"

# --- Yan Menü (Sidebar) ---
st.sidebar.title("⚽ MatchLens")
st.sidebar.markdown("Futbol Veri & Analiz Platformu")
st.sidebar.divider()

menu_secimi = st.sidebar.radio(
    "Menü",
    ["📊 Genel Bakış", "🔍 Detaylı Maç Analizi", "📈 Takım Form Merkezi"]
)

# --- SAYFA 1: GENEL BAKIŞ ---
if menu_secimi == "📊 Genel Bakış":
    st.title("📊 Veritabanı Genel Bakış")
    st.markdown("Sistemde kayıtlı olan son maçların listesi ve temel özellikleri.")
    
    # API'den veriyi çek
    try:
        response = requests.get(f"{API_BASE_URL}/features?limit=15")
        if response.status_code == 200:
            df = pd.DataFrame(response.json())
            st.dataframe(df, use_container_width=True)
        else:
            st.warning("Veriler çekilirken bir sorun oluştu.")
    except Exception as e:
        st.error(f"API Bağlantı Hatası: Lütfen FastAPI sunucusunun açık olduğundan emin olun. Detay: {e}")

# --- SAYFA 2: DETAYLI MAÇ ANALİZİ ---
elif menu_secimi == "🔍 Detaylı Maç Analizi":
    st.title("🔍 Özel Maç Analizi")
    st.markdown("Bir maçın ID'sini girerek yapay zeka destekli taktiksel yoruma ulaşın.")
    
    col1, col2 = st.columns([1, 3])
    with col1:
        game_id_input = st.text_input("Maç ID:", "2225443")
        analiz_butonu = st.button("Analizi Getir", type="primary")
        
    if analiz_butonu:
        try:
            response = requests.get(f"{API_BASE_URL}/matches/{game_id_input}/analysis")
            if response.status_code == 200:
                data = response.json()
                
                st.divider()
                st.subheader("Taktiksel Önizleme")
                
                # Metrik Kartları
                m_col1, m_col2, m_col3 = st.columns(3)
                m_col1.metric(label="Ev Sahibi ID", value=data["home_club_id"])
                m_col2.metric(label="Deplasman ID", value=data["away_club_id"])
                m_col3.metric(label="Form Avantaj Skoru", value=data["form_advantage_score"])
                
                # AI Yorum Kutusu
                st.success(f"💡 **MatchLens Yorumu:** {data['analysis']}")
            elif response.status_code == 404:
                st.error("Bu ID'ye ait bir maç bulunamadı.")
            else:
                st.warning("Bilinmeyen bir hata oluştu.")
        except Exception as e:
            st.error("API'ye ulaşılamıyor.")

# --- SAYFA 3: TAKIM FORM MERKEZİ ---
elif menu_secimi == "📈 Takım Form Merkezi":
    st.title("📈 Takım Form Merkezi")
    st.markdown("Takımların en güncel form durumlarını, BTTS ve 2.5 Üst eğilimlerini inceleyin.")
    
    col1, col2 = st.columns([1, 3])
    with col1:
        club_id_input = st.text_input("Takım (Club) ID:", "289")
        form_butonu = st.button("Form Durumunu Getir", type="primary")
        
    if form_butonu:
        try:
            response = requests.get(f"{API_BASE_URL}/teams/{club_id_input}/form")
            if response.status_code == 200:
                data = response.json()
                
                st.divider()
                st.subheader(f"Takım ID: {data['club_id']} Güncel Form Raporu")
                
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Oynanan Maç", data["matches_played"])
                c2.metric("Galibiyet", data["wins"])
                c3.metric("Beraberlik", data["draws"])
                c4.metric("Mağlubiyet", data["loses"])
                
                st.markdown("#### Eğilim Analizi (Son 10 Maç)")
                e1, e2, e3 = st.columns(3)
                e1.metric("Maç Başı Puan (PPG)", f"{data['average_point_per_game']:.2f}")
                e2.metric("Karşılıklı Gol (BTTS) Oranı", f"%{data['btts_rate']*100:.0f}")
                e3.metric("2.5 Üst Oranı", f"%{data['total_over_2_5']*100:.0f}")
                
            elif response.status_code == 404:
                st.error("Bu ID'ye ait takım form verisi bulunamadı.")
        except Exception as e:
            st.error("API'ye ulaşılamıyor.")