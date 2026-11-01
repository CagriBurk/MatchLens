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
- **Model** (`dixon_coles.py` + `markets.py` + `goal_calibration.py`): sadece geçmiş maç verisi; ridge 5 (ayrık güç/stil ridge kodu var ama kapalı: `RIDGE_STYLE=None`); skor matrisi toplam gol × KG grubuna göre yeniden ağırlıklandırılıyor.
- **Oran İkizleri** (`twins.py`): marjsız 1/2/Ü2.5'e en yakın 200 geçmiş maçın gerçek sonuçları (kombolar dahil).
- **Piyasa**: Bet365, yoksa DraftKings (ESPN summary); 2.5 çizgisi yoksa Asya çizgisinden çevrilir (`~`). Kapsama ~%95.
- **İddaa (Nesine)** (`data_pipeline/nesine.py`): sadece kupon oranları ve İddaa marjsız yüzdesi.
- Arayüz sekmeleri: Bülten, Maç detayı, Oran İkizleri, Kuponlar (mavi/sarı/kırmızı + sürpriz; Çağrı seçimleri beğenmedi, Model/İkiz olarak ikiye bölünecek), Karne (ileriye dönük isabet + kupon karnesi).

## 4. Komutlar
```
.venv\Scripts\python -m matchlens.update [--rebuild-coupons]
.venv\Scripts\python -m matchlens.bulletin --date 2026-11-08
.venv\Scripts\python -m matchlens.twins build|backtest          # backtest -> twins_backtest tablosu
.venv\Scripts\python -m matchlens.backtest [--ridge R --ridge-style S] [--snapshot AD]  # walk-forward -> backtest_predictions + goal weights; --snapshot sadece data/backtests/AD.pkl
.venv\Scripts\python -m matchlens.goal_calibration              # goal weights yeniden hesapla
.venv\Scripts\python -m matchlens.health --label X [--preds AD] [--against TABAN]   # sağlık raporu + eşleştirilmiş kapı -> data/reports/
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
- Üretimde model ridge 5 (eski hâli). 1X2'de iyi kalibre ama Bet365'ten zayıf (log-loss 1.0073 vs 0.988). Hiçbir bahis kuralı tarihsel olarak kâr etmiyor; İddaa marjı ~%15-19.
- **Bilinen kalibrasyon sorunu (ridge 5):** gol toplamı fazla açılıyor (gerçek/tahmin toplam eğimi 0.77); Üst/KG eğimleri 0.65-0.80; kuponlardaki Alt yığılmasının kaynağı. Ayrık ridge (güç 3 / stil 30) bunu düzeltiyor (eğimler 0.95-1.03, ayar FAIL 9→1) ama son sınavda gol log-loss kazancı (−0.0036) istatistiksel olarak yetmedi → yeni kapı RET, Çağrı kuralı uyguladı ve geri alındı. Snapshot: `data/backtests/split30.pkl` ve `ridge5.pkl`.
- **Yeni sağlık kapısı** (ayrıntı roadmap Adım 2): karar eşleştirilmiş log-loss farkıyla (haftalık blok bootstrap GA), kalibrasyon z-skorlu FAIL/WARN. Kural sonuç görmeden sabitlendi ve güç simülasyonuyla doğrulandı; değiştirilmeyecek.
- **2026 kayması:** aslında 2026/27 sezon başı: Tem-Eki 3.08 gol/maç (tarihsel 2.66-2.82), artış normal oyun süresine yayılmış, çoğu ligde (ita.1 2.56→3.20, bel.1 2.71→3.20), Bet365 de kaçırdı → geçmiş veriden öngörülemez şok; kısmen yakalanabilir.
- KG: sezon bazında eğim 0.58-1.10 dalgalı (SE ≈0.13); FootyStats piyasası KG'de modelden iyi (modelde olmayan maç bilgisi). Ek KG katmanı/NegBin/iki değişkenli Poisson denenmeyecek.

## 7. Sıradaki İş
1. **Mevsimsellik:** ay (veya takvim grubu: Avrupa / usa+nor) bazında gol seviyesi çarpanı λ·exp(δ_ay), katsayılar walk-forward içinde yalnız geçmiş veriden (genişleyen pencere). Denetçi ön testi: iç doğrulamada gol log-loss −20.5e-4, son sınavda −7e-4. Taban `ridge5` snapshot, karar yeni kapıyla (`health --preds X --against ridge5`).
2. **Adım 3:** havuzlu (ligler arası), tek parametreli, muhafazakâr seviye takipçisi (λ·exp(δ_t)); seçim kuralı önceden: ayar döneminde en iyi olandan 1 SE içindeki en yavaş. Beklenti düşük: 2026 sonbahar Ü2.5 sapması −5.9 → ≈−3 puan.
3. Sonra: kuponları Model/İkiz olarak ikiye bölmek ve kupon şartında referansı Bet365/DK yapmak. Son faz (v3): canlı bildirim.
- Not: 01.11 tahminleri/kuponları ridge 5 ile üretildi (üretim modeli hiç değişmemiş sayılır; arada sadece ~1 saat 3:30 vardı, update o arada çalışmadı).
