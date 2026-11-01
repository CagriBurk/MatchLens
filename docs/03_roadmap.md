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

## ✅ Alınan Kararlar (2026-10-31)
- **Oran referansı Bet365.** Nesine/İddaa arşivleyici yazılmayacak. Bet365'te karşılığı olan marketlerde (1X2, Çifte Şans, Alt/Üst) model ile oran kıyaslanır; karşılığı olmayan özel marketlerde (İki Yarı 1.5 Üst, İki Yarı KG, 6+ Gol, 0-15 dk gol) oran kıyası yapılmaz, sadece model olasılığı gösterilir.
- **Veri omurgası ESPN.** Understat yalnızca Top 5 lig için derin katman (xG/PPDA/Deep). Elo'yu kendimiz sonuçlardan hesaplayacağız (repoda daha önce kendi Elo kodu yokmuş, sadece ClubElo çekici vardı; ClubElo şu an çalışmıyor).
- **Lig listesi (ilk faz, 12 lig):** eng.1, esp.1, ita.1, ger.1, fra.1, tur.1, bel.1, den.1, nor.1, usa.1, eng.2, esp.2. Danimarka 2 ve Norveç 2 ESPN'de yok. Liste `data_pipeline/espn/leagues.py` içinde, genişletmek tek satır (ESPN'de jpn.1, ned.1, por.1, ger.2, ita.2, fra.2, eng.3, sco.1 vb. de var).

