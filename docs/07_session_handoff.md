# MatchLens — Oturum Devir Notu (2026-10-31 → 2026-11-01)

Bu dosya, 31 Ekim oturumunda nerede kaldığımızı, yarın ne indirileceğini ve sıradaki işleri tek yerde toplar. Yeni oturum önce bunu, sonra `docs/03_roadmap.md` ve `.agents/AGENTS.md` dosyalarını okumalı.

## 1. Çalışma Düzeni
- Kararları Çağrı ile birlikte alıyoruz, kodu Claude yazıyor. Adım adım öğretici anlatım istenmiyor; hızlı ilerleme isteniyor.
- Kod stili: string/print/log İngilizce, yorum satırı yok, minimal terminal çıktısı. Yollar `data_pipeline/config.py`, DB erişimi `data_pipeline/db.py` üzerinden.
- Konuşma dili Türkçe. Roadmap her kararda güncellenir.
- **Büyük indirmelerden önce boyut söylenip onay alınır** (Çağrı bazen kotalı internette).

## 2. Nihai Hedef
Cumartesi sabah 08:00'de açıldığında, o gün oynanacak maçlar için model olasılıklarını Bet365 oranlarıyla kıyaslayıp en değerli (pozitif EV) bahisleri listeleyen motor + veri sistemi. Bet365'te karşılığı olmayan özel marketler (İki Yarı 1.5 Üst, İki Yarı KG Var, 6+ Gol, 0-15 dk gol, korner/kart) oran kıyası olmadan sadece model olasılığıyla gösterilir.

