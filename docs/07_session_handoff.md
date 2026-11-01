# MatchLens — Oturum Devir Notu (2026-11-01 gece)

Yeni oturum önce bunu, sonra `docs/03_roadmap.md` (Aşama 4-5a ve 7) ve `.agents/AGENTS.md` dosyalarını okumalı.

## 1. Çalışma Düzeni
- Kararları Çağrı ile birlikte alıyoruz, kodu Claude yazıyor. Konuşma dili Türkçe, hızlı ilerleme.
- Kod stili: string/print/log İngilizce (istisna: `ui/` altındaki kullanıcı metinleri Türkçe), yorum satırı yok, minimal çıktı. Yollar `data_pipeline/config.py`, DB `data_pipeline/db.py`.
- Büyük indirmelerden önce boyut söylenip onay alınır. Commit'i Claude atar, push'u Çağrı yapar.
- **Model ilkesi (Çağrı):** model "üst çıksın" diye değil, gerçeğe uysun diye ayarlanır. Her model değişikliği `matchlens.health` raporunun son sınav dönemiyle kabul/ret edilir.

## 2. Ortam (Windows)
- `C:\Users\cbura\projects\MatchLens`, Python 3.14 `.venv`, `PYTHONUTF8=1`, `tzdata`. WSL kopyası sadece yedek.
- Günlük: Görev Zamanlayıcı "MatchLens Daily Update" 07:30 → `scripts/daily_update.ps1` (mutex) → `python -m matchlens.update`, log `data/logs/update.log`. Update; ESPN, ikiz havuzu, bülten dosyaları (`data/bulletins/<tarih>_matches.csv`), `prediction_log`, Nesine oranları ve o günün kuponlarını üretir, bitmiş maçları sonuçlandırır.
- Arayüz: `powershell -File scripts\run_ui.ps1` → http://localhost:8501 (Streamlit; motor kodu değişince sunucuyu yeniden başlat).
- Uzun hesaplar DB'ye yazarken update/UI ile çakıştırma (SQLite tek yazıcı).

## 3. Ürün
Her maç için bağımsız kaynaklar yan yana (Bet365 oranı modele girmez):
- **Model** (`dixon_coles.py` + `markets.py` + `goal_calibration.py`): sadece geçmiş maç verisi; ayrık ridge (güç 3 / stil 30); skor matrisi toplam gol × KG grubuna göre yeniden ağırlıklandırılıyor.
- **Oran İkizleri** (`twins.py`): marjsız 1/2/Ü2.5'e en yakın 200 geçmiş maçın gerçek sonuçları (kombolar dahil).
- **Piyasa**: Bet365, yoksa DraftKings (ESPN summary); 2.5 çizgisi yoksa Asya çizgisinden çevrilir (`~`). Kapsama ~%95.
- **İddaa (Nesine)** (`data_pipeline/nesine.py`): sadece kupon oranları ve İddaa marjsız yüzdesi.
- Arayüz sekmeleri: Bülten, Maç detayı, Oran İkizleri, Kuponlar (iki sekme: Modelin seçtikleri / İkiz oran; her birinde mavi/sarı/kırmızı + sürpriz; şart kaynak olasılığı ≥ Bet365/DK marjsız, gol/kombo marketlerinde türetilmiş `~`), Karne (ileriye dönük isabet + kupon karnesi).

## 4. Komutlar
```
.venv\Scripts\python -m matchlens.update [--rebuild-coupons]
.venv\Scripts\python -m matchlens.bulletin --date 2026-11-08
.venv\Scripts\python -m matchlens.twins build|backtest          # backtest -> twins_backtest tablosu
.venv\Scripts\python -m matchlens.backtest [--ridge 3 --ridge-style 30]  # model walk-forward -> backtest_predictions + goal weights
.venv\Scripts\python -m matchlens.goal_calibration              # goal weights yeniden hesapla
.venv\Scripts\python -m matchlens.health --label X --weights none|tune|saved   # sağlık raporu -> data/reports/
.venv\Scripts\python -m matchlens.calibration
.venv\Scripts\python -m data_pipeline.ingest_espn scoreboards|summaries|build|coverage [--incremental]
.venv\Scripts\python -m pytest -q -p no:seleniumbase tests     # 97 test
powershell -File scripts\run_ui.ps1
```