## ✅ Alınan Kararlar (2026-11-01)
- **İş sırası değişti:** Önce ESPN verisiyle gol motoru + backtest + bülten (isim eşleştirmesi gerektirmiyor); Kaggle ingest, isim eşleştirme, kendi Elo'muz, FootyStats xG katmanı ve Understat genişletmesi v1.1'e.
- **The Odds API şimdilik bırakıldı:** ev Wi-Fi'sinde `the-odds-api.com` ve `api.the-odds-api.com` TLS aşamasında sıfırlanıyor (SNI tabanlı ISS engeli). Güncel Bet365 oranı yalnızca ESPN'den (Top 5 + eng.2 + usa.1); diğer liglerde bülten oran kıyası olmadan sadece model olasılığı gösterir.
- **Model takım anahtarı ESPN takım ID'si** (isim değişikliklerine dayanıklı). AET/penaltılı maçlar eğitimden çıkarılır (sadece `STATUS_FULL_TIME`).
- **Dixon-Coles varsayılanları:** xi=0.0019/gün (yarı ömür ~1 yıl), ridge=5, 4 yıllık pencere, yeni takımlar için negatif prior (grid araması 2019-2026 walk-forward, 1X2 log-loss'a göre).

## 📌 Aşama 4a: v1 Gol Motoru (2026-11-01)
- [x] `matchlens/data.py`: ESPN scoreboard önbelleğinden maçlar + İY golleri + 0-15 dk golleri (`events_consistent` maçlardan).
- [x] `matchlens/dixon_coles.py`: lig bazlı, zaman ağırlıklı, ridge'li Dixon-Coles (analitik gradyan, L-BFGS-B, fit ~0.04 sn). Yarı payları ve erken gol payı lig bazında.
- [x] `matchlens/markets.py`: skor matrisi → 1X2, ÇŞ, Alt/Üst 1.5-4.5, KG, İY 1X2, İY/2Y 0.5/1.5 Üst, İY/MS (9), İki Yarı 1.5 Üst, İki Yarı KG, 6+ gol, 0-15 dk gol, en olası skorlar.
- [x] `matchlens/odds.py`: marj temizleme, adil oran, EV, Asya gol çizgisi (2.25/2.75/3.0) hesaplaşması.
- [x] `matchlens/backtest.py`: haftalık walk-forward (2019-07+), log-loss (model / taban / Bet365), flat-stake ROI. Tahminler `backtest_predictions` tablosuna.
- [x] `matchlens/bulletin.py`: `python -m matchlens.bulletin --date YYYY-MM-DD` → fikstür + ESPN Bet365 oranları + model olasılıkları + özel marketler + değer adayları; CSV `data/bulletins/`.
- [x] Testler: `tests/` (34 test; markets, odds, Dixon-Coles gradyan/sızıntı, backtest).
- **İlk backtest (31.902 maç, 745 oranlı maç):** 1X2 log-loss model 1.015 / taban 1.072; Bet365 karşısında model 1.004, piyasa 0.981 → **model henüz piyasayı yenmiyor**, ROI -%8..-%13. Over 2.5 kalibrasyonu uçlarda fazla emin (tahmin %30 → gerçek %38, %79 → %71).
- [x] Backfill sonrası tam Bet365 örneklemiyle tekrar koşuldu (2026-11-01): 31.902 maç, 17.784 Bet365 oranlı; 1X2 log-loss model 1.0073 / piyasa 0.9880, ROI 1X2 -%9, toplam -%4. Sonuç değişmedi: model piyasayı yenmiyor.
- [ ] Gol marketleri için kalibrasyon katmanı (gol marketleri daha yüksek küçültmeyi tercih ediyor: ridge≈20).
- [ ] Model + piyasa harmanı (blend) ve değer eşiğinin backtest ile belirlenmesi.

## 📌 Aşama 4c: Kalibrasyon ve Model + Piyasa Harmanı (2026-11-01)
- [x] `matchlens/market_lambda.py`: piyasa 1X2 (+ varsa Üst/Alt 2.5) adil olasılıklarından ima edilen (λ_ev, λ_dep); 0.01 adımlı ızgara + KD-ağacı, 30k maç ~1 sn.
- [x] `matchlens/calibration.py`: backtest tahminleri + Bet365 (ESPN) / Kaggle ort.-max / FootyStats oranları; `log λ = w·model + (1−w)·piyasa` harmanı; ayar (<2023-07) / test (≥2023-07) log-loss, lig bazında en iyi w, ROI.
- **Sonuç (30.061 maç, test 13.988):** Tüm marketlerde en iyi w = 0 (ayar dönemi). Test 1X2 log-loss: piyasa 0.9895, saf model 1.0106. Saf model ile bahis ROI -%6..-%17. **Saf Dixon-Coles piyasaya bilgi eklemiyor.** Lig bazında küçük katkı sadece az likit liglerin gol marketlerinde (usa/nor/den/bel Üst 2.5 ve KG: w 0.1-0.4).
- **Özel marketler piyasa λ'sı ile iyi kalibre:** İki Yarı 1.5 Üst tahmin %16.8 / gerçek %17.2, İY 0.5 Üst %71.0 / %71.8, 0-15 dk gol %30.3 / %31.1, 6+ gol %7.2 / %6.7; hepsinde piyasa λ'sı modelden iyi. Piyasa λ'sından türetilen KG (0.6816) FootyStats KG oranının kendisine (0.6795) yakın → yarı bölme yöntemi sağlam.

- [x] **Skor durumu etkisi (İY/MS):** bağımsız yarı varsayımı geri dönüşleri az tahmin ediyordu (1/2 %1.92 vs gerçek %2.40, 2/1 %2.37 vs %3.01). İkinci yarı λ'sı devre skoruna göre çarpılıyor: önde 0.943, geride 1.088, beraberlik 0.960 (30k maçtan oran tahmini; ayar/test dönemlerinde tutarlı). Sonrası: 1/2 %2.31, 2/1 %2.79, 1/1 %27.20 vs %27.13; tüm İY/MS hücrelerinde log-loss iyileşti. (`markets.STATE_FACTORS`)
- [x] **A: Piyasa çapalı bülten.** Bet365 oranı olan maçlarda λ = piyasa λ'sı (1X2 + Asya gol çizgisi; `market_lambda` artık 2.25/2.75/3.0 gibi çizgileri de çözüyor); gol toplamında lig bazlı model ağırlığı (usa/nor/den 0.2, bel 0.1, diğerleri 0), 1X2 tarafı tamamen piyasa (`matchlens/blend.py`). Oranı olmayan maçlarda saf model (`src=model`). Sürpriz tablosu: İki Yarı KG, İki Yarı 1.5 Üst, 6+, 0-15 dk, İY/MS 1/2 ve 2/1 — olasılık + adil oran. Saf model kenarları sadece `--show-edges` ile "deneysel" etiketiyle. `prediction_log`'a İY/MS 1/2 ve 2/1 eklendi.

## 📌 Aşama 4d: B — Modele Ek Bilgi (2026-11-01)
- [x] `dixon_coles.fit(targets=..., fixed_rho=...)`: gol yerine gol/xG karışımı hedefe fit.
- [x] **xG deneyi** (FootyStats xG; tur/bel/den/nor/esp.2/eng.2/usa; walk-forward 2024-07+, 6.037 piyasa oranlı maç): xG karışımı saf modeli iyileştiriyor (Üst 2.5 log-loss 0.6811 → 0.6787, KG 0.6831 → 0.6811, en iyi α=0.5 gol + 0.5 xG) ama piyasa harmanında 1X2 ve Üst 2.5 için en iyi w yine 0; KG'de w≈0.3 ile 0.6805 → 0.6796 (önemsiz). **Bet365 xG bilgisini zaten fiyatlıyor.**
- [x] **Ürün tasarımı kararı (Çağrı):** Bet365 oranı modele girmez. Kullanıcı üç bağımsız bilgiyi yan yana görür: **A: Oran İkizleri** (AI yok, benzer oranla açılmış geçmiş maçların gerçek sonuçları), **B: AI modeli** (sadece geçmiş maç verisi), **Piyasa** (Bet365 marjsız %). En sonda "A ve B ikisi de piyasadan yüksek" kıyası. Piyasa çapalı bülten (`blend.py`) kaldırıldı.
- [x] **A: `matchlens/twins.py`** — `twins_pool` (144.428 maç: Kaggle 133.588 + FootyStats 9.857 + Bet365 983; 121k Alt/Üst, 144k İY, 47k 0-15 dk). Kalite: doğrulanamayan Kaggle ek ligleri (aut/jpn/pol/sui/swe) hariç, den/nor/usa sadece ESPN'e bağlı satırlar. Marjsız (1, 2, Üst 2.5) uzayında KD-ağacı, en yakın 200 maç, sadece maç tarihinden önceki maçlar. Arama derinliği 20k / parti 2M hücre ile sınırlı (bellek tepe ~600 MB).
- **İkiz backtest'i (2019-07+, 50.501 maç, sızıntısız):** 1X2 log-loss piyasa 0.9940 / ikiz 0.9982; Üst 2.5 0.6734 / 0.6757. "İkiz > piyasa + eşik" kuralı ROI -%3..-%7 (≈ marj). "İkiz VE model > piyasa" kuralı (30.047 maç) ROI -%8..-%9; ikiz tek başına -%5, model tek başına -%9..-%10. **Hiçbir kural tarihsel olarak kâr etmiyor** (ortalama/Bet365 oranlarıyla; İddaa marjında daha kötü olur). Havuzda favori lehine sapma var (p≈0.84 → gerçek 0.89) ama oynanabilir kâra dönmüyor.
- [x] Bülten: Model / İkiz / Piyasa yan yana (1, X, 2, Üst 2.5, KG), sürpriz marketler model / ikiz (İki Yarı KG, İki Yarı 1.5 Üst, 6+, 0-15, İY/MS 1/2 ve 2/1), en olası skorlar (model ve ikiz), uyum listesi ("bilgi amaçlı" uyarısıyla). `prediction_log`'a `twin_p` ve `market_p` eklendi → üç kaynağın ileriye dönük isabeti ayrı ölçülüyor. Günlük update havuzu yeniden kuruyor.
- **Ortam notu (2026-11-01):** Oturum 5 kez çöktü; WSL sanal makinesi yeniden başlıyor. Bir tanesi kesin uyku (pille 3 dk boşta uyku). Diğerleri ESPN backfill (sürekli ağ trafiği) çalışırken ve Intel Wi-Fi sürücü (Netwtw14) olaylarıyla aynı anda. WSL'e 24 GB RAM + 8 GB swap verildi (`C:\Users\cbura\.wslconfig`). Uzun işler editörden bağımsız (`setsid nohup`) çalıştırılmalı.

## 📌 Aşama 4b: Kaggle + FootyStats Ingest ve Otomatik İsim Eşleştirme (2026-11-01)
- [x] `data_pipeline/linking.py`: dış kaynak maçlarını ESPN'e bağlar. Aday çiftler (lig, ±1 gün, aynı skor) → takım ismi→ESPN ID çoğunluk oyu (en az 3 oy, ikinci adaydan ≥3 kat) → eşlenmiş ID'ler + ±2 gün ile kesin birleştirme; `score_match` bayrağı. Sonuç `team_name_map` tablosu (source = kaggle / footystats).
- [x] `data_pipeline/ingest_kaggle.py` → `kaggle_matches` (158.560 maç, 23 bölüm, 2000-2026/09) + `kaggle_elo`. ESPN'e bağlanan 37.350 maç; ana liglerde bağlanma %99-100, skor uyumu %99.7-100.
- [x] `data_pipeline/ingest_footystats.py` → `footystats_matches` (18.346 maç, 18 lig/turnuva). ESPN liglerinde bağlanma %100, eşlenemeyen isim yok.
- **Bulgu:** Kaggle `OddHome` Bet365 değil (ESPN Bet365 ile birebir eşleşme %10, marj %5.1 vs %5.7) → piyasa ortalaması/başka zaman damgası; piyasa referansı olarak kullanılır.
- **Bulgu:** Kaggle DEN/NOR/USA satırlarının ~%35'i hatalı (olmayan maçlar, yanlış skorlar). Bu liglerde sadece ESPN'e bağlanan Kaggle satırları kullanılır; ayrıca Alt/Üst oranı yok ve 2024 sonunda bitiyor.
- **FootyStats rolü:** (1) KG ve Üst 1.5/3.5/4.5 oranlarının tek kaynağı → bu marketlerin backtest/kalibrasyonu; (2) Top 5 dışı liglerde xG (2023/24+) → xG katmanı denemesi; (3) den/nor/usa 2025-2026 oranları (Kaggle'da yok). Üyelik bitince güncel sezon xG'si güncellenemez → canlı xG katmanı üyelik süresine bağlı.
- [ ] FootyStats oranlarının kaynağını ESPN Bet365 ile karşılaştır (backfill sonrası).

## 📌 Aşama 2.5: ESPN Veri Omurgası
- [x] `data_pipeline/ingest_espn.py` + `data_pipeline/espn/` (client / parse / leagues). Ham JSON `data/raw/espn/` altında gzip önbellek; biten maçlar bir daha çekilmez.
- [x] Scoreboard (lig×yıl tek istek): 43.916 maç, 2016-2026, skor + gol/kart dakikaları (`espn_matches`, `espn_match_events`). Own goal yararlanan takıma yazılıyor; skor/olay tutarlılığı %98.1 (`events_consistent` bayrağı; tutarsızlar ağırlıkla bel/den 2016-17, tur 2018/2022).
- [x] Kapsam ölçümü (lig-sezon başı 15 maç örneklem): İstatistik (korner/şut/faul/kart/topa sahip olma) Top 5 + eng.2 + usa.1'de 2016'dan beri %100; esp.2 2021+, tur.1 2016-18 ve 2024+, bel.1 2024+, den.1 2024+, nor.1 2024+. Bet365 maç öncesi oran (1X2 + gol çizgisi): Top 5 + eng.2 2018+ büyük ölçüde var; bel/tur kısmi; den/nor/esp.2 (2022+) ve usa.1 neredeyse yok.
- [x] Tam summary backfill (43.294 maç) Windows'ta bitti (2026-11-01 11:50). Build: 43.916 maç, 20.213 Bet365 oran satırı. `twins_pool`'daki Bet365 maçı 983 → 20.117. İkiz backtest'i (50.837 maç): 1X2 log-loss piyasa 0.9932 / ikiz 0.9970; tüm kurallar yine negatif ROI (Bet365 kaynağında -%2..-%4).
- [x] Kaggle `adamgbor/club-football-match-data-2000-2025` indirildi (`data/raw/kaggle/club_football/`, 2026-11-01).
- [ ] Kaggle `archangel0x01/football-odds-movements-2018-2026` (~542 MB, açılış-kapanış ve oran hareketleri) — v2 (Smart Money) için ertelendi.
- [x] Günlük güncelleme komutu `python -m matchlens.update` (2026-11-01): bu yılın (ve 7 gün önceki yılın) scoreboard'ları → yeni biten + önümüzdeki 7 günün summary'leri → ESPN tablolarının artımlı güncellenmesi (`build --incremental`, sadece ilgili yılların event_id'leri silinip yeniden yazılır) → bekleyen tahminlerin sonuçlandırılması → önümüzdeki 3 günün tahminlerinin `prediction_log`'a yazılması → kümülatif isabet (Brier/log-loss) ve EV>%3 bahis ROI raporu.
- [x] `prediction_log`: (event_id, market) başına tek satır; maç başlayana kadar her güncellemede son tahmin + o anki Bet365 oranı ile üzerine yazılır, başladıktan sonra donar. 16 market + Asya gol çizgisi. Uzatma/penaltılı biten maçlar void.
- [x] Günlük çalıştırma: Windows Görev Zamanlayıcı "MatchLens Daily Update" her gün 07:30 (`scripts/register_daily_task.ps1`) → `scripts/daily_update.ps1` (mutex kilidi, log `data/logs/update.log`). Bilgisayar o saatte kapalıysa açılınca ilk fırsatta çalışır.

## 🔶 Açık Sorular
- [ ] Tarihsel Bet365 oranı olmayan lig-sezonlarda backtest/oran ikizleri için ek kaynak (Kaggle'daki football-data aynası tek seferlik indirilebilir).

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

## 📌 Aşama 5a: Streamlit v1 Arayüzü (2026-11-01)
- [x] Tasarım önce mockup olarak yapıldı (claude.ai Design tuvali "MatchLens UI"): koyu "maç günü veri masası", Barlow Condensed + Barlow + JetBrains Mono, Model mavi daire / İkiz turuncu baklava / Piyasa beyaz çizgi, uyum yeşil. Çağrı onayladı; tasarım ileride değişebilir.
- [x] Mimari: motor ↔ arayüz ayrık. `update` her gün `data/bulletins/<tarih>_matches.csv` (+ `_odds.csv`) yazar (`bulletin.save_snapshots`, kayda `rho` eklendi); arayüz bu dosyaları ve `twins_pool`'u sadece okur, DB'ye yazmaz.
- [x] `ui/data.py` (veri), `ui/views.py` (HTML), `ui/theme.css` (tüm renk/font tokenları tek yerde), `ui/pages/` (Bülten, Maç detayı, Oran İkizleri), `ui/picker.py` (maç seçimi, `?event=` parametresi). Başlatma: `scripts/run_ui.ps1` → http://localhost:8501.
- [x] `twins_pool`'a `home_team` / `away_team` eklendi; `TwinFinder.twin_table` 200 ikizi uzaklıkla listeler.
- Not: arayüz metinleri Türkçe (kullanıcıya dönük kopya); kod içi log/print İngilizce kuralı aynen geçerli.
- [x] **Piyasa kapsamı (2026-11-01):** ESPN summary'lerinde DraftKings oranı var (1X2 + standart Üst/Alt 2.5, açılış/kapanış; 2025 sonundan beri, 2026'da 12 ligin hepsinde %91-100). Kalite: 1.901 ortak maçta 1X2 log-loss DK kapanış 0.9955 / Bet365 0.9965, marj %6.1 / %6.6; sızıntı yok (hiçbir maçta p>0.95). Karar (Çağrı): piyasa market bazında önce Bet365, yoksa DraftKings; hiçbir kaynakta 2.5 çizgisi yoksa Asya çizgisi `market_lambda` ile Üst 2.5'e çevrilir (`~`). `prediction_log.market_src` (b365 / dk / b365~ / dk~). Sonuç: önümüzdeki 62 maçta piyasa+ikiz 27 → 60, Üst 2.5 piyasası 5 → 60.
- [ ] DraftKings geçmişini (~3.7k maç) `twins_pool`'a ve kalibrasyona eklemek (isteğe bağlı).
- [x] **Kuponlar (2026-11-01, Çağrı'nın isteği):** 4. sekme. Her sabah update'te o günün kuponları üretilip `coupon_log`'a yazılır, maçlar bitince sonuçlandırılır (`--rebuild-coupons` ile yeniden üretim).
  - Oranlar **Nesine/İddaa** (`data_pipeline/nesine.py`, `getprebultenfull`, ~1.8 MB/gün; ham `data/raw/nesine/`, eşleşmiş oranlar `nesine_odds`). ESPN eşleşmesi: başlama ±20 dk + takım ismi benzerliği (ilk denemede pencere içindeki 53/53 maç). Market kodları (MTID) editör seçimlerinden ve model korelasyonuyla doğrulandı (MS&KG sırası: 1&Var, 1&Yok, X&Var, X&Yok, 2&Var, 2&Yok). İki yarı KG ve 0-15 dk kodu bulunamadı.
  - Kombolar (`matchlens/selections.py`): MS&KG, MS&1.5/2.5 Alt-Üst, KG&2.5 Alt-Üst; model skor matrisinden, ikizler 200 maçtan aynı tanımla.
  - Kural: güvenli olasılık = min(Model, İkiz); seçim şartı güvenli olasılık ≥ İddaa marjsız yüzdesi (esnek); DEĞER etiketi güvenli × oran ≥ 1. Kupon başına bir maç, MBS kuralı. Mavi 1.35-1.65 / hedef tutma ≥%20, Sarı 1.70-2.40 / ≥%6, Kırmızı 2.50-4.50 / ≥%2 (2-4 seçim, MS kombo öncelikli), Sürpriz: 6+, İY/MS 1/2-2/1, iki yarı 1.5 Üst'ten en iyi 10 aday.
  - İlk gözlem: İddaa marjı Üst/KG Var tarafında yoğun; seçimler Alt/KG Yok ağırlıklı çıkıyor, DEĞER'li seçim nadir.
- [x] **Karne (2026-11-01):** 5. sekme (`matchlens/scorecard.py`, `ui/pages/scorecard.py`). Üç kaynağın aynı satırlarda Brier/log-loss kıyası, market bazında tablo (en iyi kaynak işaretli), kalibrasyon (kaynak seçilebilir), Bet365 vs DraftKings, kupon karnesi (tutma oranı vs beklenen, düz 1 birim ROI, seçim isabeti) ve kupon geçmişi.
- [ ] Kuponları ikiye bölmek (Çağrı, 2026-11-01: makinenin seçimleri beğenilmedi): "Modelin seçtikleri" ve "İkiz oran" kuponları ayrı.
- [ ] Tasarım revizyonu (işler bitince).

## 📌 Aşama 5: Streamlit "5 Ekranlı Pro Karar Destek Platformu" Arayüzü
- [ ] **Ekran 1 — Günün AI Fırsatları (Vitrin):** `Oran >= 1.50` ve yüksek Edge filtreli, 3/3 Üçlü Onay rozetli öne çıkan maçlar.
- [ ] **Ekran 2 — Maç Laboratuvarı (Sol: Geçmiş & Dakika Analizi | Sağ: AI Olasılıkları & Canlı Oran Testi):** Sol panelde `0-15..75-90` dakika gol grafikleri, İY/MS ve H2H trendleri; sağ panelde 36'lı Skor Isı Haritası, Korner/Kart tahminleri, SHAP açıklaması ve kullanıcının kendi oranını test edebileceği interaktif kutu.
- [ ] **Ekran 3 — Bet365 Oran İkizleri Tarayıcısı:** Benzer oranlı geçmiş maçlarda ne çıktığını, en sık görülen skorları ve oran düşüşlerini (*Smart Money*) gösteren ekran.
- [ ] **Ekran 4 — Sürpriz & Özel Oran Avcısı:** `6+ Gol`, `Her İki Yarı 1.5 Üst`, `Her İki Yarı KG Var` ve `0-15 Dk Gol` fırsatlarının listelendiği yüksek oran radarı.
- [ ] **Ekran 5 — Backtest & Kasa Simülatörü:** Sistemin geçmiş maçlardaki isabet oranını ve ROI başarısını kanıtlayan simülasyon ekranı.

## 📌 Aşama 7 (v3, son faz): Canlı Bildirim
- Fikir (Çağrı): maç sırasında (örn. 15. dk, favori ev sahibi baskıda, takım 15-30 arasında çok gol atıyor) "oynanabilir" bildirimi.
- Parçalar: takım bazlı 15 dk gol dağılımı (ESPN gol dakikaları, lig ortalamasına çekilmiş), canlı skor/dakika ve şut (ESPN, 30-60 sn gecikme; tehlikeli atak verisi yok), kalan süre + skor durumlu canlı Poisson, Nesine canlı oranı (incelenmedi), Telegram/Windows bildirimi.
- Riskler: canlı oran baskıyı hızla fiyatlar; maç boyu sürekli veri çekme (ölçülü internet); kanıt için uzun kayıt gerekir.
- Önce "bildirim + kayıt" modu, parasız test; ön maç kuponları ve Karne'den sonra.

## 📌 Aşama 6: Otomasyon ve Ürünleşme
- [ ] Verilerin her gün otomatik çekilmesi (cron job).
- [ ] Projenin GitHub'a README ve dokümantasyonlarıyla birlikte profesyonelce sunulması.