## 3. Alınan Kararlar
- **Oran referansı Bet365** (Nesine/İddaa arşivleyici yazılmayacak; İddaa marjı ~%19).
- **Güncel veri omurgası ESPN** (`site.api.espn.com`): fikstür, sonuç, gol/kart dakikaları, takım istatistikleri, kısmen Bet365 maç öncesi oranları.
- **Tarihsel veri/oran omurgası Kaggle** (football-data.co.uk Türkiye'den engelli; Kaggle aynası kullanılacak).
- **Understat** sadece Top 5 lig için derin katman (xG, PPDA, Deep).
- **Elo'yu kendimiz hesaplayacağız** (repoda kendi Elo kodu hiç yokmuş; ClubElo API şu an 502). Kaggle setindeki ClubElo snapshot'ları kıyas/başlangıç için kullanılabilir.
- **Lig listesi (faz 1):** eng.1, esp.1, ita.1, ger.1, fra.1, tur.1, bel.1, den.1, nor.1, usa.1, eng.2, esp.2 (`data_pipeline/espn/leagues.py`). Danimarka 2 / Norveç 2 ESPN'de yok. Genişletme serbest (jpn.1, ned.1, por.1, ger.2, ita.2, fra.2...).
- **Katmanlı model:** Tüm liglerde gol/sonuç/şut/korner/kart/Elo/oran tabanı; Top 5'te ek olarak xG katmanı. Eksik feature'lar LightGBM'de NaN olarak kalır; katmanın faydası backtest'te lig bazında ölçülür.

## 3.1. Ürün Kararları (31 Ekim gecesi)
- **Elle oran girme yok.** Geçmiş oranların hepsi Kaggle'dan (ve bulunabilecek diğer setlerden) çekilecek; güncel oranlar otomatik bir kaynaktan gelecek.
- **v1 kapsamı = Gol motoru:** 1X2, Çifte Şans, Alt/Üst (1.5/2.5/3.5), KG Var, İY/MS gol marketleri ve özel marketler (İki Yarı 1.5 Üst, İki Yarı KG, 6+ Gol, 0-15 dk gol). Korner/kart motorları ve Oran İkizleri v2'ye.
- **v1 çıktısı = terminal komutu** (`python -m matchlens.bulletin --date YYYY-MM-DD` gibi): o günün fikstürünü + oranları çeker, model olasılıkları, adil oran, Bet365 oranı, edge/EV ve özel market olasılıklarıyla tablo basar (+ CSV). 5 ekranlı Streamlit projenin son hali, motor oturduktan sonra.
- Sürümler hızlı çıkacak; öncelik az hata/debugging. Her modül için küçük doğrulama testleri yazılacak.
- **Hedef: 1 Kasım (Pazar) akşamı ilk canlı deneme.** Pazar maçlarının çoğu o saatte bitmiş olacağı için deneme Pazartesi-Salı fikstürleri + sonraki hafta sonu maçları üzerinde yapılır; Pazar günü oynanan maçlar da "maç öncesi verisiyle tahmin et, sonucu kontrol et" sağlama testi olarak kullanılır.

### Güncel oran kaynağı (erişim testi 1 Kasım)
| Kaynak | Durum |
| :--- | :--- |
| ESPN Bet365 preMatch | ✅ Ücretsiz. Top 5 + eng.2 + usa.1'de güncel maçlar için var, diğer liglerde çoğunlukla yok |
| API-Football (key `.env`'de, Free plan, 100 istek/gün) | ⚠️ Free plan sadece 2022-2024 sezonlarına izin veriyor → güncel oran yok. Bet365 (id 8) ve Pinnacle (id 4) destekli; Pro plan (ücretli) ile çözülür |
| The Odds API | ✅ Erişilebilir (401 = key gerekli). Ücretsiz plan 500 kredi/ay. Bet365/Pinnacle'ı hangi bölgede verdiği key alınınca doğrulanacak |
| Sportmonks / OddsPapi | ✅ Erişilebilir, key gerekli, büyük ölçüde ücretli |
| Pinnacle guest API, OddsPortal, football-data | ❌ Engelli |

Plan: ESPN Bet365 + The Odds API (ücretsiz key) birleşimi. Yetmezse API-Football Pro değerlendirilir (Çağrı'ya maliyet sorulacak).

### FootyStats (Çağrı'nın üyeliği, süresi az, CSV kredisi çok kısıtlı)
- Elde: EPL 2026/27 league/matches/players/teams/teams2 CSV'leri → `data/raw/footystats/`.
- **Maç CSV'sinin değeri (66 sütun):** maç xG'si (`team_a_xg`, `team_b_xg`) — Understat'ın olmadığı liglerde (tur/bel/den/nor/esp.2/eng.2/usa) tek xG kaynağı; gol dakikaları, İY skoru, yarı bazlı kartlar, korner, şut, faul, topa sahip olma, hakem; **oranlar: 1X2, Üst 1.5/2.5/3.5/4.5, KG Var/Yok** (KG oranı başka hiçbir kaynağımızda yok); oynanmamış maçlarda da maç öncesi oran ve pre-match xG var.
- Oranların hangi bahis şirketine ait olduğu belirsiz (muhtemelen piyasa ortalaması) → Bet365 yerine geçmez, KG ve backtest için ek referans.
- **Scraping yapılmayacak:** ücretli içerik + kredi limiti erişim kısıtlaması, kullanım şartlarına aykırı, hesap kapanma riski. Resmi API (football-data-api.com) ayrı ücretli ürün.
- **Kalan kredi öncelik sırası (sadece "matches" CSV'leri):** son 3-4 sezon için esp.2 → tur.1 → eng.2 → bel.1 → den.1 → nor.1 → usa.1 (xG + KG oranı olmayan ligler). league/teams/players CSV'leri düşük öncelik (aynılarını maç verisinden kendimiz türetiyoruz).
- Ayrıca `C:\Users\cbura\Downloads\football-events\` (Kaggle "Football Events", ~10k maç, Top 5 lig 2011-2017, 1X2/Alt-Üst/KG oranları) diskte duruyor; eski dönem ek oran verisi olarak kullanılabilir.

## 4. Mevcut Durum (commit `de73a4c` itibarıyla)
### Kod
- `data_pipeline/config.py`, `db.py`, `team_names.py` (Understat→ClubElo isimleri)
- `data_pipeline/ingest_understat.py` (şu an sadece EPL 23/24), `ingest_elo.py` (ClubElo, şu an çalışmıyor), `feature_engine.py` (rolling 3/5 xG/PPDA/Deep, rest_days, momentum), `merge_features.py` (→ `ml_master_dataset`), `run_pipeline.py` (argparse adımları)
- `data_pipeline/ingest_espn.py` + `data_pipeline/espn/{client,parse,leagues}.py`
  - `python -m data_pipeline.ingest_espn scoreboards|summaries|build|coverage|all [--leagues ..] [--from-year ..] [--to-year ..] [--sample N] [--workers 4]`
  - Ham JSON gzip önbelleği: `data/raw/espn/scoreboard/{league}/{year}.json.gz`, `data/raw/espn/summary/{league}/{event_id}.json.gz`. Bitmiş maçların summary'si bir daha çekilmez.

### Veritabanı (`database/matchlens.db`)
- ESPN: `espn_matches` (43.916 maç, 2016-2026, `events_consistent` bayrağı), `espn_match_events` (306k gol/kart olayı, dakika + yarı), `espn_team_stats`, `espn_odds` (Bet365 1X2 / Çifte Şans / gol çizgisi; şu an sadece ~2.800 summary çekildiği için az)
- Understat hattı: `tactical_match_stats`, `team_tactical_form`, `historical_club_elo`, `ml_master_dataset` (EPL 23/24, 760 satır)
- Transfermarkt: `games` (88.958, 2006-2026), `club_games`, `competitions`, `tm_clubs`
- Eski DB yedeği: `database/matchlens_legacy_backup.db` (silinebilir). `_trash/` klasörü gözden geçirilip silinebilir.

### Doğrulanmış teknik bulgular
- ESPN scoreboard `dates=YYYY&limit=1000` ile lig×yıl tek istek. Tarih aralığı formatı çalışmıyor.
- ESPN own goal, yararlanan takıma yazılıyor; olaylardan hesaplanan skor %98.1 tutarlı.
- ESPN `odds` içindeki "Bet 365" ana alanı eski maçlarda **maç sonu canlı oranı** (sızıntı). Sadece `bettingOdds.teamOdds.preMatch*` alanları kullanılıyor.
- ESPN Bet365 maç öncesi oran kapsamı: Top 5 + eng.2 2018+ iyi; tur/bel kısmi; den/nor/esp.2(2022+)/usa neredeyse yok. İstatistik kapsamı: Top 5 + eng.2 + usa 2016+ tam; esp.2 2021+; tur 2016-18 ve 2024+; bel/den/nor 2024+.
- Erişim (Türkiye bağlantısı): football-data.co.uk ❌, FBref/Sofascore 403, ClubElo 502; ESPN ✅, Understat ✅, Kaggle ✅.
- `soccerdata`'nın `TEAMNAME_REPLACEMENTS` sözlüğü varsayılan olarak boş → kaynaklar arası isim eşleştirmesini kendimiz kuracağız (doc 06'daki "kusursuz birleşme" iddiası yanlış).
- ESPN summary isteği ~20-35 KB; tam backfill ~1.2-1.3 GB.

## 5. Yarın İndirilecekler (sınırsız Wi-Fi)
Önce: Kaggle → Settings → API → "Create New Token" → `kaggle.json` dosyasını `~/.kaggle/kaggle.json` olarak kaydet (`chmod 600`). Sonra `.venv/bin/pip install kaggle`.
Ayrıca: https://the-odds-api.com adresinden ücretsiz key al, `.env` dosyasına `ODDS_API_KEY=...` olarak ekle.

| # | Ne | Boyut | Komut / Hedef |
| :--- | :--- | ---: | :--- |
| 1 | Kaggle `adamgbor/club-football-match-data-2000-2025` (football-data aynası: 42 lig, 2000-2026, İY/MS, şut, korner, faul, kart, Bet365 1X2 + 2.5 Alt/Üst + Asya handikap, max oranlar, ClubElo snapshot'ları) | ~16 MB zip | `kaggle datasets download -d adamgbor/club-football-match-data-2000-2025 -p data/raw/kaggle/club_football --unzip` |
| 2 | Kaggle `archangel0x01/football-odds-movements-2018-2026` (Pinnacle/Bet365/Singbet/SBOBET tüm maç öncesi oran hareketleri, açılış-kapanış, 1X2 + AH + Alt/Üst, 63.597 maç, 30 lig; Türkiye/Belçika/Danimarka/Norveç/İspanya 2 yok) | ~542 MB | `kaggle datasets download -d archangel0x01/football-odds-movements-2018-2026 -p data/raw/kaggle/odds_movements --unzip` |
| 3 | ESPN tüm maç summary backfill (istatistik, Bet365 maç öncesi oran, kadrolar) | ~1.2-1.3 GB, ~2 saat | `.venv/bin/python -m data_pipeline.ingest_espn summaries --workers 4 > data/logs/espn_backfill.log 2>&1` ardından `... ingest_espn build` ve `... ingest_espn coverage` |
| 4 | Understat Top 5 lig, 2014/15-2026/27 (kod genişletilecek) | tahmini <200 MB | `ingest_understat.py` çoklu lig/sezon yapılınca çalıştırılır |

1 ve 2 Çağrı tarafından hemen başlatılabilir; 3 arka planda bırakılabilir (yarıda kesilirse aynı komut kaldığı yerden devam eder). 4 kod değişikliğinden sonra.

## 6. Sıradaki İş Sırası
1. Kaggle setlerini yükleyen ingest (`ingest_kaggle.py`): lig kodu eşlemesi (football-data `E0/E1/SP2/T1/B1/...` ↔ ESPN `eng.1/eng.2/esp.2/tur.1/bel.1/...`), takım ismi eşleştirme tablosu (Kaggle ↔ ESPN ↔ Understat), DB tablolarına yazma, ESPN maçlarıyla (lig, tarih, ev, deplasman) üzerinden birleştirme ve tutarlılık kontrolü.
2. Understat'ı çoklu lig/sezona genişletmek.
3. Kendi Elo motorumuz (tüm sonuç geçmişi üzerinden, ev avantajı + gol farkı çarpanı; ClubElo snapshot'larıyla kıyas).
4. `ml_match_dataset`: maç başına tek satır, sızıntısız rolling feature'lar (gol, xG, şut, isabetli şut, korner, kart, faul, İY golleri, dakika dilimleri, Elo, dinlenme günü, piyasa olasılığı).
5. Motor 1: Dixon-Coles / Poisson (λ_H, λ_A ve yarı bazlı λ_1H, λ_2H) → skor matrisi → 1X2, Alt/Üst, KG, özel marketler.
6. Walk-forward backtest: Brier/log-loss kalibrasyon + Bet365/Pinnacle kapanışına karşı ROI. Model piyasayı yenmeden diğer motorlara geçilmez.
7. Güncel oran entegrasyonu (ESPN Bet365 + The Odds API) ve takım ismi eşleştirmesi.
8. Günlük güncelleme komutu + terminal bülteni (v1) → Pazar akşamı ilk canlı deneme.
9. v2: korner/kart motorları, Oran İkizleri (k-NN), Smart Money (archangel oran hareketleri), Streamlit UI.

Not: Pazar akşamı hedefine yetişmek için 1-6 adımları sade tutulur (önce Elo + rolling gol/şut feature'ları + Dixon-Coles; xG katmanı ve dakika feature'ları gerekirse v1.1).

## 7. Doc 06 İçin Düzeltmeler
- "16 tablo" artık geçerli değil (temizlik yapıldı).
- MatchHistory/Understat "kusursuz birleşme" yanlış (bkz. bölüm 4).
- `B365H` gerçek açılış oranı değil; football-data maçtan 1-3 gün önce topluyor, kapanış `B365CH`. Gerçek açılış/kapanış için archangel seti kullanılacak.
- Özel marketlerde "en yüksek edge" iddiası kanıtlanmamış; bu marketlerin tarihsel oranı yok, backtest edilemez.
- `game_events.csv` yerine dakika verisi ESPN'den geliyor (`espn_match_events`).
