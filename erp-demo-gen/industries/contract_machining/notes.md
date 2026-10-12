# Talaşlı imalat / fason metal parça üretimi — ayar notları

`tuning.json` içindeki değerlerin gerekçesi. Üretilen bir veri seti yanlış
göründüğünde burayı güncelleyin ki sonraki üretimler daha iyi olsun.

Bu sektör, generic `manufacturing` yolundan farklı olarak kendi jeneratörünü
(`engine/gen_contract.py`), kendi görünümlerini (`engine/views_mfg.py`), kendi
doğrulamalarını (`validate._contract_checks`) ve kendi tablo uzantısını
(`engine/ddl_mfg.py`, `tables.json` içindeki `"ddl_extension": "mfg"`) kullanır.

## Temel modelleme kararları

- **Taban para birimi TRY, fiyatlar EUR referansında.** Türkiye enflasyonu 5
  yılda nominal TL fiyatlarını 3 kattan fazla artırır. Ürün fiyat ve
  maliyetleri seeds içinde EUR olarak yazılır, işlem tarihindeki kurla TL'ye
  çevrilir. Böylece TL cirosu gerçekçi biçimde şişerken EUR/USD bazında analiz
  tutarlı kalır. Sabit TL fiyatı kullanılsaydı 2022 adetleri 2026'nın üç katı
  çıkardı — yani tam ters yönde.
- **Kur çapaları YILLIK ORTALAMADIR** ve yıl ortasına (1 Temmuz) oturtulup iki
  yıl ortası arasında yürütülür. Yıl başına oturtulursa yılın ortalama kuru bir
  sonraki yıla kayar ve EUR bazlı ciro sistematik olarak ~%25 düşük çıkar.
- **Belgeye yazılan kur, 1 birim döviz karşılığı TL'dir** (53,40), 1 TL
  karşılığı döviz (0,0187) değil. İkincisi dört ondalıkta saklandığında EUR
  karşılıkları binde bir sapıyordu; ayrıca Türkiye'de kur bu yönde okunur.
  `amount_eur = amount_base / fx_rate_eur`.
- **SMM (620) yalnızca DİREKT maliyettir**: hammadde + direkt işçilik + fason +
  kesici takım. Üretim genel giderleri (enerji, üretim amortismanı, endirekt
  üretim personeli, bakım, kalite), pazarlama-satış-dağıtım, genel yönetim,
  Ar-Ge, finansman ve vergi `expenses` tablosundadır. Hiçbir kalem iki kez
  sayılmaz; tam yükleme brüt kâr `v_pnl_*` görünümlerinde ayrıca verilir.
  Direkt üretim operatörlerinin (`employees.job_family = 'Üretim'`) ücreti SMM
  içinde taşındığı için gidere yazılmaz — yazılsaydı iki kez sayılırdı.
- **Faaliyet gideri GRUP bazında toplanır, kaynak (source) bazında değil.**
  Banka komisyonu ve diğer vergi/resim/harç kalemlerinin kaynağı `purchased`
  olduğu için kaynak bazında toplansaydı hem faaliyet giderine hem
  finansman/vergi satırına girip iki kez sayılırdı.
- **Çevrim süreleri parçanın tezgah maliyeti payından türetilir**
  (`machine_alloc_pct`). Elle yazılan çevrim süreleriyle makine parkı kapasitesi
  birbirini tutmuyordu; bu yolla toplam tezgah saati ile tezgah sayısı
  kendiliğinden tutarlı olur ve `v_capacity_by_work_center` anlamlı çıkar.
- **lot_min/lot_max YILLIK adet bandıdır**, sipariş adedi değil. OEM müşteriler
  yıllık sözleşmeyi haftalık/aylık çağrı planıyla çeker; `call_off_divisor`
  bölmeyi yapar. Yıllık bandı doğrudan siparişe yazınca sipariş başına ortalama
  40 bin EUR çıkıyordu.
- **Açılış stoğu, dönem boyunca oluşan açığı da kapatır.** İptal edilen bir iş
  emri tek başına bir parçanın stok bakiyesini eksiye düşürebiliyordu.

## Gerçekçilik bantları (doğrulamalarla korunuyor)

| Kalem | Hedef | Not |
|---|---|---|
| Direkt brüt marj | %47-51 | direkt SMM üzerinden |
| Tam yükleme brüt marj | %28-32 | üretim genel giderleri dahil |
| Faaliyet kâr marjı | %10-15 | |
| Net kâr marjı | %5-12 | 2024'te faiz baskısıyla dip yapar |
| İhracat payı | %36 | AB + yakın pazarlar |
| OEE | %76-83 | kullanılabilirlik ~%88, performans ~%88 |
| İş merkezi kapasite kullanımı | %45-90 | darboğaz otomat torna ve CNC torna |
| İç hurda oranı | %1,5-2,5 | |

- **OEE'yi duruş ve performans kaybı belirler.** `downtime_chance`,
  `downtime_share` ve `performance_loss_factor` olmadan her iş merkezi %95+ OEE
  ile çalışıyor gibi görünüyordu; gerçek bir atölyede bu bant %65-85'tir.
- **ABC sınıfı fiili ciroya göre atanır** (Pareto: %80 / %15 / %5). Rastgele
  atandığında en büyük müşteri C sınıfında görünüp veri kendi içinde çelişiyordu.
- **Kapasite %100'ü aşmamalıdır.** Aşarsa darboğaz iş merkezine tezgah ekleyin
  veya vardiya sayısını artırın; operasyon `time_weight` değerlerini düşürmek
  yükü diğer iş merkezlerine kaydırdığı için genelde çözüm olmaz.

## Seeds yazım rehberi

- `products`: parça arketipleri. Varyantlar motor tarafından (Ø12, M8, Rev.C …)
  türetilir; arketip sayısı ürün sayısının 1/3'ü kadar olabilir.
- `routing_templates` + `operations`: rota şablonları operasyon kodlarına
  referans verir. Fason adımlar (`is_subcontract`) ayrı bir tedarik akışı yaratır.
- `shop_machines`: gerçek tezgah marka ve modelleri kullanılır (Citizen, Mazak,
  DMG MORI, Studer …) — kullanıcı bunu açıkça istiyor. Müşteri ve tedarikçi
  firma adları ise kurgusaldır.
- `chart_of_accounts`: Türk Tekdüzen Hesap Planı. Gider kategorilerinin
  `account_code` değerleri 730.x / 631.x / 632.x / 630.x / 660.x / 691 alt
  hesaplarına bağlanır.
- `departments[].roles[]`: kadro elle yazılır; `job_family = 'Üretim'` olanlar
  direkt işçiliktir. Toplam kadro ciro/kişi oranını belirler — 11 mn EUR ciro
  için ~130 kişi (kişi başı ~85 bin EUR) gerçekçidir; 220 kişi yazıldığında
  bordro cironun %41'ine çıkıyordu.
