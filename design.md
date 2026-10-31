# MatchLens Streamlit UI/UX Tasarim Dokumani

## Genel Konsept ve Tema

MatchLens arayuzu, futbol mac verisini hizli okunabilir hale getiren modern bir analitik platform olarak kurgulanmalidir. Temel his: profesyonel, karar destek odakli, guven veren ve yogun veri icinde kullaniciyi yormayan bir deneyim.

Tema tercihi olarak koyu tema onerilir. Bahis, performans analizi ve canli veri panellerinde koyu zemin, metrik kartlari ve grafiklerin daha net ayrismasini saglar. Acik tema ikincil tercih olarak desteklenebilir, ancak varsayilan deneyim koyu olmalidir.

Renk paleti:

- Arka plan: `#0B1120`
- Yuzey / panel rengi: `#111827`
- Ikincil yuzey: `#1F2937`
- Ana vurgu: `#22C55E`
- Ikincil vurgu: `#38BDF8`
- Risk / uyari: `#F59E0B`
- Negatif sinyal: `#EF4444`
- Metin ana renk: `#F9FAFB`
- Metin ikincil renk: `#9CA3AF`
- Cizgi / ayrac: `#374151`

Gorsel dil:

- Genel arayuz veri terminali gibi soguk degil, modern bir spor analitik urunu gibi hissettirmelidir.
- Kartlar kompakt, koseleri hafif yuvarlatilmis ve metrik okumaya uygun olmalidir.
- Renkler karar sinyali olarak kullanilmalidir: yesil avantaj, sari risk/kararsizlik, kirmizi negatif sapma, mavi bilgi/analiz.
- Uzun aciklamalar yerine kisa basliklar, net metrikler ve genisletilebilir detay bloklari tercih edilmelidir.

Streamlit tema ayari icin `.streamlit/config.toml` dosyasinda su yaklasim kullanilabilir:

```toml
[theme]
base = "dark"
primaryColor = "#22C55E"
backgroundColor = "#0B1120"
secondaryBackgroundColor = "#111827"
textColor = "#F9FAFB"
font = "sans serif"
```

## Sayfa Hiyerarsisi ve Navigasyon

Navigasyon Streamlit sidebar uzerinden kurulmalidir. Sidebar hem sayfa gecisi hem de global filtreleme alani gibi calismalidir.

Sidebar menuleri:

1. Genel Bakis
2. Detayli Mac Analizi
3. Takim Form Merkezi
4. Lig ve Fikstur Kesfi
5. Model / Kural Aciklamalari
6. Ayarlar

Sidebar global bilesenleri:

- Lig secimi
- Tarih araligi secimi
- Takim filtresi
- Mac durumu filtresi: oynanmamis, tamamlanmis, tum maclar
- Minimum guven skoru filtresi
- Hızli mac ID arama kutusu

Navigasyon prensibi:

- Genel Bakis, kullanicinin uygulamaya girdiginde ilk gordugu karar paneli olmalidir.
- Detayli Mac Analizi, tek bir macin derinlemesine incelendigi ana analiz ekrani olmalidir.
- Takim Form Merkezi, takim bazli ev/deplasman form trendlerini gostermelidir.
- Model / Kural Aciklamalari, sistemin hangi metrikleri nasil yorumladigini seffaflastirmalidir.
- Ayarlar, API adresi, yenileme araligi ve gorunum tercihleri gibi teknik kontrolleri icermelidir.

## Ekran Yerlesimleri (Layouts)

### 1. Genel Bakis

Amac: Kullaniciya bugunun veya secili tarih araliginin en dikkat cekici maclarini gostermek.

Yerlesim:

- Ust bolumde genis bir baslik: `MatchLens`
- Altinda kisa aciklama: `Kural tabanli futbol mac analizi ve tahmin paneli`
- Hemen altinda 4 adet metrik karti:
  - Toplam mac sayisi
  - Analizi hazir mac sayisi
  - Yuksek guvenli secim sayisi
  - Riskli / denk mac sayisi

Streamlit bilesenleri:

