---
name: belediye-demo-gen
description: Generate a realistic fictional Turkish municipality (belediye) demo database in Postgres — population, births/deaths, unemployment, property tax, budget/revenue/expense, payroll, permits, waste, social aid, citizen requests, surveys, council decisions. Use when the user wants municipal/public-sector demo data, a "belediye" analytics demo, or fake city/district data for a presales demo. Not for ERP/company data (use erp-demo-gen for that).
---

# belediye-demo-gen

Kurgusal ama tutarlı bir **belediye** veri ambarı üretir ve mevcut
`erp_demo_pg` Postgres konteynerine `bld_<slug>` adıyla yükler.

Bu skill bir ERP üreticisi **değildir**. Şirket/üretim/satış verisi için
`erp-demo-gen` kullanın. Buradaki konu: bir ilçe belediyesinin sahip olduğu
veri — nüfus, doğum/ölüm, işsizlik, emlak vergisi, bütçe, personel maaşları,
imar, zabıta, temizlik, sosyal yardım, çözüm merkezi başvuruları, anketler,
meclis kararları.

## Ne zaman kullanılır

- "Belediyeye demo yapacağım, veri üret"
- "Nüfus / işsizlik / ölüm / anket / bütçe verisi olsun"
- "Belediye personeli maaşları, giderleri, gelirleri"
- Kamu sektörü / yerel yönetim analitik demosu

## Hızlı kullanım

```bash
cd .claude/skills/belediye-demo-gen

# üret + yükle (varsayılan: Bahçelievler, 2019-01-01 .. 2026-08-31)
python3 -m engine.run build

# sadece CSV üret, yükleme
python3 -m engine.run build --no-load

# önceden üretilmiş CSV'leri yükle
python3 -m engine.run load

# özet
python3 -m engine.run summary
```

Aynı `--seed` ⇒ aynı veri. Yeniden `build` çalıştırmak veritabanını
drop edip yeniden oluşturur (idempotent).

## Ön koşul

`erp_demo_pg` konteyneri **çalışıyor olmalı** — bu skill kendi Postgres'ini
ayağa kaldırmaz, mevcut olanı kullanır:

```bash
docker ps --format '{{.Names}}\t{{.Status}}' | grep erp_demo_pg
```

Yüklemede volume mount gerekmez: CSV'ler `docker exec -i` üzerinden
client-side `\copy ... FROM STDIN` ile akıtılır.

Bağlantı:
- host'tan: `postgresql://demo:demo@localhost:5544/bld_bahcelievler`
- başka konteynerden: `postgresql://demo:demo@erp_demo_pg:5432/bld_bahcelievler`

## Konvansiyonlar

- **Tablo ve kolon adları İngilizce**, **içerik Türkçe** (statü, tür, ad,
  açıklama). Mevcut `erp_*` veritabanlarıyla aynı kural.
- Her tabloda ve her kolonda `COMMENT` var — snapshot/LLM tarafı için.
- Ek olarak **Türkçe isimli analitik view'lar** (`v_*`) üretilir.
- Para birimi TL; tüm tutarlar yıllık TÜFE ile ölçeklenir
  (2019 = 1.00 → 2026 ≈ 9.92), yani 2019 ve 2025 rakamları gerçekçi biçimde
  farklı büyüklüktedir.

## Veri modeli (16 konu alanı, 87 tablo)

