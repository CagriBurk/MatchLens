# MatchLens - Proje Özeti (Project Overview)

## 📌 Projenin Amacı
MatchLens, geçmiş futbol maç verilerini ve güncel API verilerini harmanlayarak, kullanıcıya derinlemesine veri analizi ve yapay zeka (AI) destekli gelecek tahminleri (future prediction) sunan modern bir analitik platformudur.

## 🛠 Kullanılan Teknolojiler (Tech Stack)
- **Veri Kaynağı (Geçmiş):** Kaggle veri seti
- **Veri Kaynağı (Güncel):** api-football API
- **Veri İşleme:** Pandas, SQL (SQLite)
- **Kullanıcı Arayüzü (UI):** Streamlit
- **Yapay Zeka (AI):** (Planlanıyor - Future Prediction)

## 🏗 Mimari Akış (Architecture Flow)
1. **Veri Toplama (Data Ingestion):** Kaggle'dan alınan geçmiş maç verileri tabana oturur. `api-football` kullanılarak eksik/güncel veriler çekilir.
2. **Veri İşleme (Data Pipeline):** Ham veriler temizlenir, birleştirilir. Form durumları, gol beklentileri vb. yeni türetilmiş (derived) sütunlar oluşturulur.
3. **Veritabanı (Database):** Temizlenmiş ve analize hazır veriler `matchlens.db` (SQLite) üzerinde saklanır.
4. **Tahmin Motoru (Prediction Engine):** Hazırlanan veriler üzerinden kural tabanlı analizler veya ML (Makine Öğrenmesi) modelleri koşularak maç tahminleri üretilir.
5. **Kullanıcı Arayüzü (UI):** Streamlit arayüzü sayesinde tüm bu karmaşık veriler, "karar destek odaklı" profesyonel bir tasarımla kullanıcıya sunulur.

## 🎯 Geliştiricinin Hedefleri
- Büyük proje kontrolü yetkinliği kazanmak
- Hard-coding tecrübesi edinmek
- Güçlü bir portföy/CV projesi ortaya çıkarmak
- Genel yazılım mimarisi ve kodlama kabiliyetini artırmak