## 5. Veri / Tablolar
- ESPN 12 lig 2016-2026 (`espn_*`, summary backfill tamam, Bet365 oranlı ~20k maç). Kaggle (`kaggle_matches`), FootyStats (`footystats_matches`, üyelik bitmek üzere), `team_name_map`.
- `twins_pool` (144.8k, takım isimli), `twins_backtest` (ESPN maçları için sızıntısız ikiz frekansları; sütunlar sayım, `_n` ile böl), `backtest_predictions` (model walk-forward 2019-07+), `prediction_log` (model_p/twin_p/market_p/market_src), `nesine_odds` (event_id, key, odds, mbs, fair), `coupon_log`.
- `data/model/goal_weights.json`, `data/raw/nesine/` (günlük ~1.8 MB), `data/reports/health_*.md|json`.
- `data/raw/kaggle/odds_movements/` (2026-11-01, ~300 MB parquet: matches, match_closing, odds_1x2, odds_ou, odds_ah; Kaggle archangel0x01/football-odds-movements-2018-2026) — v2 Smart Money için, henüz kullanılmıyor.

## 6. Dürüst Durum
- Model 1X2'de iyi kalibre ama Bet365'ten zayıf (Bet365 oranlı maçlarda log-loss 1.0067 vs 0.988). Hiçbir bahis kuralı tarihsel olarak kâr etmiyor; İddaa marjı ~%15-19 (Üst/KG Var tarafına daha çok yüklü).
- **Adım 2 yapıldı (2026-11-01 akşam):** Dixon-Coles'ta ayrık ridge: güç (atak+savunma → 1X2) 3, stil (atak−savunma → gol toplamı) 30. Eski tek ridge 5 gol toplamını fazla açıyor (eğim 0.77), 1X2'yi fazla küçültüyordu. Sağlık raporu son sınav (≥2024-07, ~10k maç): 12 GEÇTİ / 7 KALDI (önce 10/9); Üst 1.5/2.5/3.5 eğimleri 0.95-1.03, tüm marketlerde log-loss iyileşti veya aynı. Kabul şartı harfiyen sağlanmadı, Çağrı uygulama kararı verdi.
- **Kalan hatalar:** (1) Üst 2.5/3.5, KG+Üst, İY 0.5, iki yarı 1.5 Üst sadece sapmadan kalıyor ve tamamı 2026: Üst 2.5 sapması 2024/25 −0.2, 2026 −3.4 puan (ikizler −2.0); 2026'da maç başı gol +0.12. (2) KG eğimi 0.75 — toplamdan bağımsız gerçek zaaf; FootyStats KG piyasası eğim ~1.0 tutturuyor. λ-koşullu ağırlık ve KG matris eğme denendi, kazanç çok küçük olduğu için uygulanmadı. (3) İY/MS 1/2 eğimi 0.63 (nadir olay, gürültülü). İkizler hâlâ gol marketlerinde modelden biraz iyi (Ü2.5 0.6729 vs 0.6774).
- Deney betikleri/varyant tahminleri oturum scratchpad'indeydi (kalıcı değil); tekrar için `backtest --ridge X --ridge-style Y` + `health`.

## 7. Sıradaki İş
**Model ayarı donduruldu (Çağrı, 2026-11-01):** split30 (güç 3 / stil 30) üretimde, ölçüt kalibrasyon. Akşam denenen sıkı log-loss kapısı, mevsimsellik ve gol seviyesi takipçisi binde bir kazanç verdi, kanıtlanamadı, geri alındı (git: 2361300, ebfacae). 2026 sonbahar gol artışı öngörülemez şok; Karne'den izlenecek.

Sıradaki (nitelikli işler):
1. ~~Kuponları ikiye bölmek~~ yapıldı (2026-11-01 akşam, roadmap 5a). İlk yeni kuponlar 02.11 07:30 update ile; logun eksiksiz bittiğini kontrol et (01.11 11:57 çalışmasının logu "logged" satırında kesik, kuponlar 14:21'de elle üretilmişti).
- v2 oran hareketi araştırması yapıldı (roadmap "v2"): hareket sabah fiyatına ek bilgi vermiyor, kâr yok; ürüne girmedi.
- FootyStats üyeliği bitmeden Çağrı'nın elle indirmesi önerildi: eng.1 2023/24-2025/26, esp.1/ita.1/ger.1/fra.1 2023/24-2026/27 maç CSV'leri (+ istenirse 12 lig için 2019/20-2022/23). `data/raw/footystats/`e koyup `python -m data_pipeline.run_pipeline footystats` + `python -m matchlens.twins build` (büyük 4 ligin dosya adları okuyucuya eklendi).
2. Karne'yi izlemek: ileriye dönük isabet ve kupon tutma oranı birkaç hafta birikince değerlendirilecek.
3. Son faz (v3): canlı bildirim (roadmap Aşama 7).
- Not: 01.11 tahminleri/kuponları ridge 5 ile üretildi; 02.11 07:30 update'ten itibaren split30.
