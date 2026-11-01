# MatchLens — Yeni Oturum Başlangıç Prompt'u (v5, 2026-11-01 gece)

Yeni bir Claude Code oturumu açınca (`C:\Users\cbura\projects\MatchLens` yerel klasörü) aşağıdaki metni yapıştır.

---
**[KOPYALAMAYA BURADAN BAŞLA]**

Merhaba, ben Çağrı. MatchLens projesine devam ediyoruz. Kararları birlikte alıyoruz, kodu sen yazıyorsun, commit'i sen atıyorsun. Benimle Türkçe ve sade konuş: istatistik jargonu yerine "model %40 diyor, gerçekte %43 çıkıyor" gibi düz cümleler kur. Kötü bir şey varsa açıkça söyle, takıldığın yerde sor.

Önce şunları oku:
1. `docs/07_session_handoff.md`: ortam (Windows), ürün (Model / Oran İkizleri / Piyasa ayrı), komutlar, veri, dürüst durum, sıradaki iş (§7).
2. `docs/03_roadmap.md`: kararların geçmişi. Özellikle Aşama 5a'daki "Kuponlar", "Karne" ve "Adım 2: ayrık ridge" maddeleri.
3. `.agents/AGENTS.md`: kod stili.

Nerede kaldık (2026-11-01):
- Model Üst/Alt'ta fazla uç tahminler veriyordu, kuponlardaki Alt yığılmasının kaynağı buydu. Ayrık ridge ile düzeltildi (`dixon_coles.RIDGE=3`, `RIDGE_STYLE=30`) ve üretimde. Model "%40 Üst" dediğinde artık gerçekten ~%40 çıkıyor.
- Ardından gün boyu ince ayar denendi: sıkı log-loss kapısı, mevsimsellik, gol seviyesi takipçisi. Etkileri binde bir mertebesindeydi, hepsi geri alındı. **Model ayarı donduruldu.** Yeni ince ayar turu önerme. Model değişikliğinde ölçüt kalibrasyon.
- 2026/27 sezon başı alışılmadık derecede gollü (Tem-Eki maç başı 3.08 gol). Bet365 de kaçırdı, öngörülemez bir şok. Sadece Karne'den izleniyor.
- 01.11 tahminleri ve kuponları eski modelle (ridge 5) üretildi. 02.11 07:30 update'ten itibaren yeni model devrede. Karne'yi yorumlarken bunu ayır.
- `data/raw/kaggle/odds_movements/` altına Kaggle "football-odds-movements-2018-2026" parquet dosyaları indirildi (~300 MB: matches, match_closing, odds_1x2, odds_ou, odds_ah). Bu v2 (oran hareketleri / Smart Money) için. Ben istemedikçe kullanma.

İlk iş:
1. `data/logs/update.log` son çıktısına, `prediction_log` ve `coupon_log` tablolarına bakıp ileriye dönük tahminlerin ve kuponların durumunu birkaç cümleyle özetle: kaç maç sonuçlandı, kupon tuttu mu, yeni model ilk kez çalıştı mı.
2. Sonra devir notu §7'deki 1. işe geç: kuponları "Modelin seçtikleri" ve "İkiz oran" olarak ikiye bölmek, kupon şartında referansı Bet365/DraftKings yapmak. Başlamadan önce mevcut kupon mantığını (`matchlens/coupons.py`, `matchlens/selections.py`, `ui/pages/`) okuyup planı tek paragrafta, sade dille teyit et.

**[KOPYALAMA BURADA BİTER]**
---
