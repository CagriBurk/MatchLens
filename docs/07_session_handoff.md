# MatchLens — Oturum Devir Notu (2026-11-01 sonu)

Yeni oturum önce bunu, sonra `docs/03_roadmap.md` ve `.agents/AGENTS.md` dosyalarını okumalı. Ayrıntılı karar/bulgu geçmişi roadmap'te (Aşama 4a-4d).

## 1. Çalışma Düzeni
- Kararları Çağrı ile birlikte alıyoruz, kodu Claude yazıyor. Konuşma dili Türkçe, hızlı ilerleme.
- Kod stili: string/print/log İngilizce, yorum satırı yok, minimal çıktı. Yollar `data_pipeline/config.py`, DB `data_pipeline/db.py`.
- Büyük indirmelerden önce boyut söylenip onay alınır. Commit'i Claude atar, push'u Çağrı yapar.

## 2. Ortam (2026-11-01'den itibaren Windows)
- Proje **WSL'den Windows'a taşındı**: `C:\Users\cbura\projects\MatchLens`. Eski WSL kopyası (`/home/main/projects/MatchLens`) sadece yedek, kullanılmıyor.
- Sebep: WSL sanal makinesi defalarca yeniden başladı (uyku, ESPN backfill sırasında Wi-Fi sürücü olayları, Antigravity'nin WSL'e yeniden bağlanamaması). Editör Antigravity IDE, klasör yerel açılıyor.
- Python 3.14 `.venv` (Windows), `PYTHONUTF8=1` kullanıcı ortam değişkeni (konsol ibm857), `tzdata` paketi (Europe/Istanbul için).
- Günlük güncelleme: Windows Görev Zamanlayıcı "MatchLens Daily Update" her gün 07:30 → `scripts/daily_update.ps1` → `python -m matchlens.update`, log `data/logs/update.log`.

## 3. Ürün Tasarımı (Çağrı'nın kararı)
Bet365 oranı modele **girmez**. Her maç için üç bağımsız bilgi yan yana:
- **A: Oran İkizleri** (`matchlens/twins.py`): AI yok. Marjsız (1, 2, Üst 2.5) yüzdelerine en yakın, maçtan önce oynanmış 200 geçmiş maçın gerçek sonuçları (1X2, Alt/Üst, KG, İY/MS, iki yarı marketleri, 6+, 0-15 dk, en sık skorlar).
- **B: AI modeli** (`matchlens/dixon_coles.py` + `markets.py`): sadece geçmiş maç verisi. Lig bazlı, zaman ağırlıklı, ridge'li Dixon-Coles; ikinci yarı skor durumuna bağlı (İY/MS 1/2-2/1 düzeltmesi).
- **Piyasa**: Bet365 marjsız yüzdesi; yoksa DraftKings (ESPN summary'sinden). Üst 2.5 çizgisi yoksa Asya çizgisinden çevrilir.
- Son katman: "A ve B ikisi de piyasadan yüksek" listesi (bilgi amaçlı).

## 4. Komutlar
```
.venv\Scripts\python -m matchlens.update                    # günlük: ESPN + havuz + tahmin kaydı + sonuçlandırma + rapor
.venv\Scripts\python -m matchlens.bulletin --date 2026-11-08 # bülten (Model / İkiz / Piyasa)
.venv\Scripts\python -m matchlens.twins build|backtest
.venv\Scripts\python -m matchlens.backtest                  # model walk-forward
.venv\Scripts\python -m matchlens.calibration               # model vs piyasa ölçümü (ürün dışı ölçüm aracı)
.venv\Scripts\python -m data_pipeline.run_pipeline kaggle footystats
.venv\Scripts\python -m data_pipeline.ingest_espn scoreboards|summaries|build|coverage [--incremental]
.venv\Scripts\python -m pytest -q -p no:seleniumbase tests
powershell -File scripts\run_ui.ps1                         # arayüz: http://localhost:8501
```

## 5. Veri
- ESPN (12 lig, 2016-2026): scoreboard önbelleği tam; summary backfill taşıma sonrası Windows'ta bitirildi (bkz. roadmap). `espn_*` tabloları.
- Kaggle `club_football` (football-data aynası, 2000-2026/09): `kaggle_matches`, `kaggle_elo`. Oranlar Bet365 değil (piyasa ort.), DEN/NOR/USA satırlarının ~%35'i hatalı → sadece ESPN'e bağlı satırlar.
- FootyStats (58 lig-sezon, 2023+; üyelik ~10 gün içinde bitiyor, veri statik): `footystats_matches`. xG, KG ve Üst 1.5-4.5 oranlarının tek kaynağı.
- `team_name_map`: dış kaynak ↔ ESPN takım ID'si, otomatik (tarih + skor oylaması).
- `twins_pool` (144k maç), `backtest_predictions`, `prediction_log` (model_p / twin_p / market_p, sonuçlandırma).

## 6. Dürüst Durum (backtest'ler)
- Model tek başına taban orana göre iyi, ama Bet365'ten zayıf (1X2 log-loss 1.011 vs 0.990). xG karışımı modeli iyileştiriyor ama piyasaya bilgi eklemiyor.
- İkizler piyasaya çok yakın (log-loss 0.998 vs 0.994). "İkiz > piyasa", "model > piyasa", "ikisi birden > piyasa" kurallarının hepsi 2019-2026'da negatif ROI (yaklaşık marj kadar). İddaa marjında daha kötü olur.
- Özel marketlerde model + skor durumu düzeltmesi iyi kalibre (İki Yarı 1.5 Üst, İY 0.5 Üst, 0-15 dk, İY/MS).
- Gerçek kanıt ileriye dönük `prediction_log`'dan gelecek; birkaç hafta veri birikince üç kaynağın isabeti kıyaslanacak.

## 7. Sıradaki Adaylar
1. İleriye dönük kaydı izlemek (her sabah update raporu).
2. Modeli güçlendirmek (Çağrı'nın planı: ikizlerden sağlam veri gelince): ligler arası Elo, Understat xG (Top 5), yorgunluk/UEFA, kadro. Her ekleme `calibration` ve twins backtest'iyle ölçülür.
3. İkizlerde aynı lig/ligler arası ağırlık, k ve mesafe ölçüsü denemeleri.
4. Arayüz: v1 hazır (Bülten / Maç detayı / Oran İkizleri / Kuponlar / Karne, `scripts/run_ui.ps1`). Sıradaki: kuponları Model ve İkiz olarak ikiye bölmek. Kuponlar Nesine oranlarıyla sabah update'te üretilir. Sıradaki: Karne ekranı (prediction_log), korner/kart motorları (v2).
