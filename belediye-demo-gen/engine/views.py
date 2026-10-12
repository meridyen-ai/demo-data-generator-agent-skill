# -*- coding: utf-8 -*-
"""Turkce isimli analitik view'lar."""
from __future__ import annotations

VIEWS = [

# ===================================================== NUFUS VE DEMOGRAFI
("v_mahalle_nufus_ozeti", "Mahalle ve yil bazinda toplam nufus, cinsiyet dagilimi ve yogunluk", """
SELECT p.year                                              AS yil,
       n.neighborhood_id                                   AS mahalle_id,
       n.neighborhood_name                                 AS mahalle,
       n.socioeconomic_segment                             AS segment,
       sum(p.population)                                   AS toplam_nufus,
       sum(p.population) FILTER (WHERE p.gender = 'E')      AS erkek_nufus,
       sum(p.population) FILTER (WHERE p.gender = 'K')      AS kadin_nufus,
       sum(p.citizen_foreign_count)                        AS yabanci_nufus,
       round(sum(p.population) / n.area_km2)               AS km2_basina_nufus,
       round(100.0 * sum(p.population) FILTER (
             WHERE p.age_band IN ('0-4','5-9','10-14')) / NULLIF(sum(p.population),0), 2)
                                                           AS cocuk_orani_yuzde,
       round(100.0 * sum(p.population) FILTER (
             WHERE p.age_band IN ('65-69','70-74','75-79','80+')) / NULLIF(sum(p.population),0), 2)
                                                           AS yasli_orani_yuzde
FROM population_stat p
JOIN neighborhood n ON n.neighborhood_id = p.neighborhood_id
GROUP BY p.year, n.neighborhood_id, n.neighborhood_name, n.socioeconomic_segment, n.area_km2
"""),

("v_yas_piramidi", "Yil, yas grubu ve cinsiyet bazinda ilce nufus piramidi", """
SELECT year AS yil, age_band AS yas_grubu, gender AS cinsiyet,
       sum(population) AS nufus,
       round(100.0 * sum(population) / sum(sum(population)) OVER (PARTITION BY year), 3) AS pay_yuzde
FROM population_stat
GROUP BY year, age_band, gender
"""),

("v_dogum_olum_dengesi", "Yil ve mahalle bazinda dogum, olum, dogal artis ve kaba hizlar", """
WITH d AS (
  SELECT extract(year FROM birth_date)::int AS yil, neighborhood_id, count(*) AS dogum
  FROM birth_record GROUP BY 1, 2),
o AS (
  SELECT extract(year FROM death_date)::int AS yil, neighborhood_id, count(*) AS olum
  FROM death_record GROUP BY 1, 2),
n AS (
  SELECT year AS yil, neighborhood_id, sum(population) AS nufus
  FROM population_stat GROUP BY 1, 2)
SELECT n.yil, nb.neighborhood_name AS mahalle, n.nufus,
       COALESCE(d.dogum, 0) AS dogum, COALESCE(o.olum, 0) AS olum,
       COALESCE(d.dogum, 0) - COALESCE(o.olum, 0) AS dogal_artis,
       round(1000.0 * COALESCE(d.dogum,0) / NULLIF(n.nufus,0), 2) AS kaba_dogum_hizi_binde,
       round(1000.0 * COALESCE(o.olum,0) / NULLIF(n.nufus,0), 2) AS kaba_olum_hizi_binde
FROM n
JOIN neighborhood nb ON nb.neighborhood_id = n.neighborhood_id
LEFT JOIN d ON d.yil = n.yil AND d.neighborhood_id = n.neighborhood_id
LEFT JOIN o ON o.yil = n.yil AND o.neighborhood_id = n.neighborhood_id
"""),

("v_olum_nedenleri", "Yil ve olum nedeni grubuna gore olum sayilari ve ortalama yas", """
SELECT extract(year FROM death_date)::int AS yil,
       cause_group AS olum_nedeni_grubu,
       gender AS cinsiyet,
       count(*) AS olum_sayisi,
       round(avg(age_at_death), 1) AS ortalama_yas,
       round(100.0 * count(*) / sum(count(*)) OVER (PARTITION BY extract(year FROM death_date)::int), 2)
         AS pay_yuzde
FROM death_record
GROUP BY 1, 2, 3
"""),

("v_aylik_olum_trendi", "Aylik olum sayilari ve 12 aylik hareketli ortalama", """
SELECT date_trunc('month', death_date)::date AS ay,
       count(*) AS olum_sayisi,
       count(*) FILTER (WHERE cause_detail = 'COVID-19') AS covid_olum,
       round(avg(count(*)) OVER (ORDER BY date_trunc('month', death_date)::date
             ROWS BETWEEN 11 PRECEDING AND CURRENT ROW), 1) AS hareketli_ort_12ay
FROM death_record
GROUP BY 1
"""),

("v_dogum_profili", "Yil bazinda dogum sayisi, sezaryen orani ve anne yasi", """
SELECT extract(year FROM birth_date)::int AS yil,
       count(*) AS dogum_sayisi,
       round(100.0 * count(*) FILTER (WHERE delivery_type = 'Sezaryen') / count(*), 2) AS sezaryen_orani,
       round(avg(mother_age), 1) AS ortalama_anne_yasi,
       round(avg(birth_weight_gram)) AS ortalama_dogum_agirligi_gr,
       count(*) FILTER (WHERE is_multiple_birth) AS cogul_dogum,
       round(100.0 * count(*) FILTER (WHERE gender = 'E') / count(*), 2) AS erkek_bebek_orani
FROM birth_record GROUP BY 1
"""),

("v_goc_dengesi", "Ay ve mahalle bazinda gelen-giden goc ve net goc", """
SELECT m.period_month AS ay, n.neighborhood_name AS mahalle,
       sum(m.person_count) FILTER (WHERE m.direction = 'Gelen') AS gelen_kisi,
       sum(m.person_count) FILTER (WHERE m.direction = 'Giden') AS giden_kisi,
       sum(m.person_count) FILTER (WHERE m.direction = 'Gelen')
         - sum(m.person_count) FILTER (WHERE m.direction = 'Giden') AS net_goc
FROM migration_stat m
JOIN neighborhood n ON n.neighborhood_id = m.neighborhood_id
GROUP BY 1, 2
"""),

("v_nikah_ozeti", "Yil bazinda nikah sayilari, ortalama yas ve ucret geliri", """
SELECT extract(year FROM marriage_date)::int AS yil,
       count(*) AS nikah_sayisi,
       round(avg(groom_age), 1) AS ortalama_damat_yasi,
       round(avg(bride_age), 1) AS ortalama_gelin_yasi,
       count(*) FILTER (WHERE foreign_spouse_flag) AS yabanci_esli_nikah,
       round(sum(fee_amount), 2) AS toplam_nikah_geliri_tl
FROM marriage_record GROUP BY 1
"""),

("v_hane_profili", "Mahalle bazinda hane buyuklugu, gelir bandi ve konut sahiplik profili", """
SELECT n.neighborhood_name AS mahalle, n.socioeconomic_segment AS segment,
       count(*) AS hane_sayisi,
       round(avg(h.member_count), 2) AS ortalama_hane_buyuklugu,
       sum(h.child_count) AS toplam_cocuk,
       sum(h.elderly_count) AS toplam_yasli,
       sum(h.disabled_count) AS engelli_bireyli_hane,
       round(100.0 * count(*) FILTER (WHERE h.tenure_type = 'Kiracı') / count(*), 2) AS kiraci_orani,
       round(100.0 * count(*) FILTER (WHERE h.income_band IN ('0-15.000 TL','15.001-25.000 TL'))
             / count(*), 2) AS dusuk_gelirli_hane_orani
FROM household h JOIN neighborhood n ON n.neighborhood_id = h.neighborhood_id
GROUP BY 1, 2
"""),

# ===================================================== ISGUCU VE EKONOMI
("v_issizlik_ozeti", "Yil-ceyrek bazinda ilce issizlik orani ve isgucune katilim", """
SELECT year AS yil, quarter AS ceyrek,
       sum(labor_force) AS isgucu, sum(unemployed_count) AS issiz_sayisi,
       round(100.0 * sum(unemployed_count) / NULLIF(sum(labor_force),0), 2) AS issizlik_orani,
       round(100.0 * sum(unemployed_count) FILTER (WHERE gender='K')
             / NULLIF(sum(labor_force) FILTER (WHERE gender='K'),0), 2) AS kadin_issizlik_orani,
       round(100.0 * sum(unemployed_count) FILTER (WHERE age_band='15-24')
             / NULLIF(sum(labor_force) FILTER (WHERE age_band='15-24'),0), 2) AS genc_issizlik_orani,
       sum(informal_employment_count) AS kayit_disi_calisan
FROM unemployment_stat GROUP BY 1, 2
"""),

("v_mahalle_issizlik", "Mahalle bazinda yillik ortalama issizlik orani", """
SELECT u.year AS yil, n.neighborhood_name AS mahalle, n.socioeconomic_segment AS segment,
       sum(u.labor_force) AS isgucu, sum(u.unemployed_count) AS issiz,
       round(100.0 * sum(u.unemployed_count) / NULLIF(sum(u.labor_force),0), 2) AS issizlik_orani
FROM unemployment_stat u JOIN neighborhood n ON n.neighborhood_id = u.neighborhood_id
GROUP BY 1, 2, 3
"""),

("v_isyeri_ozeti", "Sektor ve mahalle bazinda faal isyeri sayisi ve istihdam", """
SELECT n.neighborhood_name AS mahalle, b.sector AS sektor,
       count(*) AS isyeri_sayisi,
       count(*) FILTER (WHERE b.status = 'Faal') AS faal_isyeri,
       sum(b.employee_count) FILTER (WHERE b.status = 'Faal') AS istihdam,
       round(avg(b.employee_count), 2) AS ortalama_calisan
FROM business b JOIN neighborhood n ON n.neighborhood_id = b.neighborhood_id
GROUP BY 1, 2
"""),

("v_isyeri_acilis_kapanis", "Yil bazinda isyeri acilis, kapanis ve net degisim", """
WITH a AS (SELECT extract(year FROM open_date)::int AS yil, count(*) AS acilis
           FROM business GROUP BY 1),
     k AS (SELECT extract(year FROM close_date)::int AS yil, count(*) AS kapanis
           FROM business WHERE close_date IS NOT NULL GROUP BY 1)
SELECT COALESCE(a.yil, k.yil) AS yil, COALESCE(a.acilis,0) AS acilan_isyeri,
       COALESCE(k.kapanis,0) AS kapanan_isyeri,
       COALESCE(a.acilis,0) - COALESCE(k.kapanis,0) AS net_degisim
FROM a FULL JOIN k ON a.yil = k.yil
WHERE COALESCE(a.yil, k.yil) BETWEEN 2019 AND 2026
"""),

("v_ruhsat_performansi", "Yil ve ruhsat turune gore basvuru, onay orani ve ortalama sure", """
SELECT extract(year FROM application_date)::int AS yil, license_type AS ruhsat_turu,
       count(*) AS basvuru_sayisi,
       count(*) FILTER (WHERE status = 'Onaylandı') AS onaylanan,
       round(100.0 * count(*) FILTER (WHERE status = 'Onaylandı') / count(*), 2) AS onay_orani,
       round(avg(processing_days), 1) AS ortalama_sure_gun,
       round(sum(fee_amount), 2) AS toplam_harc_tl
FROM business_license GROUP BY 1, 2
"""),

("v_isyeri_denetim_ozeti", "Yil ve denetim sonucuna gore isyeri denetimleri", """
SELECT extract(year FROM i.inspection_date)::int AS yil, i.inspection_type AS denetim_turu,
       i.result AS sonuc, count(*) AS denetim_sayisi,
       round(avg(i.score), 1) AS ortalama_puan,
       sum(i.finding_count) AS toplam_uygunsuzluk
FROM business_inspection i GROUP BY 1, 2, 3
"""),

("v_kurs_basari", "Kurs kategorisi ve donem bazinda kayit, tamamlama ve istihdam", """
SELECT c.term AS donem, c.category AS kategori,
       count(DISTINCT c.vocational_course_id) AS kurs_sayisi,
       count(e.course_enrollment_id) AS kursiyer_sayisi,
       count(*) FILTER (WHERE e.status = 'Tamamladı') AS tamamlayan,
       round(100.0 * count(*) FILTER (WHERE e.status = 'Tamamladı')
             / NULLIF(count(e.course_enrollment_id),0), 2) AS tamamlama_orani,
       count(*) FILTER (WHERE e.employed_after_course) AS ise_yerlesen,
       round(avg(e.satisfaction_score), 2) AS memnuniyet_ort,
       round(sum(c.cost_amount) / NULLIF(count(DISTINCT c.vocational_course_id),0), 2)
         AS kurs_basina_maliyet_tl
FROM vocational_course c
LEFT JOIN course_enrollment e ON e.vocational_course_id = c.vocational_course_id
GROUP BY 1, 2
"""),

# ===================================================== EMLAK VE VERGI
("v_emlak_vergi_tahakkuk_tahsilat", "Yil ve mahalle bazinda emlak vergisi tahakkuk/tahsilat ve tahsilat orani", """
SELECT a.tax_year AS yil, n.neighborhood_name AS mahalle,
       count(*) AS tahakkuk_sayisi,
       round(sum(a.assessed_amount), 2) AS tahakkuk_tl,
       round(sum(a.penalty_amount), 2) AS gecikme_zammi_tl,
       round(COALESCE(sum(p.tahsil), 0), 2) AS tahsilat_tl,
       round(100.0 * COALESCE(sum(p.tahsil),0) / NULLIF(sum(a.assessed_amount),0), 2)
         AS tahsilat_orani_yuzde,
       count(*) FILTER (WHERE a.status = 'Ödenmedi') AS odenmeyen_tahakkuk
FROM property_tax_assessment a
JOIN neighborhood n ON n.neighborhood_id = a.neighborhood_id
LEFT JOIN (SELECT property_tax_assessment_id, sum(amount) AS tahsil
           FROM property_tax_payment GROUP BY 1) p
       ON p.property_tax_assessment_id = a.property_tax_assessment_id
GROUP BY 1, 2
"""),

("v_vergi_borclu_mukellefler", "Odenmemis emlak vergisi borcu olan mukellefler", """
SELECT c.citizen_id AS vatandas_id, c.full_name AS ad_soyad,
       n.neighborhood_name AS mahalle,
       count(*) AS odenmemis_taksit,
       round(sum(a.total_due), 2) AS toplam_borc_tl,
       min(a.tax_year) AS en_eski_borc_yili
FROM property_tax_assessment a
JOIN citizen c ON c.citizen_id = a.citizen_id
JOIN neighborhood n ON n.neighborhood_id = a.neighborhood_id
WHERE a.status IN ('Ödenmedi', 'Kısmi ödendi')
GROUP BY 1, 2, 3
"""),

("v_tahsilat_kanali", "Emlak vergisi tahsilatinin kanal bazinda yillik dagilimi", """
SELECT extract(year FROM payment_date)::int AS yil, channel AS kanal,
       count(*) AS islem_sayisi, round(sum(amount), 2) AS tutar_tl,
       round(100.0 * count(*) FILTER (WHERE is_late) / count(*), 2) AS gec_odeme_orani,
       round(avg(late_days) FILTER (WHERE is_late), 1) AS ortalama_gecikme_gun
FROM property_tax_payment GROUP BY 1, 2
"""),

("v_yerel_vergi_gelirleri", "Yil bazinda emlak, CTV ve ilan-reklam vergisi tahsilatlari", """
WITH e AS (SELECT extract(year FROM payment_date)::int AS yil, sum(amount) AS emlak
           FROM property_tax_payment GROUP BY 1),
     c AS (SELECT tax_year AS yil, sum(collected_amount) AS ctv
           FROM environmental_tax GROUP BY 1),
     i AS (SELECT tax_year AS yil, sum(collected_amount) AS ilan
           FROM advertisement_tax GROUP BY 1)
SELECT COALESCE(e.yil, c.yil, i.yil) AS yil,
       round(COALESCE(e.emlak,0), 2) AS emlak_vergisi_tl,
       round(COALESCE(c.ctv,0), 2)   AS cevre_temizlik_vergisi_tl,
       round(COALESCE(i.ilan,0), 2)  AS ilan_reklam_vergisi_tl,
       round(COALESCE(e.emlak,0) + COALESCE(c.ctv,0) + COALESCE(i.ilan,0), 2) AS toplam_tl
FROM e FULL JOIN c ON e.yil = c.yil FULL JOIN i ON COALESCE(e.yil,c.yil) = i.yil
"""),

("v_bina_stogu", "Mahalle bazinda bina stoku, yas profili ve deprem risk dagilimi", """
SELECT n.neighborhood_name AS mahalle, count(*) AS bina_sayisi,
       round(avg(2026 - b.construction_year), 1) AS ortalama_bina_yasi,
       sum(b.unit_count) AS bagimsiz_bolum,
       count(*) FILTER (WHERE b.earthquake_risk_class IN ('Yüksek','Acil riskli')) AS riskli_bina,
       round(100.0 * count(*) FILTER (WHERE b.earthquake_risk_class IN ('Yüksek','Acil riskli'))
             / count(*), 2) AS riskli_bina_orani,
       count(*) FILTER (WHERE NOT b.has_occupancy_permit) AS iskansiz_bina,
       count(*) FILTER (WHERE b.urban_renewal_status <> 'Kapsam dışı') AS donusum_surecinde
FROM building b JOIN neighborhood n ON n.neighborhood_id = b.neighborhood_id
GROUP BY 1
"""),

("v_deprem_risk_tespitleri", "Yil ve mahalle bazinda risk tespit sonuclari ve kira yardimi", """
SELECT extract(year FROM s.survey_date)::int AS yil, n.neighborhood_name AS mahalle,
       count(*) AS tespit_sayisi,
       count(*) FILTER (WHERE s.risk_result = 'Riskli') AS riskli_cikan,
       count(*) FILTER (WHERE s.demolition_date IS NOT NULL) AS yikilan,
       round(avg(s.concrete_strength_mpa), 2) AS ortalama_beton_dayanimi,
       round(sum(s.rental_aid_amount), 2) AS toplam_kira_yardimi_tl
FROM earthquake_risk_survey s JOIN neighborhood n ON n.neighborhood_id = s.neighborhood_id
GROUP BY 1, 2
"""),

# ===================================================== MALI TABLOLAR
("v_butce_gerceklesme", "Yil ve yon bazinda butce odenegi ve gerceklesme orani", """
SELECT b.year AS yil, b.direction AS yon,
       round(sum(b.initial_appropriation), 2) AS baslangic_odenegi_tl,
       round(sum(b.revised_appropriation), 2) AS revize_odenek_tl,
       round(sum(b.realized_amount), 2) AS gerceklesen_tl,
       round(100.0 * sum(b.realized_amount) / NULLIF(sum(b.revised_appropriation),0), 2)
         AS gerceklesme_orani
FROM budget_line b GROUP BY 1, 2
"""),

("v_mudurluk_butce_performansi", "Mudurluk bazinda yillik odenek ve gerceklesme", """
SELECT b.year AS yil, d.directorate_name AS mudurluk, d.service_group AS hizmet_grubu,
       round(sum(b.revised_appropriation), 2) AS odenek_tl,
       round(sum(b.realized_amount), 2) AS harcama_tl,
       round(100.0 * sum(b.realized_amount) / NULLIF(sum(b.revised_appropriation),0), 2)
         AS gerceklesme_orani
FROM budget_line b JOIN directorate d ON d.directorate_id = b.directorate_id
WHERE b.direction = 'Gider'
GROUP BY 1, 2, 3
"""),

("v_gelir_gider_ozeti", "Yil bazinda toplam gelir, gider ve butce dengesi", """
WITH g AS (SELECT year AS yil, sum(amount) AS gelir FROM revenue_transaction GROUP BY 1),
     h AS (SELECT year AS yil, sum(total_amount) AS gider FROM expense_transaction GROUP BY 1)
SELECT g.yil, round(g.gelir, 2) AS toplam_gelir_tl, round(h.gider, 2) AS toplam_gider_tl,
       round(g.gelir - h.gider, 2) AS butce_dengesi_tl,
       round(100.0 * (g.gelir - h.gider) / NULLIF(g.gelir,0), 2) AS denge_orani_yuzde
FROM g JOIN h ON g.yil = h.yil
"""),

("v_gelir_turleri", "Gelir turu bazinda yillik tahsilat ve pay", """
SELECT year AS yil, revenue_type AS gelir_turu,
       count(*) AS islem_sayisi, round(sum(amount), 2) AS tutar_tl,
       round(100.0 * sum(amount) / sum(sum(amount)) OVER (PARTITION BY year), 2) AS pay_yuzde
FROM revenue_transaction GROUP BY 1, 2
"""),

("v_gider_turleri", "Gider turu bazinda yillik harcama ve pay", """
SELECT year AS yil, expense_type AS gider_turu,
       count(*) AS islem_sayisi, round(sum(total_amount), 2) AS tutar_tl,
       round(100.0 * sum(total_amount) / sum(sum(total_amount)) OVER (PARTITION BY year), 2)
         AS pay_yuzde
FROM expense_transaction GROUP BY 1, 2
"""),

("v_aylik_nakit_akisi", "Aylik gelir, gider ve net nakit akisi", """
WITH g AS (SELECT date_trunc('month', transaction_date)::date AS ay, sum(amount) AS gelir
           FROM revenue_transaction GROUP BY 1),
     h AS (SELECT date_trunc('month', transaction_date)::date AS ay, sum(total_amount) AS gider
           FROM expense_transaction GROUP BY 1)
SELECT COALESCE(g.ay, h.ay) AS ay,
       round(COALESCE(g.gelir,0), 2) AS gelir_tl,
       round(COALESCE(h.gider,0), 2) AS gider_tl,
       round(COALESCE(g.gelir,0) - COALESCE(h.gider,0), 2) AS net_tl,
       round(sum(COALESCE(g.gelir,0) - COALESCE(h.gider,0))
             OVER (ORDER BY COALESCE(g.ay, h.ay)), 2) AS kumulatif_net_tl
FROM g FULL JOIN h ON g.ay = h.ay
"""),

("v_ekonomik_kod_gider", "Analitik butce ekonomik kod kirilimi ile gider dagilimi", """
SELECT e.year AS yil, ec.code AS ekonomik_kod, ec.name AS ekonomik_kod_adi,
       ec.sub_code AS alt_kod, ec.sub_name AS alt_kod_adi,
       round(sum(e.total_amount), 2) AS tutar_tl
FROM expense_transaction e JOIN economic_code ec ON ec.economic_code_id = e.economic_code_id
GROUP BY 1, 2, 3, 4, 5
"""),

("v_fonksiyonel_harcama", "Hizmet alani (fonksiyonel kod) bazinda harcama dagilimi", """
SELECT e.year AS yil, f.code AS fonksiyonel_kod, f.name AS hizmet_alani,
       round(sum(e.total_amount), 2) AS tutar_tl,
       round(100.0 * sum(e.total_amount) / sum(sum(e.total_amount)) OVER (PARTITION BY e.year), 2)
         AS pay_yuzde
FROM expense_transaction e JOIN functional_code f ON f.functional_code_id = e.functional_code_id
GROUP BY 1, 2, 3
"""),

("v_kisi_basi_harcama", "Yil bazinda kisi basina dusen belediye harcamasi ve geliri", """
WITH n AS (SELECT year AS yil, sum(population) AS nufus FROM population_stat GROUP BY 1),
     h AS (SELECT year AS yil, sum(total_amount) AS gider FROM expense_transaction GROUP BY 1),
     g AS (SELECT year AS yil, sum(amount) AS gelir FROM revenue_transaction GROUP BY 1)
SELECT n.yil, n.nufus,
       round(h.gider / n.nufus, 2) AS kisi_basi_gider_tl,
       round(g.gelir / n.nufus, 2) AS kisi_basi_gelir_tl
FROM n JOIN h ON h.yil = n.yil JOIN g ON g.yil = n.yil
"""),

("v_ihale_ozeti", "Yil, usul ve is turune gore ihale hacmi ve kirim orani", """
SELECT extract(year FROM tender_date)::int AS yil, procurement_type AS ihale_usulu,
       work_type AS is_turu, count(*) AS ihale_sayisi,
       round(sum(estimated_cost), 2) AS yaklasik_maliyet_tl,
       round(sum(winning_bid), 2) AS sozlesme_bedeli_tl,
       round(avg(discount_rate), 2) AS ortalama_kirim_yuzde,
       round(avg(bidder_count), 1) AS ortalama_istekli_sayisi
FROM tender GROUP BY 1, 2, 3
"""),

("v_tedarikci_hacmi", "Tedarikci bazinda toplam odeme ve sozlesme hacmi", """
SELECT s.supplier_id AS tedarikci_id, s.supplier_name AS tedarikci,
       s.category AS kategori, s.is_local AS ilce_icinde, s.blacklisted AS yasakli,
       count(DISTINCT c.contract_id) AS sozlesme_sayisi,
       round(COALESCE(sum(DISTINCT c.contract_amount), 0), 2) AS sozlesme_bedeli_tl,
       round(COALESCE((SELECT sum(p.gross_amount) FROM payment_order p
                       WHERE p.supplier_id = s.supplier_id), 0), 2) AS toplam_odeme_tl
FROM supplier s LEFT JOIN contract c ON c.supplier_id = s.supplier_id
GROUP BY 1, 2, 3, 4, 5
"""),

("v_odeme_vadesi", "Yil bazinda tedarikci odeme suresi performansi", """
SELECT extract(year FROM order_date)::int AS yil,
       count(*) AS odeme_emri_sayisi,
       round(avg(delay_days), 1) AS ortalama_odeme_gun,
       round(100.0 * count(*) FILTER (WHERE delay_days <= 30) / count(*), 2) AS otuz_gun_ici_oran,
       round(sum(gross_amount), 2) AS brut_tutar_tl,
       round(sum(net_amount), 2) AS net_odenen_tl,
       count(*) FILTER (WHERE status = 'Beklemede') AS bekleyen_odeme
FROM payment_order GROUP BY 1
"""),

("v_sozlesme_takibi", "Devam eden ve tamamlanan sozlesmelerin gerceklesme durumu", """
SELECT c.contract_id AS sozlesme_id, c.contract_no AS sozlesme_no, c.subject AS konu,
       s.supplier_name AS yuklenici, d.directorate_name AS mudurluk,
       c.start_date AS baslangic, c.end_date AS bitis,
       round(c.contract_amount, 2) AS bedel_tl,
       round(c.price_increase_amount, 2) AS is_artisi_tl,
       round(c.paid_to_date, 2) AS odenen_tl,
       c.completion_rate AS gerceklesme_yuzde, c.status AS durum,
       CASE WHEN c.status = 'Devam ediyor' AND c.end_date < CURRENT_DATE THEN true ELSE false END
         AS suresi_gecmis
FROM contract c
JOIN supplier s ON s.supplier_id = c.supplier_id
LEFT JOIN directorate d ON d.directorate_id = c.directorate_id
"""),

# ===================================================== PERSONEL
("v_personel_mevcudu", "Mudurluk ve istihdam turune gore aktif personel mevcudu", """
SELECT d.directorate_name AS mudurluk, d.service_group AS hizmet_grubu,
       e.employment_type AS istihdam_turu,
       count(*) AS personel_sayisi,
       count(*) FILTER (WHERE e.gender = 'K') AS kadin_sayisi,
       round(100.0 * count(*) FILTER (WHERE e.gender = 'K') / count(*), 2) AS kadin_orani,
       round(avg(extract(year FROM age(CURRENT_DATE, e.birth_date))), 1) AS ortalama_yas,
       round(avg(extract(year FROM age(CURRENT_DATE, e.hire_date))), 1) AS ortalama_kidem_yil,
       d.headcount_budget AS norm_kadro
FROM employee e JOIN directorate d ON d.directorate_id = e.directorate_id
WHERE e.status <> 'Ayrıldı'
GROUP BY 1, 2, 3, d.headcount_budget
"""),

("v_personel_gideri", "Yil ve mudurluk bazinda personel maliyeti kalemleri", """
SELECT p.year AS yil, d.directorate_name AS mudurluk,
       count(DISTINCT p.employee_id) AS personel_sayisi,
       round(sum(p.gross_pay), 2) AS brut_ucret_tl,
       round(sum(p.overtime_pay), 2) AS fazla_mesai_tl,
       round(sum(p.bonus), 2) AS ikramiye_tl,
       round(sum(p.social_security_employer), 2) AS sgk_isveren_tl,
       round(sum(p.net_pay), 2) AS net_odenen_tl,
       round(sum(p.employer_cost), 2) AS toplam_isveren_maliyeti_tl
FROM payroll p JOIN directorate d ON d.directorate_id = p.directorate_id
GROUP BY 1, 2
"""),

("v_aylik_bordro_ozeti", "Aylik bordro toplamlari ve ortalama net ucret", """
SELECT period_month AS ay, employment_type AS istihdam_turu,
       count(*) AS bordro_sayisi,
       round(sum(gross_pay), 2) AS brut_toplam_tl,
       round(sum(income_tax + stamp_tax + social_security_employee
                 + union_due + other_deductions), 2) AS kesinti_toplam_tl,
       round(sum(net_pay), 2) AS net_toplam_tl,
       round(avg(net_pay), 2) AS ortalama_net_ucret_tl,
       round(sum(employer_cost), 2) AS isveren_maliyeti_tl
FROM payroll GROUP BY 1, 2
"""),

("v_personel_devir_hizi", "Yil bazinda ise giris, ayrilis ve devir hizi", """
WITH g AS (SELECT extract(year FROM hire_date)::int AS yil, count(*) AS giren FROM employee GROUP BY 1),
     a AS (SELECT extract(year FROM termination_date)::int AS yil, count(*) AS ayrilan
           FROM employee WHERE termination_date IS NOT NULL GROUP BY 1),
     m AS (SELECT year AS yil, count(DISTINCT employee_id) AS mevcut FROM payroll GROUP BY 1)
SELECT m.yil, m.mevcut AS ortalama_mevcut, COALESCE(g.giren,0) AS ise_giren,
       COALESCE(a.ayrilan,0) AS ayrilan,
       round(100.0 * COALESCE(a.ayrilan,0) / NULLIF(m.mevcut,0), 2) AS devir_hizi_yuzde
FROM m LEFT JOIN g ON g.yil = m.yil LEFT JOIN a ON a.yil = m.yil
"""),

("v_ayrilis_nedenleri", "Ayrilis nedenlerinin yil bazinda dagilimi", """
SELECT extract(year FROM termination_date)::int AS yil,
       termination_reason AS ayrilis_nedeni, count(*) AS kisi_sayisi
FROM employee WHERE termination_date IS NOT NULL GROUP BY 1, 2
"""),

("v_izin_devamsizlik", "Yil ve izin turune gore kullanilan izin gunleri", """
SELECT extract(year FROM l.start_date)::int AS yil, l.leave_type AS izin_turu,
       count(*) AS izin_sayisi, sum(l.day_count) AS toplam_gun,
       round(avg(l.day_count), 1) AS ortalama_gun
FROM leave_record l WHERE l.status = 'Onaylandı' GROUP BY 1, 2
"""),

("v_fazla_mesai", "Yil, mudurluk ve gerekceye gore fazla mesai yuku", """
SELECT extract(year FROM o.work_date)::int AS yil, d.directorate_name AS mudurluk,
       o.reason AS gerekce, count(*) AS mesai_kaydi,
       round(sum(o.hours), 1) AS toplam_saat, round(sum(o.amount), 2) AS toplam_tutar_tl
FROM overtime_record o JOIN directorate d ON d.directorate_id = o.directorate_id
GROUP BY 1, 2, 3
"""),

("v_egitim_ozeti", "Yil ve kategoriye gore hizmet ici egitim faaliyetleri", """
SELECT extract(year FROM training_date)::int AS yil, training_category AS kategori,
       count(*) AS egitim_katilim, count(DISTINCT employee_id) AS egitilen_personel,
       sum(hours) AS toplam_saat, round(sum(cost_amount), 2) AS toplam_maliyet_tl,
       round(avg(exam_score), 1) AS ortalama_sinav_puani
FROM training_record GROUP BY 1, 2
"""),

# ===================================================== IMAR VE ZABITA
("v_imar_basvuru_performansi", "Yil ve basvuru turune gore imar basvurulari ve sure", """
SELECT extract(year FROM application_date)::int AS yil, application_type AS basvuru_turu,
       count(*) AS basvuru_sayisi,
       count(*) FILTER (WHERE status = 'Onaylandı') AS onaylanan,
       count(*) FILTER (WHERE status = 'Reddedildi') AS reddedilen,
       round(100.0 * count(*) FILTER (WHERE status = 'Onaylandı') / count(*), 2) AS onay_orani,
       round(avg(processing_days), 1) AS ortalama_sure_gun,
       round(sum(fee_amount), 2) AS toplam_harc_tl
FROM zoning_application GROUP BY 1, 2
"""),

("v_yapi_ruhsat_ozeti", "Yil ve mahalle bazinda verilen yapi ruhsatlari", """
SELECT extract(year FROM p.issue_date)::int AS yil, n.neighborhood_name AS mahalle,
       count(*) AS ruhsat_sayisi, sum(p.unit_count) AS bagimsiz_bolum,
       round(sum(p.construction_area_m2), 2) AS insaat_alani_m2,
       round(sum(p.estimated_cost), 2) AS yatirim_tutari_tl,
       round(sum(p.permit_fee), 2) AS harc_geliri_tl
FROM building_permit p JOIN neighborhood n ON n.neighborhood_id = p.neighborhood_id
GROUP BY 1, 2
"""),

("v_zabita_faaliyeti", "Yil, mahalle ve islem turune gore zabita faaliyeti", """
SELECT extract(year FROM a.action_date)::int AS yil, n.neighborhood_name AS mahalle,
       a.action_type AS islem_turu, count(*) AS islem_sayisi,
       count(*) FILTER (WHERE a.result = 'İdari para cezası') AS ceza_kesilen,
       round(avg(a.response_minutes), 1) AS ortalama_mudahale_dk
FROM municipal_police_action a JOIN neighborhood n ON n.neighborhood_id = a.neighborhood_id
GROUP BY 1, 2, 3
"""),

("v_idari_para_cezalari", "Yil ve dayanaga gore idari para cezasi ve tahsilat orani", """
SELECT extract(year FROM decision_date)::int AS yil, legal_basis AS dayanak,
       count(*) AS ceza_sayisi,
       round(sum(penalty_amount), 2) AS kesilen_tutar_tl,
       round(sum(collected_amount), 2) AS tahsil_edilen_tl,
       round(100.0 * sum(collected_amount) / NULLIF(sum(penalty_amount),0), 2) AS tahsilat_orani,
       count(*) FILTER (WHERE status = 'İtiraz edildi') AS itiraz_sayisi
FROM penalty_decision GROUP BY 1, 2
"""),

# ===================================================== ALTYAPI VE FILO
("v_altyapi_ariza_performansi", "Ariza turu ve oncelige gore cozum suresi performansi", """
SELECT extract(year FROM f.report_date)::int AS yil, f.fault_type AS ariza_turu,
       f.severity AS oncelik, count(*) AS ariza_sayisi,
       count(*) FILTER (WHERE f.status = 'Çözüldü') AS cozulen,
       round(avg(f.resolution_hours), 2) AS ortalama_cozum_saati,
       round(percentile_cont(0.9) WITHIN GROUP (ORDER BY f.resolution_hours)::numeric, 2)
         AS p90_cozum_saati,
       round(sum(f.cost_amount), 2) AS toplam_maliyet_tl
FROM infrastructure_fault f GROUP BY 1, 2, 3
"""),

("v_yol_calismalari", "Yil, mahalle ve calisma turune gore yol yatirimlari", """
SELECT extract(year FROM r.start_date)::int AS yil, n.neighborhood_name AS mahalle,
       r.work_type AS calisma_turu, count(*) AS calisma_sayisi,
       round(sum(r.area_m2), 2) AS toplam_alan_m2,
       round(sum(r.asphalt_ton), 2) AS asfalt_ton,
       round(sum(r.cost_amount), 2) AS maliyet_tl
FROM road_work r JOIN neighborhood n ON n.neighborhood_id = r.neighborhood_id
GROUP BY 1, 2, 3
"""),

("v_park_yesil_alan", "Mahalle bazinda park envanteri ve kisi basi yesil alan", """
WITH n2026 AS (SELECT neighborhood_id, sum(population) AS nufus
               FROM population_stat WHERE year = 2026 GROUP BY 1)
SELECT n.neighborhood_name AS mahalle, count(p.park_id) AS park_sayisi,
       round(sum(p.area_m2), 2) AS toplam_park_alani_m2,
       sum(p.playground_count) AS oyun_grubu,
       sum(p.tree_count) AS agac_sayisi,
       round(sum(p.area_m2) / NULLIF(nn.nufus,0), 2) AS kisi_basi_park_m2,
       round(avg(p.accessibility_score), 1) AS erisilebilirlik_puani,
       round(sum(p.annual_maintenance_cost), 2) AS yillik_bakim_maliyeti_tl
FROM neighborhood n
LEFT JOIN park p ON p.neighborhood_id = n.neighborhood_id
LEFT JOIN n2026 nn ON nn.neighborhood_id = n.neighborhood_id
GROUP BY 1, nn.nufus
"""),

("v_aydinlatma_envanteri", "Mahalle ve armatur tipine gore aydinlatma envanteri ve enerji", """
SELECT n.neighborhood_name AS mahalle, s.lamp_type AS armatur_tipi,
       count(*) AS direk_sayisi,
       count(*) FILTER (WHERE s.status = 'Arızalı') AS arizali,
       round(sum(s.annual_kwh), 2) AS yillik_tuketim_kwh,
       round(avg(s.power_watt), 1) AS ortalama_guc_watt
FROM street_light s JOIN neighborhood n ON n.neighborhood_id = s.neighborhood_id
GROUP BY 1, 2
"""),

("v_filo_maliyeti", "Arac sinifi bazinda yakit, bakim ve kiralama maliyetleri", """
SELECT v.vehicle_class AS arac_sinifi, count(DISTINCT v.vehicle_id) AS arac_sayisi,
       round(COALESCE(sum(f.tutar), 0), 2) AS yakit_maliyeti_tl,
       round(COALESCE(sum(f.litre), 0), 2) AS toplam_litre,
       round(COALESCE(sum(m.bakim), 0), 2) AS bakim_maliyeti_tl,
       round(COALESCE(sum(f.tutar), 0) + COALESCE(sum(m.bakim), 0), 2) AS toplam_maliyet_tl
FROM vehicle v
LEFT JOIN (SELECT vehicle_id, sum(amount) AS tutar, sum(liters) AS litre
           FROM fuel_log GROUP BY 1) f ON f.vehicle_id = v.vehicle_id
LEFT JOIN (SELECT vehicle_id, sum(total_cost) AS bakim
           FROM vehicle_maintenance GROUP BY 1) m ON m.vehicle_id = v.vehicle_id
GROUP BY 1
"""),

("v_yillik_yakit_tuketimi", "Yil ve mudurluk bazinda akaryakit tuketimi", """
SELECT extract(year FROM f.fill_date)::int AS yil, d.directorate_name AS mudurluk,
       round(sum(f.liters), 2) AS litre, round(sum(f.amount), 2) AS tutar_tl,
       round(avg(f.unit_price), 3) AS ortalama_litre_fiyati
FROM fuel_log f JOIN vehicle v ON v.vehicle_id = f.vehicle_id
JOIN directorate d ON d.directorate_id = v.directorate_id
GROUP BY 1, 2
"""),

("v_tesis_enerji", "Tesis bazinda yillik enerji ve su tuketimi ile maliyeti", """
SELECT extract(year FROM u.period_month)::int AS yil, f.facility_name AS tesis,
       f.facility_type AS tesis_turu,
       round(sum(u.electricity_kwh), 2) AS elektrik_kwh,
       round(sum(u.gas_m3), 2) AS dogalgaz_m3,
       round(sum(u.water_m3), 2) AS su_m3,
       round(sum(u.solar_generation_kwh), 2) AS ges_uretimi_kwh,
       round(sum(u.electricity_cost + u.gas_cost + u.water_cost), 2) AS toplam_maliyet_tl
FROM facility_energy_usage u
JOIN municipal_facility f ON f.municipal_facility_id = u.municipal_facility_id
GROUP BY 1, 2, 3
"""),

# ===================================================== CEVRE VE TEMIZLIK
("v_atik_toplama_ozeti", "Ay ve mahalle bazinda toplanan atik miktari ve maliyeti", """
SELECT date_trunc('month', w.collection_date)::date AS ay, n.neighborhood_name AS mahalle,
       round(sum(w.total_ton), 2) AS toplam_atik_ton,
       round(sum(w.household_waste_ton), 2) AS evsel_atik_ton,
       round(sum(w.market_waste_ton), 2) AS pazar_atigi_ton,
       sum(w.trip_count) AS sefer_sayisi,
       round(sum(w.disposal_cost), 2) AS bertaraf_maliyeti_tl
FROM waste_collection w JOIN neighborhood n ON n.neighborhood_id = w.neighborhood_id
GROUP BY 1, 2
"""),

("v_kisi_basi_atik", "Yil ve mahalle bazinda kisi basi gunluk atik uretimi (kg)", """
WITH a AS (SELECT extract(year FROM collection_date)::int AS yil, neighborhood_id,
                  sum(total_ton) AS ton, count(DISTINCT collection_date) AS gun
           FROM waste_collection GROUP BY 1, 2),
     n AS (SELECT year AS yil, neighborhood_id, sum(population) AS nufus
           FROM population_stat GROUP BY 1, 2)
SELECT a.yil, nb.neighborhood_name AS mahalle, n.nufus,
       round(a.ton, 2) AS yillik_atik_ton,
       round(1000.0 * a.ton / NULLIF(n.nufus,0) / NULLIF(a.gun,0), 3) AS kisi_basi_gunluk_kg
FROM a JOIN n ON n.yil = a.yil AND n.neighborhood_id = a.neighborhood_id
JOIN neighborhood nb ON nb.neighborhood_id = a.neighborhood_id
"""),

("v_geri_donusum_performansi", "Yil ve mahalle bazinda geri donusum miktarlari ve orani", """
SELECT extract(year FROM r.period_month)::int AS yil, n.neighborhood_name AS mahalle,
       round(sum(r.paper_ton), 2) AS kagit_ton, round(sum(r.plastic_ton), 2) AS plastik_ton,
       round(sum(r.glass_ton), 2) AS cam_ton, round(sum(r.metal_ton), 2) AS metal_ton,
       round(sum(r.paper_ton + r.plastic_ton + r.glass_ton + r.metal_ton + r.organic_ton), 2)
         AS toplam_geri_kazanim_ton,
       round(avg(r.recycling_rate), 2) AS ortalama_geri_kazanim_orani,
       round(sum(r.revenue_amount), 2) AS geri_donusum_geliri_tl
FROM recycling_stat r JOIN neighborhood n ON n.neighborhood_id = r.neighborhood_id
GROUP BY 1, 2
"""),

("v_hava_kalitesi_aylik", "Istasyon ve ay bazinda hava kalitesi ortalamalari", """
SELECT date_trunc('month', measurement_date)::date AS ay, station_name AS istasyon,
       round(avg(pm10), 2) AS ortalama_pm10, round(avg(pm25), 2) AS ortalama_pm25,
       round(avg(no2), 2) AS ortalama_no2, round(avg(aqi), 1) AS ortalama_aki,
       count(*) FILTER (WHERE aqi > 100) AS hassas_ve_ustu_gun,
       round(avg(noise_db), 2) AS ortalama_gurultu_db
FROM air_quality_measurement GROUP BY 1, 2
"""),

# ===================================================== SOSYAL HIZMETLER
("v_sosyal_yardim_ozeti", "Yil, mahalle ve yardim turune gore basvuru ve onay", """
SELECT extract(year FROM s.application_date)::int AS yil, n.neighborhood_name AS mahalle,
       s.aid_type AS yardim_turu, count(*) AS basvuru_sayisi,
       count(*) FILTER (WHERE s.status = 'Onaylandı') AS onaylanan,
       round(100.0 * count(*) FILTER (WHERE s.status = 'Onaylandı') / count(*), 2) AS onay_orani,
       round(avg(s.processing_days), 1) AS ortalama_sure_gun,
       round(avg(s.household_income), 2) AS ortalama_hane_geliri_tl
FROM social_aid_application s JOIN neighborhood n ON n.neighborhood_id = s.neighborhood_id
GROUP BY 1, 2, 3
"""),

("v_yardim_odemeleri", "Yil ve yardim turune gore yapilan yardim odemeleri", """
SELECT extract(year FROM payment_date)::int AS yil, aid_type AS yardim_turu,
       payment_form AS odeme_sekli, count(*) AS odeme_sayisi,
       count(DISTINCT citizen_id) AS yararlanici_sayisi,
       round(sum(amount), 2) AS toplam_tutar_tl
FROM aid_payment GROUP BY 1, 2, 3
"""),

("v_yardim_yararlanici_yogunlugu", "Mahalle bazinda yardim alan hane orani", """
WITH y AS (SELECT neighborhood_id,
                  count(DISTINCT household_id) AS yararlanici_hane,
                  count(DISTINCT citizen_id) AS yararlanici_kisi
           FROM social_aid_application WHERE status = 'Onaylandı' GROUP BY 1),
     h AS (SELECT neighborhood_id, count(*) AS hane FROM household GROUP BY 1)
SELECT n.neighborhood_name AS mahalle, n.socioeconomic_segment AS segment,
       COALESCE(y.yararlanici_kisi,0) AS yardim_alan_kisi,
       COALESCE(y.yararlanici_hane,0) AS yardim_alan_hane, h.hane AS hane_sayisi,
       round(100.0 * COALESCE(y.yararlanici_hane,0) / NULLIF(h.hane,0), 2) AS yardim_yogunlugu_yuzde
FROM neighborhood n LEFT JOIN y ON y.neighborhood_id = n.neighborhood_id
LEFT JOIN h ON h.neighborhood_id = n.neighborhood_id
"""),

("v_asevi_performansi", "Ay bazinda asevi uretim ve maliyet performansi", """
SELECT date_trunc('month', service_date)::date AS ay,
       sum(meals_produced) AS uretilen_porsiyon,
       sum(meals_delivered_home) AS eve_teslim,
       round(avg(beneficiary_household_count), 1) AS ortalama_hane,
       round(sum(food_cost), 2) AS toplam_gida_maliyeti_tl,
       round(avg(cost_per_meal), 2) AS porsiyon_basi_maliyet_tl,
       bool_or(is_ramadan) AS ramazan_ayi
FROM soup_kitchen_daily GROUP BY 1
"""),

("v_saglik_hizmetleri", "Yil, birim ve hizmet turune gore poliklinik basvurulari", """
SELECT extract(year FROM v.visit_date)::int AS yil, h.center_name AS saglik_birimi,
       v.service_type AS hizmet_turu, count(*) AS basvuru_sayisi,
       count(DISTINCT v.citizen_id) AS tekil_hasta,
       round(avg(v.age_at_visit), 1) AS ortalama_yas,
       round(100.0 * count(*) FILTER (WHERE v.gender = 'K') / count(*), 2) AS kadin_orani,
       round(sum(v.service_cost), 2) AS toplam_maliyet_tl
FROM clinic_visit v JOIN health_center h ON h.health_center_id = v.health_center_id
GROUP BY 1, 2, 3
"""),

("v_veteriner_hizmetleri", "Yil ve islem turune gore sokak hayvani hizmetleri", """
SELECT extract(year FROM record_date)::int AS yil, animal_type AS hayvan_turu,
       procedure_type AS islem, count(*) AS islem_sayisi,
       count(*) FILTER (WHERE adopted) AS sahiplendirilen,
       round(avg(shelter_days), 1) AS ortalama_barinak_gun,
       round(sum(cost_amount), 2) AS toplam_maliyet_tl
FROM veterinary_record GROUP BY 1, 2, 3
"""),

# ===================================================== KULTUR VE SPOR
("v_etkinlik_ozeti", "Yil ve kategoriye gore etkinlik, katilim ve maliyet", """
SELECT extract(year FROM event_date)::int AS yil, event_category AS kategori,
       count(*) AS etkinlik_sayisi, sum(attendance) AS toplam_katilim,
       round(avg(100.0 * attendance / NULLIF(capacity,0)), 2) AS doluluk_orani,
       round(sum(cost_amount), 2) AS toplam_maliyet_tl,
       round(sum(revenue_amount), 2) AS bilet_geliri_tl,
       round(sum(cost_amount) / NULLIF(sum(attendance),0), 2) AS kisi_basi_maliyet_tl,
       round(avg(satisfaction_score), 2) AS memnuniyet_ort
FROM event GROUP BY 1, 2
"""),

("v_kutuphane_kullanimi", "Yil ve kutuphane bazinda odunc kitap istatistikleri", """
SELECT extract(year FROM b.loan_date)::int AS yil, l.library_name AS kutuphane,
       count(*) AS odunc_sayisi, count(DISTINCT b.citizen_id) AS tekil_uye,
       round(100.0 * count(*) FILTER (WHERE b.is_late) / count(*), 2) AS gec_iade_orani,
       round(avg(b.late_days) FILTER (WHERE b.is_late), 1) AS ortalama_gecikme_gun
FROM book_loan b JOIN library l ON l.library_id = b.library_id
GROUP BY 1, 2
"""),

("v_populer_kitap_turleri", "Kitap turune gore odunc alma sayilari", """
SELECT book_category AS tur, extract(year FROM loan_date)::int AS yil,
       count(*) AS odunc_sayisi,
       round(100.0 * count(*) / sum(count(*)) OVER (PARTITION BY extract(year FROM loan_date)::int), 2)
         AS pay_yuzde
FROM book_loan GROUP BY 1, 2
"""),

("v_spor_uyelikleri", "Yil, brans ve yas grubuna gore spor uyelikleri", """
SELECT extract(year FROM start_date)::int AS yil, branch AS brans, age_group AS yas_grubu,
       count(*) AS uyelik_sayisi,
       count(*) FILTER (WHERE gender = 'K') AS kadin_uye,
       round(100.0 * count(*) FILTER (WHERE is_discounted) / count(*), 2) AS indirimli_oran,
       round(avg(visit_count), 1) AS ortalama_giris_sayisi,
       round(sum(fee_amount), 2) AS toplam_gelir_tl
FROM sports_membership GROUP BY 1, 2, 3
"""),

# ===================================================== VATANDAS ILISKILERI
("v_basvuru_ozeti", "Yil, kategori ve kanala gore vatandas basvurulari", """
SELECT extract(year FROM s.created_date)::int AS yil, c.category_name AS kategori,
       s.channel AS kanal, count(*) AS basvuru_sayisi,
       count(*) FILTER (WHERE s.status = 'Çözüldü') AS cozulen,
       round(100.0 * count(*) FILTER (WHERE s.sla_met) / count(*), 2) AS sla_uyum_orani,
       round(avg(s.resolution_hours), 2) AS ortalama_cozum_saati,
       round(avg(s.satisfaction_score), 2) AS memnuniyet_ort
FROM service_request s
LEFT JOIN request_category c ON c.request_category_id = s.request_category_id
GROUP BY 1, 2, 3
"""),

("v_mudurluk_basvuru_performansi", "Mudurluk bazinda basvuru yuku ve cozum performansi", """
SELECT extract(year FROM s.created_date)::int AS yil, d.directorate_name AS mudurluk,
       count(*) AS basvuru_sayisi,
       count(*) FILTER (WHERE s.status = 'Çözüldü') AS cozulen,
       count(*) FILTER (WHERE s.status = 'İşlemde') AS acik_basvuru,
       round(avg(s.first_response_hours), 2) AS ilk_donus_saat,
       round(avg(s.resolution_hours), 2) AS ortalama_cozum_saat,
       round(percentile_cont(0.9) WITHIN GROUP (ORDER BY s.resolution_hours)::numeric, 2)
         AS p90_cozum_saat,
       round(100.0 * count(*) FILTER (WHERE s.sla_met) / count(*), 2) AS sla_uyum_orani
FROM service_request s JOIN directorate d ON d.directorate_id = s.assigned_directorate_id
GROUP BY 1, 2
"""),

("v_mahalle_basvuru_yogunlugu", "Mahalle bazinda 1000 kisi basina basvuru sayisi", """
WITH b AS (SELECT extract(year FROM created_date)::int AS yil, neighborhood_id, count(*) AS basvuru
           FROM service_request GROUP BY 1, 2),
     n AS (SELECT year AS yil, neighborhood_id, sum(population) AS nufus
           FROM population_stat GROUP BY 1, 2)
SELECT b.yil, nb.neighborhood_name AS mahalle, nb.socioeconomic_segment AS segment,
       b.basvuru, n.nufus,
       round(1000.0 * b.basvuru / NULLIF(n.nufus,0), 2) AS bin_kisi_basina_basvuru
FROM b JOIN n ON n.yil = b.yil AND n.neighborhood_id = b.neighborhood_id
JOIN neighborhood nb ON nb.neighborhood_id = b.neighborhood_id
"""),

("v_gunluk_basvuru_trendi", "Gunluk basvuru sayisi ve 7 gunluk hareketli ortalama", """
SELECT created_date AS gun, count(*) AS basvuru_sayisi,
       round(avg(count(*)) OVER (ORDER BY created_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 1)
         AS hareketli_ort_7gun
FROM service_request GROUP BY 1
"""),

("v_anket_memnuniyet", "Anket ve konu bazinda ortalama memnuniyet puanlari", """
SELECT s.survey_id, s.survey_name AS anket, extract(year FROM s.start_date)::int AS yil,
       q.question_topic AS konu, count(a.survey_answer_id) AS yanit_sayisi,
       round(avg(a.answer_value), 3) AS ortalama_puan,
       round(100.0 * count(*) FILTER (WHERE a.answer_value >= 4) / count(*), 2) AS memnun_orani,
       round(100.0 * count(*) FILTER (WHERE a.answer_value <= 2) / count(*), 2) AS memnuniyetsiz_orani
FROM survey s
JOIN survey_question q ON q.survey_id = s.survey_id
JOIN survey_answer a ON a.survey_question_id = q.survey_question_id
GROUP BY 1, 2, 3, 4
"""),

("v_anket_mahalle_karnesi", "Mahalle bazinda anket memnuniyet karnesi", """
SELECT extract(year FROM s.start_date)::int AS yil, n.neighborhood_name AS mahalle,
       n.socioeconomic_segment AS segment, q.question_topic AS konu,
       count(*) AS yanit_sayisi, round(avg(a.answer_value), 3) AS ortalama_puan
FROM survey_answer a
JOIN survey s ON s.survey_id = a.survey_id
JOIN survey_question q ON q.survey_question_id = a.survey_question_id
JOIN neighborhood n ON n.neighborhood_id = a.neighborhood_id
GROUP BY 1, 2, 3, 4
"""),

("v_anket_demografik_kirilim", "Yas ve egitim durumuna gore memnuniyet farklari", """
SELECT extract(year FROM s.start_date)::int AS yil, r.age_band AS yas_grubu,
       r.education_level AS ogrenim, r.gender AS cinsiyet,
       count(a.survey_answer_id) AS yanit_sayisi,
       round(avg(a.answer_value), 3) AS ortalama_puan
FROM survey_respondent r
JOIN survey s ON s.survey_id = r.survey_id
JOIN survey_answer a ON a.survey_respondent_id = r.survey_respondent_id
GROUP BY 1, 2, 3, 4
"""),

# ===================================================== YONETISIM VE DIGER
("v_meclis_kararlari", "Yil ve konuya gore meclis kararlari ve oylama sonuclari", """
SELECT extract(year FROM d.decision_date)::int AS yil, d.topic AS konu,
       count(*) AS karar_sayisi,
       count(*) FILTER (WHERE d.vote_result = 'Oybirliği') AS oybirligi,
       count(*) FILTER (WHERE d.vote_result = 'Reddedildi') AS reddedilen,
       round(avg(d.yes_votes), 1) AS ortalama_kabul_oyu,
       round(sum(d.financial_impact), 2) AS toplam_mali_etki_tl
FROM council_decision d GROUP BY 1, 2
"""),

("v_encumen_kararlari", "Yil ve konuya gore encumen kararlari", """
SELECT extract(year FROM decision_date)::int AS yil, topic AS konu,
       count(*) AS karar_sayisi,
       count(*) FILTER (WHERE result = 'Kabul') AS kabul,
       round(sum(financial_impact), 2) AS mali_etki_tl
FROM committee_decision GROUP BY 1, 2
"""),

("v_secim_sonuclari", "Mahalle bazinda secim sonuclari ve katilim", """
SELECT e.election_year AS secim_yili, e.election_type AS secim_turu,
       n.neighborhood_name AS mahalle, n.socioeconomic_segment AS segment,
       e.party_code AS secenek, e.vote_count AS oy, e.vote_share AS oy_orani,
       e.registered_voters AS secmen, e.turnout_rate AS katilim_orani
FROM election_result e JOIN neighborhood n ON n.neighborhood_id = e.neighborhood_id
"""),

("v_cenaze_hizmetleri", "Yil ve mezarlik bazinda defin hizmetleri", """
SELECT extract(year FROM burial_date)::int AS yil, cemetery_name AS mezarlik,
       count(*) AS defin_sayisi,
       count(*) FILTER (WHERE is_free_service) AS ucretsiz_hizmet,
       round(avg(age_at_death), 1) AS ortalama_yas,
       round(sum(cost_amount), 2) AS toplam_maliyet_tl,
       round(sum(fee_amount), 2) AS toplam_gelir_tl
FROM burial_record GROUP BY 1, 2
"""),

("v_otopark_gelirleri", "Yil ve otopark bazinda kullanim ve gelir", """
SELECT extract(year FROM t.entry_date)::int AS yil, p.lot_name AS otopark,
       p.lot_type AS otopark_turu, n.neighborhood_name AS mahalle,
       count(*) AS islem_sayisi,
       round(avg(t.duration_minutes), 1) AS ortalama_sure_dk,
       round(sum(t.amount), 2) AS gelir_tl,
       round(100.0 * count(*) FILTER (WHERE t.is_subscriber) / count(*), 2) AS abone_orani
FROM parking_transaction t
JOIN parking_lot p ON p.parking_lot_id = t.parking_lot_id
JOIN neighborhood n ON n.neighborhood_id = p.neighborhood_id
GROUP BY 1, 2, 3, 4
"""),

("v_acil_durum_mudahale", "Yil, olay turu ve mahalleye gore acil durum mudahaleleri", """
SELECT extract(year FROM e.call_date)::int AS yil, n.neighborhood_name AS mahalle,
       e.event_type AS olay_turu, count(*) AS cagri_sayisi,
       round(avg(e.response_minutes), 1) AS ortalama_varis_dk,
       sum(e.affected_person_count) AS etkilenen_kisi,
       round(sum(e.damage_estimate), 2) AS tahmini_hasar_tl,
       round(sum(e.response_cost), 2) AS mudahale_maliyeti_tl
FROM emergency_call e JOIN neighborhood n ON n.neighborhood_id = e.neighborhood_id
GROUP BY 1, 2, 3
"""),

# ===================================================== BASKANLIK PANOSU
("v_baskanlik_panosu", "Yil bazinda kurumsal performans ozeti (tek bakista karne)", """
WITH n AS (SELECT year AS yil, sum(population) AS nufus FROM population_stat GROUP BY 1),
     g AS (SELECT year AS yil, sum(amount) AS gelir FROM revenue_transaction GROUP BY 1),
     h AS (SELECT year AS yil, sum(total_amount) AS gider FROM expense_transaction GROUP BY 1),
     p AS (SELECT year AS yil, count(DISTINCT employee_id) AS personel,
                  sum(employer_cost) AS personel_maliyeti FROM payroll GROUP BY 1),
     b AS (SELECT extract(year FROM created_date)::int AS yil, count(*) AS basvuru,
                  avg(resolution_hours) AS cozum_saat,
                  100.0 * count(*) FILTER (WHERE sla_met) / count(*) AS sla
           FROM service_request GROUP BY 1),
     a AS (SELECT extract(year FROM collection_date)::int AS yil, sum(total_ton) AS atik
           FROM waste_collection GROUP BY 1),
     s AS (SELECT extract(year FROM application_date)::int AS yil, count(*) AS yardim_basvuru
           FROM social_aid_application GROUP BY 1),
     m AS (SELECT extract(year FROM start_date)::int AS yil, round(avg(overall_satisfaction), 2) AS memnuniyet
           FROM survey GROUP BY 1)
SELECT n.yil, n.nufus,
       round(g.gelir, 2) AS gelir_tl, round(h.gider, 2) AS gider_tl,
       round(g.gelir - h.gider, 2) AS denge_tl,
       p.personel AS personel_sayisi,
       round(100.0 * p.personel_maliyeti / NULLIF(h.gider,0), 2) AS personel_gideri_pay_yuzde,
       b.basvuru AS vatandas_basvurusu,
       round(b.cozum_saat::numeric, 1) AS ortalama_cozum_saat,
       round(b.sla::numeric, 2) AS sla_uyum_orani,
       round(a.atik, 1) AS toplanan_atik_ton,
       s.yardim_basvuru AS sosyal_yardim_basvurusu,
       m.memnuniyet AS anket_memnuniyet_ort
FROM n
LEFT JOIN g ON g.yil = n.yil LEFT JOIN h ON h.yil = n.yil
LEFT JOIN p ON p.yil = n.yil LEFT JOIN b ON b.yil = n.yil
LEFT JOIN a ON a.yil = n.yil LEFT JOIN s ON s.yil = n.yil
LEFT JOIN m ON m.yil = n.yil
"""),
]


def views_sql():
    parcalar = ["-- Turkce isimli analitik view'lar", ""]
    for ad, aciklama, sql in VIEWS:
        parcalar.append(f"CREATE OR REPLACE VIEW {ad} AS\n{sql.strip()};")
        parcalar.append(f"COMMENT ON VIEW {ad} IS '{aciklama}';")
        parcalar.append("")
    return "\n".join(parcalar)
