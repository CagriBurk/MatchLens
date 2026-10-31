# MatchLens - Günlük Seyir Defteri (Daily Log)

Bu dosya, projede günlük olarak hangi zorluklarla karşılaşıldığını, nelerin düzeltildiğini ve hangi önemli kararların alındığını kayıt altına almak içindir.

### [Tarih: 2026-08-01]
- **Yapılanlar**: Projenin karmaşıklaşmasını önlemek ve AI araçlarıyla daha verimli çalışabilmek (context kaybını önlemek) adına `docs/` klasörü altına proje mimarisi, mevcut durum ve yol haritası dokümanları oluşturuldu.
- **Sonraki Adım**: Mevcut kodların (Streamlit, SQL, Pandas) incelenerek `02_current_state.md` dosyasının güncellenmesi.

### [Tarih: 2026-08-02]
- **Yapılanlar**: Taktiksel veri entegrasyonu (Aşama 2) için FBref yerine daha güvenilir ve NaN hatası vermeyen `soccerdata.Understat` modülüne geçiş yapıldı.
- **Düzeltilenler**: `feature_engine.py` içinde Makine Öğrenmesi (ML) için Takım Formu (Rolling Averages) ve Dinlenme Günleri (Rest Days) hesaplandı. Momentum sapması hesaplanırken oluşan "Data Leakage" (Veri sızıntısı) engellemek için Pandas `shift(1)` mantığı uygulandı.
- **Kararlar**: Makine öğrenmesine takımların tarihsel güç dengesini öğretmek için bir `EloCalculator` modülü oluşturulmasına karar verildi.