```python
col1, col2, col3, col4 = st.columns(4)
col1.metric("Toplam Mac", total_matches)
col2.metric("Analiz Hazir", analyzed_matches)
col3.metric("Yuksek Guven", high_confidence_count)
col4.metric("Riskli Mac", risky_match_count)
```

Ana icerik iki sutuna ayrilmalidir:

- Sol sutun: One cikan maclar tablosu
- Sag sutun: Kisa AI analiz kartlari ve risk dagilimi

Tablo alaninda `st.dataframe` kullanilmalidir. Kolonlar:

- Match ID
- Tarih
- Lig
- Ev Sahibi
- Deplasman
- Skor
- Form Avantaji
- KG Var Egilimi
- 2.5 Ust Egilimi
- Analiz Ozeti
- Guven Seviyesi

Tabloda renk kodlama:

- `form_advantage > 0`: ev sahibi avantaji yesil ton
- `form_advantage < 0`: deplasman avantaji mavi ton
- dusuk guven veya riskli analizler sari ton

Sag panelde:

- `st.tabs(["Favoriler", "Riskli Maclar", "Gol Potansiyeli"])`
- Her sekmede kart benzeri kompakt mac ozetleri
- Kisa AI yorumu
- Detay sayfasina yonlendirecek mac ID bilgisi

### 2. Detayli Mac Analizi

Amac: Kullanicinin belirli bir maci secip tum metrikleri ve kural tabanli yorumu birlikte okumasini saglamak.

Ust arama alani:

- `st.text_input("Mac ID ile ara")`
- Alternatif olarak `st.selectbox` ile filtrelenmis mac listesi
- `Analizi Getir` butonu

Mac secildikten sonra ustte skorboard yapisi:

```text
Ev Sahibi Takim       Skor / VS       Deplasman Takim
Form: 7/10                         Form: 4/10
```

Yerlesim:

- Birinci satir: takim isimleri, tarih, lig, mac durumu
- Ikinci satir: 3 ana metrik karti
  - Form Avantaji
  - KG Var Egilimi
  - 2.5 Ust Egilimi
- Ucuncu satir: AI analiz kutusu
- Dorduncu satir: detay sekmeleri

Metrik kartlari:

```python
col1, col2, col3 = st.columns(3)
col1.metric("Form Avantaji", form_advantage, delta=advantage_label)
col2.metric("KG Var Egilimi", f"{btts_tendency:.0%}")
col3.metric("2.5 Ust Egilimi", f"{over_2_5_tendency:.0%}")
```

AI analiz kutusu:

- `st.info`, `st.success`, `st.warning` veya `st.error` analizin tonuna gore secilmelidir.
- Ornek eslesme:
  - "Ev sahibi net favori" -> `st.success`
  - "Iki takim denk, riskli mac" -> `st.warning`
  - "Veri yetersiz" -> `st.info`

Detay sekmeleri:

```python
tab1, tab2, tab3, tab4 = st.tabs([
    "Form Karsilastirma",
    "Gol Egilimleri",
    "Gecmis Maclar",
    "Kural Detaylari"
])
```

Form Karsilastirma sekmesi:

- Ev sahibi son 10 ic saha maci
- Deplasman son 10 dis saha maci
- Galibiyet, beraberlik, maglubiyet sayilari
- Gol atma ve gol yeme ortalamalari
- Bar chart veya line chart ile form trendi

Gol Egilimleri sekmesi:

- KG Var / KG Yok dagilimi
- 2.5 Ust / Alt dagilimi
- Takimlarin son 10 mac gol ortalamalari
- `st.progress` ile egilim gucu gorsellestirme

Gecmis Maclar sekmesi:

- `st.dataframe` ile mac listesi
- Kolonlar: tarih, ev sahibi, deplasman, skor, sonuc, KG, Ust/Alt
- Kullaniciya siralama ve filtreleme imkani

Kural Detaylari sekmesi:

