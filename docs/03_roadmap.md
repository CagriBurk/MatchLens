# MatchLens - Yol Haritası (Grand Vision)

## 📌 Aşama 0: Temizlik ve Yeni İskelet (2026-10-31) - ✅ TAMAMLANDI
- [x] 1. ve 2. kuşak kodları kaldırıldı (`archive/`, `api/`, `ui/app.py`, API-Football ingest, `team_mapper`, `save_mapping`, `db_manager`, `csv_data`). Git geçmişinde duruyorlar.
- [x] DB'den kopya/atıl tablolar silindi (`tm_games`, `tm_team_form`, `tm_players`, `tm_player_valuations`, `match_features`, `team_form_snapshots`, `matches`, `team_mapping`). Yedek: `database/matchlens_legacy_backup.db`.
- [x] Ortak `config.py` + `db.py`, tek isim eşleştirme modülü `team_names.py`, argparse'lı `run_pipeline.py`. Refactor sonrası `ml_master_dataset` eskisiyle birebir aynı doğrulandı.
- [x] `.gitignore` (Python), `requirements.txt`, `AGENTS.md` yeniden yazıldı. Eski `02_current_state.md` / `05_project_structure.md` `_trash/`'e taşındı.

## 📌 Veri Kaynağı Erişim Testi (2026-10-31, Türkiye bağlantısından)
| Kaynak | Durum | Ne verir |
| :--- | :--- | :--- |
| football-data.co.uk | ❌ Engelli | (Tarihsel oran + korner/kart) |
| FBref / Sofascore | ❌ 403 | — |
| ClubElo API | ⚠️ 502 (kapalı/kararsız) | Elo |
| Understat | ✅ | xG, PPDA, Deep (Top 5 lig, 2014+) |
| ESPN (site.api.espn.com) | ✅ | Fikstür (bugün/gelecek), sonuç, korner/kart/faul/şut/topa sahip olma, gol & kart dakikaları, hakem, bazı oranlar. tur.1 dahil çok sayıda lig, 2019 ve öncesi geçmiş |
| Nesine bülten API | ✅ | Canlı İddaa oranları: ~660 futbol maçı, 170 lig, ~100 market (İki Yarı 1.5 Üst dahil) |
| Kaggle / GitHub raw | ✅ | Tarihsel oran veri seti aynaları |

**Önemli notlar:** İddaa marjı ~%18-19 (örn. 1.17/5.30/7.00 ve 2.5 Alt/Üst 1.74/1.63). ESPN'deki "Bet 365" ana alanı maç sonu canlı oranı olabilir (sızıntı); sadece `preMatch*` alanları kullanılmalı.

