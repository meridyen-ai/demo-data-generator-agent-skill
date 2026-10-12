# belediye-demo-gen

Kurgusal bir Türk ilçe belediyesi için uçtan uca demo veri ambarı üretir.

- **Örnek kurum**: Bahçelievler Belediyesi (İstanbul), 11 mahalle, ~592.000 nüfus
- **Dönem**: 2019-01-01 → 2026-08-31 (2026 yıl içi)
- **Hedef**: mevcut `erp_demo_pg` konteyneri, `bld_bahcelievler` veritabanı
- **Şema**: 87 tablo (İngilizce adlar) + Türkçe isimli analitik view'lar
- **İçerik dili**: Türkçe

Gerçek kişi, gerçek yönetici veya gerçek kurum kaydı içermez; tüm isimler,
firmalar, muhtarlar, meclis üyeleri ve seçim seçenekleri kurgusaldır
(seçim tablosunda "A Partisi", "B Partisi" gibi anonim etiketler kullanılır).
Mahalle adları gerçektir, sayısal veriler kurgudur.

## Çalıştırma

```bash
python3 -m engine.run build            # üret + yükle
python3 -m engine.run build --no-load  # sadece CSV
python3 -m engine.run load             # CSV'leri yükle
python3 -m engine.run summary          # bağlantı ve boyut özeti
```

## Dosya düzeni

```
engine/
  spec.py        tablo tanım DSL'i (DDL + CSV kolon sırası tek kaynaktan)
  tables.py      87 tablonun tanımı, tablo/kolon açıklamalarıyla
  world.py       ortak parametreler: mahalleler, enflasyon, bütçe, fiyat endeksi
  util.py        RNG, tarih, CSV yazıcı, Türkçe isim havuzları
  gen_base.py    mahalle, sokak, müdürlük, ünvan, tesis, tedarikçi, bütçe kodları
  gen_people.py  nüfus, hane, vatandaş, doğum, ölüm, göç, nikah, boşanma
  gen_hr.py      personel, bordro, izin, mesai, eğitim, performans
  gen_econ.py    işsizlik, işyeri, ruhsat, denetim, kurslar
  gen_property.py bina, bağımsız bölüm, emlak vergisi, ÇTV, ilan-reklam vergisi
  gen_finance.py bütçe kalemleri, gelir/gider, ihale, sözleşme, ödeme emri, kredi
  gen_services.py imar, zabıta, yol, park, aydınlatma, arıza, filo, atık, hava
  gen_social.py  sosyal yardım, aşevi, sağlık, veteriner, kültür, kütüphane, spor
  gen_civic.py   çözüm merkezi başvuruları, anketler
  gen_gov.py     meclis, encümen, seçim, defin, otopark, acil durum
  views.py       Türkçe analitik view'lar
  schema.py      spesifikasyondan DDL üretimi
  load.py        docker exec + \copy ile yükleme
  run.py         CLI
out/<slug>/      üretilen CSV'ler, schema.sql, constraints.sql, views.sql
```

## Tasarım notları

- **Tek kaynak**: kolon sırası ve tipleri yalnızca `tables.py` içinde tanımlı;
  CSV yazıcı her satırı bu spesifikasyona göre doğrular, kolon kayması
  üretim anında hata verir.
- **Determinizm**: `--seed` sabitken çıktı bit bazında aynıdır. Her üretici
  modül kendi alt-RNG'sini kullanır, bu yüzden bir modülü değiştirmek
  diğerlerinin verisini kaydırmaz.
- **Tutarlılık**: bordro toplamları bütçe personel giderini, emlak
  tahsilatı gelir hareketlerini, sözleşme hakedişleri ödeme emirlerini
  besler — yani "personel gideri / toplam gider" gibi oranlar rastgele
  değil, veriden türetilebilir.
