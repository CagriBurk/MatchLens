# MatchLens — Oturum Devir Notu (2026-11-01 akşam)

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
- **Model** (`dixon_coles.py` + `markets.py` + `goal_calibration.py`): sadece geçmiş maç verisi; skor matrisi toplam gol × KG grubuna göre yeniden ağırlıklandırılıyor.
- **Oran İkizleri** (`twins.py`): marjsız 1/2/Ü2.5'e en yakın 200 geçmiş maçın gerçek sonuçları (kombolar dahil).
- **Piyasa**: Bet365, yoksa DraftKings (ESPN summary); 2.5 çizgisi yoksa Asya çizgisinden çevrilir (`~`). Kapsama ~%95.
- **İddaa (Nesine)** (`data_pipeline/nesine.py`): sadece kupon oranları ve İddaa marjsız yüzdesi.
- Arayüz sekmeleri: Bülten, Maç detayı, Oran İkizleri, Kuponlar (mavi/sarı/kırmızı + sürpriz; Çağrı seçimleri beğenmedi, Model/İkiz olarak ikiye bölünecek), Karne (ileriye dönük isabet + kupon karnesi).

## 4. Komutlar
```
.venv\Scripts\python -m matchlens.update [--rebuild-coupons]
.venv\Scripts\python -m matchlens.bulletin --date 2026-11-08
.venv\Scripts\python -m matchlens.twins build|backtest          # backtest -> twins_backtest tablosu
.venv\Scripts\python -m matchlens.backtest                      # model walk-forward -> backtest_predictions + goal weights
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

## 6. Dürüst Durum
- Model 1X2'de iyi kalibre ama Bet365'ten zayıf (log-loss 1.007 vs 0.988). Hiçbir bahis kuralı tarihsel olarak kâr etmiyor; İddaa marjı ~%15-19 (Üst/KG Var tarafına daha çok yüklü).
- **Sağlık raporu (son sınav ≥2024-07, ~10k maç, ağırlıklar sadece ayar döneminden):** 1X2 ve MS kombo marketleri GEÇTİ. Üst 1.5/2.5/3.5, KG, KG+Üst, İY gol marketleri KALDI: kalibrasyon eğimi 0.65-0.80 (tahminler fazla uçlara yayılıyor). Model "Üst %30-40" dediğinde gerçek %43, "%40-50" → %48; gol beklentisi <2.2 olan maçlarda Üst 7 puan, 2.2-2.6'da 3 puan eksik; ≥2.6'da doğru. Kuponlardaki Alt yığılmasının asıl kaynağı bu. İkizler aynı maçlarda daha iyi (Ü2.5 log-loss 0.673 vs 0.679). 2026 olağandışı gollü: ikizler bile Üst'ü 2 puan eksik veriyor.

## 7. Sıradaki İş (onaylandı, başlanmadı)
**Adım 2: hedefli yeniden ayar** (~1.5 saat, çoğu arka plan hesap):
- Hipotez: gol toplamı tahminlerini lig ortalamasına doğru daraltmak, ev/deplasman güç farkını (1X2) bozmadan.
- Deneyler: (a) gol tarafı için daha güçlü ridge / ayrı ayar (eski bulgu: gol marketleri ridge≈20 istiyor), (b) λ_toplam' = L + γ(λ_toplam − L), oran λ_ev/λ_dep korunur, γ ve L (lig ortalaması, sızıntısız) sadece ayar döneminden.
- Kabul: `health` son sınavında gol marketleri GEÇMELİ (eğim 0.85-1.15, |sapma| ≤ 1 puan), 1X2 kötüleşmemeli. Sağlanmazsa uygulanmaz.
- Sonra Adım 3: 2026 gol artışı için lig gol seviyesine daha hızlı zaman ağırlığı (aynı çerçevede). Sonra kuponları Model/İkiz olarak ikiye bölmek ve kupon şartında referansı Bet365/DK yapmak.
- Son faz (v3): canlı bildirim (roadmap Aşama 7).