- Hangi kuralin hangi sinyali urettigi aciklanmalidir.
- Ornek:
  - Form avantaji yuksekse favori etiketi guclenir.
  - Iki takimin KG Var oranlari yuksekse gol beklentisi artar.
  - Form farki dusuk ve gol egilimleri celiskiliyse risk etiketi verilir.

### 3. Takim Form Merkezi

Amac: Tek takim secerek ev/deplasman performansini incelemek.

Ust filtre:

- Takim secimi: `st.selectbox`
- Donem secimi: son 5, son 10, son 20 mac
- Ev/deplasman modu: `st.radio(["Tum", "Ev", "Deplasman"])`

Ana metrikler:

- Son 10 mac puan ortalamasi
- Galibiyet orani
- Mac basi gol
- Mac basi yenilen gol
- KG Var orani
- 2.5 Ust orani

Yerlesim:

- Ustte 3 veya 6 metrik karti
- Ortada form trend grafigi
- Altta detayli mac tablosu

Sekmeler:

```python
tab1, tab2, tab3 = st.tabs(["Genel Form", "Ev Performansi", "Deplasman Performansi"])
```

Genel Form:

- Son maclarin sonuc serisi
- Puan trendi
- Gol trendi

Ev Performansi:

- Ic saha maclari
- Ic saha gol atma/yeme grafigi
- Ic saha guven sinyalleri

Deplasman Performansi:

- Dis saha maclari
- Dis saha gol atma/yeme grafigi
- Dis saha risk sinyalleri

### 4. Lig ve Fikstur Kesfi

Amac: Kullaniciya genis mac havuzunda filtreleme ve firsat kesfi imkani vermek.

Filtreler:

- Lig
- Tarih araligi
- Takim
- Minimum `form_advantage`
- Minimum `btts_tendency`
- Minimum `over_2_5_tendency`
- Sadece yuksek guvenli analizler

Ana tablo:

- `st.dataframe` ile genis mac listesi
- Secilebilir satir yaklasimi
- Satir secildiginde altta kisa detay paneli

Onerilen gorunumler:

- `Favori Adaylari`
- `KG Var Adaylari`
- `2.5 Ust Adaylari`
- `Riskli / Pas Gecilebilir Maclar`

### 5. Model / Kural Aciklamalari

Amac: Kullaniciya sistemin kara kutu gibi hissettirmemesini saglamak.

Icerik bloklari:

- `form_advantage` nedir?
- `btts_tendency` nasil okunur?
- `over_2_5_tendency` nasil okunur?
- Kural tabanli AI metinleri hangi kosullarda uretilir?
- Guven seviyesi nasil yorumlanmali?

Bu sayfada `st.expander` kullanilmalidir:

```python
with st.expander("form_advantage nasil hesaplanir?"):
    st.write("Ev/deplasman form farklari, galibiyet serileri ve gol dengesi birlikte yorumlanir.")
```

Not: Bu alan bahis tavsiyesi gibi degil, veri analizi aciklamasi gibi yazilmalidir.

### 6. Ayarlar

Amac: Teknik konfigurasyonu arayuzden kontrol etmek.

Ayarlar:

- FastAPI base URL
- API timeout suresi
- Otomatik veri yenileme
- Sayfa basina mac sayisi
- Varsayilan tema
- Debug modu

Teknik durum kartlari:

- API baglantisi
- SQLite veri guncelligi
- Son veri cekme zamani
- Backend saglik kontrolu

## Kullanici Akisi

### Ilk Giris

1. Kullanici uygulamayi acar.
2. Genel Bakis sayfasi otomatik yuklenir.
3. Sidebar'da varsayilan tarih araligi bugun veya en yakin fikstur olarak gelir.
4. Ust metrik kartlarindan sistemin genel durumunu okur.
5. One cikan maclar tablosundan ilgisini ceken maci bulur.

### Mac ID ile Arama

1. Kullanici sidebar'daki hizli mac ID arama kutusuna ID girer.
2. Sistem ID'yi FastAPI endpoint'ine gonderir.
3. Mac bulunursa kullanici Detayli Mac Analizi sayfasina yonlendirilir.
4. Mac bulunamazsa net bir uyari gosterilir: `Bu ID ile eslesen mac bulunamadi.`