## 🔶 Bekleyen Kararlar
- [ ] Lig kapsamı: Katmanlı model (geniş taban + Top 5'te taktiksel derinlik) önerildi.
- [ ] Veri omurgası: ESPN (fikstür+istatistik+dakika) + Understat (xG) + kendi Elo'muz + Nesine (canlı oran) önerildi.
- [ ] Tarihsel oran kaynağı (Kaggle aynası?) ve Nesine bülteninin günlük arşivlenmesi.

## 📌 Aşama 1: Veri Pipeline'ının Stabilize Edilmesi (Refactoring) - ✅ TAMAMLANDI
- [x] `data_pipeline` ve `scripts` altındaki (Pandas ve SQL odaklı) dağınık veri işleme kodlarının incelenmesi. (archive klasörüne taşındı)
- [x] Veri Çekme -> Temizleme -> Eşleştirme (Mapping) -> Feature Üretimi -> Analiz adımlarının birbirinden bağımsız, temiz modüller (clean architecture) haline getirilmesi.
- [x] Veritabanı (`matchlens.db`) okuma/yazma işlemlerinin standartlaştırılması.

## 📌 Aşama 2: Taktiksel Veri Entegrasyonu (Advanced Stats) - ✅ TAMAMLANDI
- [x] `soccerdata` paketinin projeye (requirements.txt ve sanal ortama) dahil edilmesi.
- [x] Understat (FBref yerine) üzerinden maç bazlı PPDA, 3. Bölge Pasları (Deep Completions), Şut Kalitesi (xG, np_xG) istatistiklerinin çekilmesi.
- [x] Çekilen bu verilerin SQLite veritabanında yeni tablolara (`tactical_match_stats`) yazılması.

## 📌 Aşama 3: Taktiksel, Fiziksel ve Dakika Bazlı Feature Engineering (Şu an buradayız 🚀)
- [x] `data_pipeline/feature_engine.py` içinde xG, PPDA ve Deep Completions için "Rolling Averages" (Son 3/5 maçlık form) ve Momentum sapması (`diff_*`) hesaplanması.
- [x] Maç tarihleri üzerinden takımların "Dinlenme Günleri" (Rest Days) hesaplamasının yapılması.
- [x] `soccerdata.ClubElo` ve `elo_mapper.py` ile tarihsel "Takım Gücü Puanı" (Elo Rating) verilerinin çekilmesi (`historical_club_elo`) ve taktiksel formla birleştirilmesi (`ml_master_dataset`).
- [ ] `soccerdata.MatchHistory` (`football-data.co.uk`) entegrasyonu ile **İlk Yarı/Maç Sonu Gol (`HTHG`, `HTAG`), Korner (`HC`, `AC`), Sarı/Kırmızı Kart (`HY`, `AY`, `HR`, `AR`), Faul (`HF`, `AF`), Şut (`HS`, `HST`), Hakem (`Referee`) ve Tarihsel Bet365/Pinnacle Açılış-Kapanış Oranları** verilerinin çekilmesi.
- [ ] `data/raw/transfermarkt/game_events.csv` (149.6 MB) üzerinden takımların **Dakika Aralıklarına Göre (`0-15`, `16-30`, `31-45+`, `46-60`, `61-75`, `76-90+`) Gol ve Kart Dağılımlarının** (`team_minute_stats`) çıkarılması.
- [ ] Takım bazlı verilerin **Maç Bazlı (Ev Sahibi vs. Deplasman)** ML eğitim tablosuna (`ml_match_dataset`) dönüştürülmesi; Taktiksel Çarpışma (`finishing_luck`, `press_vs_buildup`, `referee_strictness`, `elo_diff`, `first_half_tempo`) ve hedef değişkenlerin eklenmesi.

## 📌 Aşama 4: Çoklu Market Olasılık, Oran İkizleri ve Sürpriz (Value) Motoru
- [ ] **1. Alt Motor (Gol, Yarı & Skor Motoru):** Tam maç ($\lambda_H, \lambda_A$) ve Yarı bazlı ($\lambda_{1H}, \lambda_{2H}$) LightGBM/XGBoost Poisson Regresyonu + Dixon-Coles matrisi ile **36 Tam Skor, 1X2, 1.5/2.5/3.5 Alt-Üst, KG Var** olasılıklarının üretilmesi.
- [ ] **2. Alt Motor (Sürpriz / Özel Oran Avcısı):** Yarı bazlı Poisson ve dakika verileriyle **`Her İki Yarıda 1.5 Üst`**, **`Her İki Yarıda KG Var`**, **`6+ Gol`** ve **`0-15 Dk Erken Gol`** olasılıklarının üretilmesi.
- [ ] **3. Alt Motor (Korner & Kart Motorları):** 3. bölge baskısı (`deep_completions`) ve şut hacminden **Korner ($\gamma_H, \gamma_A$ — `8.5/9.5/10.5 Üst`)**; hakem sertliği (`referee_strictness`) ve pres/faul yoğunluğundan **Kart ($\kappa_H, \kappa_A$ — `3.5/4.5 Üst`)** olasılıklarının üretilmesi.
- [ ] **4. Alt Motor (Bet365 Tarihsel Oran İkizleri - k-NN Engine):** Maça açılan Bet365 oranlarına tarihte en çok benzeyen 200 maçı tarayıp, oranın beklenen olasılığı ile tarihsel gerçekleşme oranı arasındaki sapmayı (`Pattern Edge`) ve sürpriz/skor dağılımını bulan motorun kurulması.
- [ ] **Üçlü Onay (Triple-Check) & Value Hesaplayıcı:** `Taktiksel AI` + `Bet365 Oran İkizleri` + `Tarihsel/Dakika İstatistiği` sinyallerini birleştirip 3 Yıldızlı fırsatları puanlayan karar mekanizması.

## 📌 Aşama 5: Streamlit "5 Ekranlı Pro Karar Destek Platformu" Arayüzü
- [ ] **Ekran 1 — Günün AI Fırsatları (Vitrin):** `Oran >= 1.50` ve yüksek Edge filtreli, 3/3 Üçlü Onay rozetli öne çıkan maçlar.
- [ ] **Ekran 2 — Maç Laboratuvarı (Sol: Geçmiş & Dakika Analizi | Sağ: AI Olasılıkları & Canlı Oran Testi):** Sol panelde `0-15..75-90` dakika gol grafikleri, İY/MS ve H2H trendleri; sağ panelde 36'lı Skor Isı Haritası, Korner/Kart tahminleri, SHAP açıklaması ve kullanıcının kendi oranını test edebileceği interaktif kutu.
- [ ] **Ekran 3 — Bet365 Oran İkizleri Tarayıcısı:** Benzer oranlı geçmiş maçlarda ne çıktığını, en sık görülen skorları ve oran düşüşlerini (*Smart Money*) gösteren ekran.
- [ ] **Ekran 4 — Sürpriz & Özel Oran Avcısı:** `6+ Gol`, `Her İki Yarı 1.5 Üst`, `Her İki Yarı KG Var` ve `0-15 Dk Gol` fırsatlarının listelendiği yüksek oran radarı.
- [ ] **Ekran 5 — Backtest & Kasa Simülatörü:** Sistemin geçmiş maçlardaki isabet oranını ve ROI başarısını kanıtlayan simülasyon ekranı.

## 📌 Aşama 6: Otomasyon ve Ürünleşme
- [ ] Verilerin her gün otomatik çekilmesi (cron job).
- [ ] Projenin GitHub'a README ve dokümantasyonlarıyla birlikte profesyonelce sunulması.
