# MatchLens — Yeni Oturum Başlangıç Prompt'u (v3.0, 2026-10-31)

Yeni bir Claude Code oturumu açınca aşağıdaki metni yapıştır.

---
**[KOPYALAMAYA BURADAN BAŞLA]**

Merhaba, ben Çağrı. MatchLens projesine dünkü (31 Ekim) oturumdan devam ediyoruz. Kararları birlikte alıyoruz, kodu sen yazıyorsun; adım adım ders anlatımı istemiyorum, hızlı ilerleyelim. Benimle Türkçe konuş.

**Önce şu dosyaları baştan sona oku:**
1. `docs/07_session_handoff.md` — nerede kaldığımız, alınan kararlar, doğrulanmış bulgular, indirme listesi ve sıradaki iş sırası (en önemlisi bu).
2. `docs/03_roadmap.md` — canlı yol haritası.
3. `.agents/AGENTS.md` — kod stili kuralları.
4. Gerekirse `docs/06_master_architecture_and_audit.md` (ürün vizyonu; 07'nin 7. bölümündeki düzeltmelerle birlikte oku).

**Kısa özet:** Hedefim, cumartesi sabahı açtığımda o günün maçları için model olasılıklarını Bet365 oranlarıyla kıyaslayıp en değerli bahisleri listeleyen bir motor. Dün temizliği yaptık (eski kuşak kodlar silindi), ESPN'den 12 ligin 2016-2026 arası 43.916 maçını, gol/kart dakikalarını ve fikstürünü çeken `ingest_espn.py`'yi yazdık. football-data.co.uk Türkiye'den engelli olduğu için tarihsel oran ve istatistikleri Kaggle'dan alacağız. Elo'yu kendimiz hesaplayacağız.

**Şu an sınırsız internetteyim. Yaptığım/yapacağım indirmeler:**
1. Kaggle API token'ı `~/.kaggle/kaggle.json` olarak kaydedildi ve `.venv/bin/pip install kaggle` yapıldı (yapılmadıysa önce bunu yap).
2. `kaggle datasets download -d adamgbor/club-football-match-data-2000-2025 -p data/raw/kaggle/club_football --unzip` (~16 MB)
3. `kaggle datasets download -d archangel0x01/football-odds-movements-2018-2026 -p data/raw/kaggle/odds_movements --unzip` (~542 MB)
4. ESPN tam summary backfill, arka planda: `.venv/bin/python -m data_pipeline.ingest_espn summaries --workers 4 > data/logs/espn_backfill.log 2>&1` (~1.2-1.3 GB, ~2 saat, kaldığı yerden devam eder). Bitince `build` ve `coverage`.
5. Understat Top 5 lig 2014/15-2026/27 — önce `ingest_understat.py`'yi çoklu lig/sezon için genişlet, sonra çalıştır.

İndirmelerin durumunu kontrol et (dosyalar yerinde mi, eksik olanı sen başlat), sonra `docs/07_session_handoff.md` bölüm 6'daki iş sırasına göre 1. adımdan (Kaggle ingest + lig/takım ismi eşleştirme) devam et. Her kararda roadmap'i güncelle.

**[KOPYALAMA BURADA BİTER]**
---