### Detayli Analiz Okuma

1. Kullanici once takim isimleri, tarih ve mac durumunu gorur.
2. Ardindan 3 ana metrik kartini okur:
   - Form avantaji
   - KG Var egilimi
   - 2.5 Ust egilimi
3. AI analiz kutusu kullaniciya kisa yorum sunar.
4. Kullanici daha fazla detay isterse sekmeler arasinda gezer.
5. Gecmis maclar ve form trendleriyle kararini destekler.

### Takim Form Inceleme

1. Kullanici Takim Form Merkezi sayfasina gecer.
2. Bir takim secer.
3. Ev, deplasman veya tum maclar filtresini belirler.
4. Son 10 maclik formu grafik ve metriklerle inceler.
5. Takimin yaklasan maclardaki sinyallerini Genel Bakis veya Lig ve Fikstur Kesfi ekraninda karsilastirir.

## Streamlit Bilesen Stratejisi

Kullanilmasi onerilen temel bilesenler:

- `st.sidebar`: navigasyon ve global filtreler
- `st.columns`: metrik kartlari ve iki kolonlu analiz yerlesimleri
- `st.metric`: ana sayisal sinyaller
- `st.tabs`: detay ekranlarinda bilgi mimarisini sade tutmak
- `st.dataframe`: mac listeleri ve gecmis performans tablolari
- `st.expander`: kural aciklamalari ve teknik detaylar
- `st.progress`: egilim gucu gosterimi
- `st.line_chart`, `st.bar_chart`: hizli form ve gol trendleri
- `st.cache_data`: API ve veritabani sorgularinda performans

## Veri Gosterim Prensipleri

- Her metrik tek basina degil, yorumuyla birlikte sunulmalidir.
- Kullaniciya ham veri, skor ve AI yorum ayni ekranda baglamli bicimde verilmelidir.
- Riskli maclar saklanmamali, acikca etiketlenmelidir.
- Yuzdeler mumkunse yuvarlanmis verilmelidir.
- Form farki, gol egilimi ve AI yorumu birbiriyle celisiyorsa bu durum sari risk etiketiyle gosterilmelidir.

## Mikro Etkilesimler ve Durumlar

Yuklenme durumlari:

- API sorgularinda `st.spinner("Analiz getiriliyor...")`
- Bos veri durumunda sade ve net mesaj
- Hata durumunda teknik detayi expander icinde gosteren kullanici dostu uyari

Bos durum mesajlari:

- `Secili filtrelerle eslesen mac bulunamadi.`
- `Bu takim icin yeterli form verisi yok.`
- `Analiz henuz uretilmemis.`

Basari durumlari:

- `Analiz basariyla yuklendi.`
- `Veriler guncellendi.`

## Onerilen Sayfa Sirasi

Ilk MVP icin gelistirme sirasi:

1. Genel Bakis
2. Detayli Mac Analizi
3. Takim Form Merkezi
4. Lig ve Fikstur Kesfi
5. Model / Kural Aciklamalari
6. Ayarlar

Bu sira, once karar degeri yuksek ekranlari tamamlayip daha sonra kesif ve konfigurasyon katmanlarini eklemeyi saglar.

## Genel Tasarim Karari

MatchLens, Streamlit'in hizli gelistirme avantajini korurken siradan bir tablo uygulamasi gibi gorunmemelidir. Arayuz; koyu temali, net metrik kartlari olan, maclari karsilastirmayi kolaylastiran ve kural tabanli analizleri guvenilir sekilde sunan bir futbol veri analiz paneli olarak tasarlanmalidir.

Kullanicinin ana hedefi tek tek veri okumak degil, mac hakkinda hizli ve gerekceli bir kanaate ulasmaktir. Bu nedenle her sayfada su uc soru yanitlanmalidir:

1. Bu macta hangi taraf veya sonuc tipi one cikiyor?
2. Bu sinyal ne kadar guvenilir?
3. Hangi veri bu yorumu destekliyor?