| Alan | Ana tablolar |
|---|---|
| Coğrafya | `district`, `neighborhood` (11 mahalle), `street` |
| Nüfus | `population_stat`, `household`, `citizen`, `birth_record`, `death_record`, `migration_stat`, `marriage_record`, `divorce_stat` |
| İşgücü | `unemployment_stat`, `business`, `business_license`, `business_inspection`, `vocational_course`, `course_enrollment` |
| Emlak/vergi | `building`, `property_unit`, `property_declaration`, `property_tax_assessment`, `property_tax_payment`, `environmental_tax`, `advertisement_tax` |
| Mali | `fiscal_year`, `functional_code`, `economic_code`, `budget_line`, `revenue_transaction`, `expense_transaction`, `supplier`, `tender`, `contract`, `payment_order`, `municipal_loan` |
| Personel | `directorate` (30 müdürlük), `job_title`, `employee`, `payroll`, `leave_record`, `overtime_record`, `training_record`, `performance_review` |
| İmar | `zoning_application`, `building_permit`, `occupancy_permit`, `earthquake_risk_survey` |
| Zabıta | `municipal_police_action`, `penalty_decision` |
| Altyapı/filo | `road_work`, `park`, `street_light`, `infrastructure_fault`, `vehicle`, `fuel_log`, `vehicle_maintenance`, `municipal_facility`, `facility_energy_usage` |
| Çevre | `waste_collection`, `recycling_stat`, `air_quality_measurement` |
| Sosyal yardım | `social_aid_application`, `aid_payment`, `soup_kitchen_daily` |
| Sağlık | `health_center`, `clinic_visit`, `veterinary_record` |
| Kültür/spor | `event`, `event_attendance`, `library`, `book_loan`, `sports_membership` |
| Vatandaş ilişkileri | `request_category`, `service_request`, `service_request_log` |
| Anket | `survey`, `survey_question`, `survey_respondent`, `survey_answer` |
| Yönetişim/diğer | `council_meeting`, `council_decision`, `committee_decision`, `election_result`, `burial_record`, `parking_lot`, `parking_transaction`, `emergency_call` |

## Veriye gömülü hikâyeler (demoda anlatılacak)

- **Pandemi**: 2020-2021'de ölümler ~%20 artar, ölüm nedeni "Enfeksiyon
  hastalıkları / COVID-19" payı üçe katlanır; etkinlik sayısı yarıya düşer;
  sosyal yardım başvuruları %60 sıçrar.
- **Sosyoekonomik eşitsizlik**: Alt-Orta segment mahallelerde (Yenibosna,
  Şirinevler, Çobançeşme, Soğanlı) işsizlik ~3 puan yüksek, yardım yoğunluğu
  ve başvuru sayısı fazla, anket memnuniyeti düşük.
- **Enflasyon**: bütçe 2019'da ~720 mn TL, 2026'da ~10,6 mlr TL; personel
  gideri/bütçe oranı, kişi başı harcama gibi oranlar bu yüzden anlamlı.
- **Dijitalleşme**: başvuru kanalı 2019'da çağrı merkezi ağırlıklı,
  2026'da mobil uygulama ağırlıklı; otopark işlemleri 2021'de başlar.
- **Deprem/kentsel dönüşüm**: 1980 öncesi ve yığma binalarda risk sınıfı
  yüksek, `earthquake_risk_survey` ve `urban_renewal_status` ile izlenir.
- **Sıfır atık**: geri kazanım oranı 2019 %6,2'den 2026 %14 civarına çıkar.
- **Tahsilat**: emlak vergisi tahsilat oranı ~%75, gecikme zammı, borçlu
  mükellef listesi (`v_vergi_borclu_mukellefler`) çıkarılabilir.

## Öne çıkan view'lar

`v_baskanlik_panosu` (yıllık kurumsal karne), `v_mahalle_nufus_ozeti`,
`v_dogum_olum_dengesi`, `v_olum_nedenleri`, `v_issizlik_ozeti`,
`v_emlak_vergi_tahakkuk_tahsilat`, `v_butce_gerceklesme`,
`v_gelir_gider_ozeti`, `v_kisi_basi_harcama`, `v_personel_gideri`,
`v_mudurluk_basvuru_performansi`, `v_anket_mahalle_karnesi`,
`v_atik_toplama_ozeti`, `v_sosyal_yardim_ozeti`, `v_ihale_ozeti`.

Tam liste: `engine/views.py` veya
`SELECT table_name, obj_description(...) FROM information_schema.views`.

## Başka bir belediye üretmek

`engine/world.py` içindeki `MAHALLELER`, `BUTCE` ve `engine/gen_base.py`
içindeki `MUDURLUKLER`/`TESIS_SABLON` listelerini değiştirip
`--slug <yeni_slug>` ile çalıştırın. Şema aynı kalır.

## Sonraki adım

Veritabanı hazır olduğunda `snapshot-builder` skill'i ile bu bağlantı için
snapshot üretilebilir — kolon yorumları ve Türkçe view'lar oradaki
LLM sorgu yazıcısının işini kolaylaştırmak için tasarlandı.
