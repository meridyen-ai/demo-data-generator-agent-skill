"""Talaşlı imalat veritabanı için analiz görünümleri.

Tüm para birimi kolonları TRY tabanlıdır (`*_base`). EUR ve USD karşılıkları ya
belgenin kendi `*_eur` / `*_usd` kolonundan ya da `fx_rates` üzerinden kurulan
aylık ortalama kur tablosundan (`fxm`) hesaplanır; böylece aynı rapor üç para
biriminde de tutarlı okunur.

Gelir tablosu mantığı:
  * SMM (620) yalnızca DİREKT maliyettir: hammadde + direkt işçilik + fason +
    kesici takım (`sales_order_lines.line_cogs_base`).
  * Üretim genel giderleri, pazarlama-satış-dağıtım, genel yönetim, Ar-Ge,
    finansman ve vergi `expenses` tablosundadır ve `source` ile ayrışır.
  * `brut_kar` direkt katkıyı, `brut_kar_tam_yukleme` ise üretim genel
    giderleri de düşülmüş tam yükleme brüt kârını verir. İki kalem birbirini
    kapsamaz; hiçbir maliyet iki kez sayılmaz.
"""
from __future__ import annotations

FXM = """
fxm AS (
    SELECT date_trunc('month', rate_date)::date AS month,
           avg(rate_per_base) FILTER (WHERE currency_code = 'EUR') AS eur_per_try,
           avg(rate_per_base) FILTER (WHERE currency_code = 'USD') AS usd_per_try
    FROM fx_rates GROUP BY 1
)"""

OPEX_SRC = "('purchased','payroll','depreciation','logistics')"


def build_views(selected: set, today: str) -> str:
    v = []

    # ===================================================== kur ve para birimi ==
    v.append("""
CREATE VIEW v_fx_daily AS
SELECT rate_date,
       max(base_per_unit) FILTER (WHERE currency_code = 'EUR') AS try_per_eur,
       max(base_per_unit) FILTER (WHERE currency_code = 'USD') AS try_per_usd,
       max(base_per_unit) FILTER (WHERE currency_code = 'GBP') AS try_per_gbp
FROM fx_rates GROUP BY 1 ORDER BY 1;""")

    v.append("""
CREATE VIEW v_fx_monthly AS
SELECT date_trunc('month', rate_date)::date AS ay,
       round(avg(base_per_unit) FILTER (WHERE currency_code = 'EUR'), 4) AS ort_eur_try,
       round(avg(base_per_unit) FILTER (WHERE currency_code = 'USD'), 4) AS ort_usd_try,
       round(min(base_per_unit) FILTER (WHERE currency_code = 'EUR'), 4) AS min_eur_try,
       round(max(base_per_unit) FILTER (WHERE currency_code = 'EUR'), 4) AS max_eur_try
FROM fx_rates GROUP BY 1 ORDER BY 1;""")

    # ================================================================= satış ==
    v.append("""
CREATE VIEW v_monthly_sales AS
SELECT date_trunc('month', o.order_date)::date       AS ay,
       count(DISTINCT o.id)                          AS siparis_adedi,
       count(DISTINCT o.customer_id)                 AS aktif_musteri,
       sum(l.qty)                                    AS uretilen_adet,
       sum(l.line_subtotal_base)                     AS ciro_try,
       sum(l.line_subtotal_eur)                      AS ciro_eur,
       sum(l.line_subtotal_usd)                      AS ciro_usd,
       sum(l.line_cogs_base)                         AS direkt_smm_try,
       sum(l.line_margin_base)                       AS brut_kar_try,
       sum(l.line_margin_eur)                        AS brut_kar_eur,
       round(100 * sum(l.line_margin_base) / NULLIF(sum(l.line_subtotal_base), 0), 2)
                                                     AS brut_kar_marj_pct
FROM sales_orders o
JOIN sales_order_lines l ON l.order_id = o.id
WHERE o.status <> 'İptal'
GROUP BY 1 ORDER BY 1;""")

    v.append("""
CREATE VIEW v_yearly_sales AS
SELECT extract(year FROM o.order_date)::int AS yil,
       count(DISTINCT o.id)                 AS siparis_adedi,
       count(DISTINCT o.customer_id)        AS aktif_musteri,
       count(DISTINCT l.product_id)         AS satilan_parca_cesidi,
       sum(l.qty)                           AS uretilen_adet,
       sum(l.line_subtotal_base)            AS ciro_try,
       sum(l.line_subtotal_eur)             AS ciro_eur,
       sum(l.line_subtotal_usd)             AS ciro_usd,
       sum(l.line_cogs_base)                AS direkt_smm_try,
       sum(l.line_margin_base)              AS brut_kar_try,
       round(100 * sum(l.line_margin_base) / NULLIF(sum(l.line_subtotal_base), 0), 2)
                                            AS brut_kar_marj_pct,
       round(sum(l.line_subtotal_base) / NULLIF(count(DISTINCT o.id), 0), 2)
                                            AS ortalama_siparis_tutari_try
FROM sales_orders o
JOIN sales_order_lines l ON l.order_id = o.id
WHERE o.status <> 'İptal'
GROUP BY 1 ORDER BY 1;""")

    v.append("""
CREATE VIEW v_revenue_by_currency AS
SELECT extract(year FROM o.order_date)::int AS yil, o.currency AS belge_para_birimi,
       count(DISTINCT o.id)                 AS siparis_adedi,
       sum(l.line_subtotal)                 AS ciro_belge_para_birimi,
       sum(l.line_subtotal_base)            AS ciro_try,
       sum(l.line_subtotal_eur)             AS ciro_eur,
       sum(l.line_subtotal_usd)             AS ciro_usd,
       round(100 * sum(l.line_subtotal_base) / NULLIF(sum(sum(l.line_subtotal_base))
             OVER (PARTITION BY extract(year FROM o.order_date)::int), 0), 2) AS pay_pct
FROM sales_orders o
JOIN sales_order_lines l ON l.order_id = o.id
WHERE o.status <> 'İptal'
GROUP BY 1, 2 ORDER BY 1, ciro_try DESC;""")

    v.append("""
CREATE VIEW v_customer_revenue AS
SELECT c.id AS musteri_id, c.name AS musteri, c.segment, c.abc_class AS abc_sinifi,
       c.country AS ulke, c.country_code AS ulke_kodu, c.region AS bolge,
       c.industry AS sektor, c.currency AS para_birimi, c.is_export AS ihracat_mi,
       c.payment_terms_days AS vade_gun, c.ppm_target AS ppm_hedefi,
       count(DISTINCT o.id)                        AS siparis_adedi,
       coalesce(sum(l.qty), 0)                     AS toplam_adet,
       coalesce(sum(l.line_subtotal_base), 0)      AS ciro_try,
       coalesce(sum(l.line_subtotal_eur), 0)       AS ciro_eur,
       coalesce(sum(l.line_subtotal_usd), 0)       AS ciro_usd,
       coalesce(sum(l.line_cogs_base), 0)          AS direkt_smm_try,
       coalesce(sum(l.line_margin_base), 0)        AS brut_kar_try,
       round(100 * sum(l.line_margin_base) / NULLIF(sum(l.line_subtotal_base), 0), 2)
                                                   AS brut_kar_marj_pct,
       min(o.order_date)                           AS ilk_siparis,
       max(o.order_date)                           AS son_siparis
FROM customers c
LEFT JOIN sales_orders o ON o.customer_id = c.id AND o.status <> 'İptal'
LEFT JOIN sales_order_lines l ON l.order_id = o.id
GROUP BY 1,2,3,4,5,6,7,8,9,10,11,12 ORDER BY ciro_try DESC NULLS LAST;""")

    v.append("""
CREATE VIEW v_country_performance AS
SELECT c.country AS ulke, c.country_code AS ulke_kodu, c.region AS bolge,
       CASE WHEN NOT c.is_export THEN 'Yurt İçi'
            WHEN c.is_intra_eu   THEN 'AB / Gümrük Birliği İhracatı'
            ELSE 'Üçüncü Ülke İhracatı' END        AS ticaret_tipi,
       count(DISTINCT c.id)                        AS musteri_adedi,
       count(DISTINCT o.id)                        AS siparis_adedi,
       sum(l.qty)                                  AS toplam_adet,
       sum(l.line_subtotal_base)                   AS ciro_try,
       sum(l.line_subtotal_eur)                    AS ciro_eur,
       sum(l.line_margin_base)                     AS brut_kar_try,
       round(100 * sum(l.line_margin_base) / NULLIF(sum(l.line_subtotal_base), 0), 2)
                                                   AS brut_kar_marj_pct
FROM customers c
JOIN sales_orders o ON o.customer_id = c.id AND o.status <> 'İptal'
JOIN sales_order_lines l ON l.order_id = o.id
GROUP BY 1,2,3,4 ORDER BY ciro_try DESC;""")

    v.append("""
CREATE VIEW v_export_vs_domestic AS
SELECT extract(year FROM o.order_date)::int AS yil,
       CASE WHEN o.is_export THEN 'İhracat' ELSE 'Yurt İçi' END AS pazar,
       count(DISTINCT o.id)      AS siparis_adedi,
       count(DISTINCT o.customer_id) AS musteri_adedi,
       sum(l.qty)                AS toplam_adet,
       sum(l.line_subtotal_base) AS ciro_try,
       sum(l.line_subtotal_eur)  AS ciro_eur,
       sum(l.line_subtotal_usd)  AS ciro_usd,
       sum(l.line_margin_base)   AS brut_kar_try,
       round(100 * sum(l.line_margin_base) / NULLIF(sum(l.line_subtotal_base), 0), 2)
                                 AS brut_kar_marj_pct
FROM sales_orders o JOIN sales_order_lines l ON l.order_id = o.id
WHERE o.status <> 'İptal'
GROUP BY 1,2 ORDER BY 1,2;""")

    v.append("""
CREATE VIEW v_product_profitability AS
SELECT p.id AS parca_id, p.sku AS parca_kodu, p.name AS parca_adi, p.category AS kategori,
       p.subcategory AS alt_kategori, p.material_grade AS malzeme_kalitesi,
       p.surface_treatment AS yuzey_islem, p.is_safety_part AS emniyet_parcasi,
       c.name AS musteri, p.program_name AS proje,
       p.list_price AS liste_fiyati_try, p.list_price_eur AS liste_fiyati_eur,
       p.unit_cost AS direkt_birim_maliyet_try, p.std_cost_total AS tam_birim_maliyet_try,
       sum(l.qty)                AS satilan_adet,
       sum(l.line_subtotal_base) AS ciro_try,
       sum(l.line_subtotal_eur)  AS ciro_eur,
       sum(l.line_cogs_base)     AS direkt_smm_try,
       sum(l.line_margin_base)   AS brut_kar_try,
       round(100 * sum(l.line_margin_base) / NULLIF(sum(l.line_subtotal_base), 0), 2)
                                 AS brut_kar_marj_pct
FROM products p
JOIN sales_order_lines l ON l.product_id = p.id
JOIN sales_orders o ON o.id = l.order_id AND o.status <> 'İptal'
LEFT JOIN customers c ON c.id = p.customer_id
GROUP BY 1,2,3,4,5,6,7,8,9,10,11,12,13,14 ORDER BY brut_kar_try DESC;""")

    v.append("""
CREATE VIEW v_product_category_performance AS
SELECT extract(year FROM o.order_date)::int AS yil, p.category AS kategori,
       count(DISTINCT p.id)      AS parca_cesidi,
       sum(l.qty)                AS satilan_adet,
       sum(l.line_subtotal_base) AS ciro_try,
       sum(l.line_subtotal_eur)  AS ciro_eur,
       sum(l.line_cogs_base)     AS direkt_smm_try,
       sum(l.line_margin_base)   AS brut_kar_try,
       round(100 * sum(l.line_margin_base) / NULLIF(sum(l.line_subtotal_base), 0), 2)
                                 AS brut_kar_marj_pct
FROM products p
JOIN sales_order_lines l ON l.product_id = p.id
JOIN sales_orders o ON o.id = l.order_id AND o.status <> 'İptal'
GROUP BY 1,2 ORDER BY 1, ciro_try DESC;""")

    v.append("""
CREATE VIEW v_salesperson_performance AS
SELECT e.id AS personel_id, e.full_name AS satis_personeli, e.role AS unvan,
       extract(year FROM o.order_date)::int AS yil,
       count(DISTINCT o.id)         AS siparis_adedi,
       count(DISTINCT o.customer_id) AS musteri_adedi,
       sum(l.line_subtotal_base)    AS ciro_try,
       sum(l.line_subtotal_eur)     AS ciro_eur,
       sum(l.line_margin_base)      AS brut_kar_try,
       round(100 * sum(l.line_margin_base) / NULLIF(sum(l.line_subtotal_base), 0), 2)
                                    AS brut_kar_marj_pct
FROM employees e
JOIN sales_orders o ON o.salesperson_id = e.id AND o.status <> 'İptal'
JOIN sales_order_lines l ON l.order_id = o.id
GROUP BY 1,2,3,4 ORDER BY yil DESC, ciro_try DESC;""")

    v.append("""
CREATE VIEW v_channel_performance AS
SELECT extract(year FROM o.order_date)::int AS yil, o.channel AS satis_kanali,
       o.order_source AS siparis_kaynagi,
       count(DISTINCT o.id)      AS siparis_adedi,
       sum(l.line_subtotal_base) AS ciro_try,
       sum(l.line_subtotal_eur)  AS ciro_eur,
       sum(l.line_margin_base)   AS brut_kar_try
FROM sales_orders o JOIN sales_order_lines l ON l.order_id = o.id
WHERE o.status <> 'İptal'
GROUP BY 1,2,3 ORDER BY 1, ciro_try DESC;""")

    v.append("""
CREATE VIEW v_order_fulfillment AS
SELECT date_trunc('month', o.order_date)::date AS ay,
       CASE WHEN o.is_export THEN 'İhracat' ELSE 'Yurt İçi' END AS pazar,
       count(*)                                          AS siparis_adedi,
       count(*) FILTER (WHERE o.is_on_time)              AS zamaninda_adedi,
       round(100.0 * count(*) FILTER (WHERE o.is_on_time) / NULLIF(count(*), 0), 2)
                                                         AS otd_pct,
       round(avg(o.delay_days), 2)                       AS ortalama_gecikme_gun,
       max(o.delay_days)                                 AS max_gecikme_gun
FROM sales_orders o
WHERE o.status <> 'İptal'
GROUP BY 1, 2 ORDER BY 1, 2;""")

    v.append("""
CREATE VIEW v_price_list_current AS
SELECT p.sku AS parca_kodu, p.name AS parca_adi, p.category AS kategori,
       c.name AS musteri, pl.valid_from AS gecerlilik_baslangic,
       pl.valid_to AS gecerlilik_bitis, pl.price_try, pl.price_eur, pl.price_usd,
       pl.min_qty AS asgari_adet, pl.agreement_no AS anlasma_no, pl.price_type AS fiyat_tipi
FROM price_list pl
JOIN products p ON p.id = pl.product_id
LEFT JOIN customers c ON c.id = pl.customer_id
ORDER BY p.sku, pl.valid_from;""")

    return _part2(v, selected, today)


def _part2(v, selected, today):
    # ========================================================= gelir tablosu ==
    v.append(f"""
CREATE VIEW v_pnl_monthly AS
WITH {FXM},
spine AS (
    SELECT generate_series(date_trunc('month', (SELECT min(order_date) FROM sales_orders)),
                           date_trunc('month', DATE '{today}'), interval '1 month')::date AS ay
),
gelir AS (
    SELECT date_trunc('month', o.order_date)::date AS ay,
           sum(l.line_subtotal_base) AS ciro,
           sum(l.line_cogs_base)     AS direkt_smm,
           sum(CASE WHEN o.is_export THEN l.line_subtotal_base ELSE 0 END) AS ihracat_ciro,
           sum(CASE WHEN NOT o.is_export THEN l.line_subtotal_base ELSE 0 END) AS yurtici_ciro,
           sum(l.qty) AS satilan_adet
    FROM sales_orders o JOIN sales_order_lines l ON l.order_id = o.id
    WHERE o.status <> 'İptal' GROUP BY 1
),
iade AS (
    SELECT date_trunc('month', return_date)::date AS ay,
           sum(refund_amount_base) AS iadeler
    FROM returns WHERE status <> 'Reddedildi' GROUP BY 1
),
gider AS (
    SELECT date_trunc('month', e.expense_date)::date AS ay,
           sum(CASE WHEN ec.expense_group = 'Üretim Genel Giderleri'
                    THEN e.amount_base ELSE 0 END) AS uretim_genel_gideri,
           sum(CASE WHEN ec.expense_group = 'Pazarlama Satış ve Dağıtım Giderleri'
                    THEN e.amount_base ELSE 0 END) AS pazarlama_satis_dagitim,
           sum(CASE WHEN ec.expense_group = 'Genel Yönetim Giderleri'
                    THEN e.amount_base ELSE 0 END) AS genel_yonetim,
           sum(CASE WHEN ec.expense_group = 'Araştırma ve Geliştirme Giderleri'
                    THEN e.amount_base ELSE 0 END) AS ar_ge,
           sum(CASE WHEN ec.expense_group = 'Finansman Giderleri'
                    THEN e.amount_base ELSE 0 END) AS finansman_gideri,
           sum(CASE WHEN e.source = 'tax' THEN e.amount_base ELSE 0 END) AS kurumlar_vergisi,
           sum(CASE WHEN ec.expense_group = 'Vergi ve Yasal Yükümlülükler'
                     AND e.source <> 'tax' THEN e.amount_base ELSE 0 END) AS diger_vergiler,
           sum(CASE WHEN e.source = 'payroll' THEN e.amount_base ELSE 0 END) AS personel_gideri,
           sum(CASE WHEN e.source = 'depreciation' THEN e.amount_base ELSE 0 END) AS amortisman,
           sum(CASE WHEN e.source = 'logistics' THEN e.amount_base ELSE 0 END) AS lojistik_gideri,
           sum(CASE WHEN e.source = 'purchased' THEN e.amount_base ELSE 0 END) AS satin_alinan_gider,
           -- faaliyet gideri GRUP bazında toplanır: kaynak (source) bazında
           -- toplansaydı 'purchased' kaynaklı banka komisyonu ve diğer vergiler
           -- hem faaliyet giderine hem finansman/vergi satırına girip iki kez sayılırdı
           sum(CASE WHEN ec.expense_group IN ('Üretim Genel Giderleri',
                                              'Pazarlama Satış ve Dağıtım Giderleri',
                                              'Genel Yönetim Giderleri',
                                              'Araştırma ve Geliştirme Giderleri')
                    THEN e.amount_base ELSE 0 END) AS faaliyet_giderleri
    FROM expenses e JOIN expense_categories ec ON ec.id = e.category_id
    GROUP BY 1
),
kur AS (
    SELECT date_trunc('month', payment_date)::date AS ay,
           sum(fx_gain_loss) AS kambiyo_kar_zarar
    FROM payments GROUP BY 1
),
isci AS (
    SELECT date_trunc('month', period_date)::date AS ay,
           sum(employer_cost) AS toplam_bordro_maliyeti
    FROM payroll_items GROUP BY 1
)
SELECT s.ay,
       extract(year FROM s.ay)::int                              AS yil,
       coalesce(g.ciro, 0)                                       AS ciro_try,
       coalesce(g.yurtici_ciro, 0)                               AS yurtici_ciro_try,
       coalesce(g.ihracat_ciro, 0)                               AS ihracat_ciro_try,
       coalesce(g.satilan_adet, 0)                               AS satilan_adet,
       coalesce(i.iadeler, 0)                                    AS satistan_iadeler_try,
       coalesce(g.ciro, 0) - coalesce(i.iadeler, 0)               AS net_satislar_try,
       coalesce(g.direkt_smm, 0)                                 AS direkt_smm_try,
       coalesce(g.ciro, 0) - coalesce(i.iadeler, 0)
           - coalesce(g.direkt_smm, 0)                           AS brut_kar_try,
       coalesce(x.uretim_genel_gideri, 0)                        AS uretim_genel_gideri_try,
       coalesce(g.ciro, 0) - coalesce(i.iadeler, 0) - coalesce(g.direkt_smm, 0)
           - coalesce(x.uretim_genel_gideri, 0)                  AS brut_kar_tam_yukleme_try,
       coalesce(x.pazarlama_satis_dagitim, 0)                    AS pazarlama_satis_dagitim_try,
       coalesce(x.genel_yonetim, 0)                              AS genel_yonetim_try,
       coalesce(x.ar_ge, 0)                                      AS ar_ge_try,
       coalesce(x.personel_gideri, 0)                            AS personel_gideri_try,
       coalesce(x.amortisman, 0)                                 AS amortisman_try,
       coalesce(x.lojistik_gideri, 0)                            AS lojistik_gideri_try,
       coalesce(x.satin_alinan_gider, 0)                         AS satin_alinan_gider_try,
       coalesce(x.faaliyet_giderleri, 0)                         AS faaliyet_giderleri_try,
       coalesce(g.ciro, 0) - coalesce(i.iadeler, 0) - coalesce(g.direkt_smm, 0)
           - coalesce(x.faaliyet_giderleri, 0)                   AS faaliyet_kari_try,
       coalesce(k.kambiyo_kar_zarar, 0)                          AS kambiyo_kar_zarar_try,
       coalesce(x.finansman_gideri, 0)                           AS finansman_gideri_try,
       coalesce(x.diger_vergiler, 0)                             AS diger_vergi_resim_harc_try,
       coalesce(g.ciro, 0) - coalesce(i.iadeler, 0) - coalesce(g.direkt_smm, 0)
           - coalesce(x.faaliyet_giderleri, 0) - coalesce(x.finansman_gideri, 0)
           - coalesce(x.diger_vergiler, 0)
           + coalesce(k.kambiyo_kar_zarar, 0)                    AS vergi_oncesi_kar_try,
       coalesce(x.kurumlar_vergisi, 0)                           AS kurumlar_vergisi_try,
       coalesce(g.ciro, 0) - coalesce(i.iadeler, 0) - coalesce(g.direkt_smm, 0)
           - coalesce(x.faaliyet_giderleri, 0) - coalesce(x.finansman_gideri, 0)
           - coalesce(x.diger_vergiler, 0) + coalesce(k.kambiyo_kar_zarar, 0)
           - coalesce(x.kurumlar_vergisi, 0)                     AS net_kar_try,
       coalesce(w.toplam_bordro_maliyeti, 0)                     AS toplam_bordro_maliyeti_try,
       f.eur_per_try, f.usd_per_try,
       round(coalesce(g.ciro, 0) * f.eur_per_try, 2)             AS ciro_eur,
       round(coalesce(g.ciro, 0) * f.usd_per_try, 2)             AS ciro_usd,
       round((coalesce(g.ciro, 0) - coalesce(i.iadeler, 0)) * f.eur_per_try, 2)
                                                                 AS net_satislar_eur,
       round((coalesce(g.ciro, 0) - coalesce(i.iadeler, 0)) * f.usd_per_try, 2)
                                                                 AS net_satislar_usd,
       round(coalesce(g.direkt_smm, 0) * f.eur_per_try, 2)       AS direkt_smm_eur,
       round((coalesce(g.ciro, 0) - coalesce(i.iadeler, 0) - coalesce(g.direkt_smm, 0))
             * f.eur_per_try, 2)                                 AS brut_kar_eur,
       round((coalesce(g.ciro, 0) - coalesce(i.iadeler, 0) - coalesce(g.direkt_smm, 0)
              - coalesce(x.faaliyet_giderleri, 0)) * f.eur_per_try, 2) AS faaliyet_kari_eur,
       round((coalesce(g.ciro, 0) - coalesce(i.iadeler, 0) - coalesce(g.direkt_smm, 0)
              - coalesce(x.faaliyet_giderleri, 0)) * f.usd_per_try, 2) AS faaliyet_kari_usd,
       round((coalesce(g.ciro, 0) - coalesce(i.iadeler, 0) - coalesce(g.direkt_smm, 0)
              - coalesce(x.faaliyet_giderleri, 0) - coalesce(x.finansman_gideri, 0)
              - coalesce(x.diger_vergiler, 0) + coalesce(k.kambiyo_kar_zarar, 0)
              - coalesce(x.kurumlar_vergisi, 0)) * f.eur_per_try, 2) AS net_kar_eur,
       round((coalesce(g.ciro, 0) - coalesce(i.iadeler, 0) - coalesce(g.direkt_smm, 0)
              - coalesce(x.faaliyet_giderleri, 0) - coalesce(x.finansman_gideri, 0)
              - coalesce(x.diger_vergiler, 0) + coalesce(k.kambiyo_kar_zarar, 0)
              - coalesce(x.kurumlar_vergisi, 0)) * f.usd_per_try, 2) AS net_kar_usd
FROM spine s
LEFT JOIN gelir g ON g.ay = s.ay
LEFT JOIN iade  i ON i.ay = s.ay
LEFT JOIN gider x ON x.ay = s.ay
LEFT JOIN kur   k ON k.ay = s.ay
LEFT JOIN isci  w ON w.ay = s.ay
LEFT JOIN fxm   f ON f.month = s.ay
ORDER BY 1;""")

    v.append("""
CREATE VIEW v_pnl_yearly AS
SELECT yil,
       sum(ciro_try) AS ciro_try, sum(ciro_eur) AS ciro_eur, sum(ciro_usd) AS ciro_usd,
       sum(yurtici_ciro_try) AS yurtici_ciro_try, sum(ihracat_ciro_try) AS ihracat_ciro_try,
       sum(satilan_adet) AS satilan_adet,
       sum(satistan_iadeler_try) AS satistan_iadeler_try,
       sum(net_satislar_try) AS net_satislar_try, sum(net_satislar_eur) AS net_satislar_eur,
       sum(net_satislar_usd) AS net_satislar_usd,
       sum(direkt_smm_try) AS direkt_smm_try, sum(direkt_smm_eur) AS direkt_smm_eur,
       sum(brut_kar_try) AS brut_kar_try, sum(brut_kar_eur) AS brut_kar_eur,
       round(100 * sum(brut_kar_try) / NULLIF(sum(net_satislar_try), 0), 2) AS brut_kar_marj_pct,
       sum(uretim_genel_gideri_try) AS uretim_genel_gideri_try,
       sum(brut_kar_tam_yukleme_try) AS brut_kar_tam_yukleme_try,
       round(100 * sum(brut_kar_tam_yukleme_try) / NULLIF(sum(net_satislar_try), 0), 2)
                                     AS brut_kar_tam_yukleme_marj_pct,
       sum(pazarlama_satis_dagitim_try) AS pazarlama_satis_dagitim_try,
       sum(genel_yonetim_try) AS genel_yonetim_try, sum(ar_ge_try) AS ar_ge_try,
       sum(personel_gideri_try) AS personel_gideri_try,
       sum(amortisman_try) AS amortisman_try, sum(lojistik_gideri_try) AS lojistik_gideri_try,
       sum(satin_alinan_gider_try) AS satin_alinan_gider_try,
       sum(faaliyet_giderleri_try) AS faaliyet_giderleri_try,
       sum(faaliyet_kari_try) AS faaliyet_kari_try, sum(faaliyet_kari_eur) AS faaliyet_kari_eur,
       sum(faaliyet_kari_usd) AS faaliyet_kari_usd,
       round(100 * sum(faaliyet_kari_try) / NULLIF(sum(net_satislar_try), 0), 2)
                                     AS faaliyet_kari_marj_pct,
       sum(kambiyo_kar_zarar_try) AS kambiyo_kar_zarar_try,
       sum(finansman_gideri_try) AS finansman_gideri_try,
       sum(diger_vergi_resim_harc_try) AS diger_vergi_resim_harc_try,
       sum(vergi_oncesi_kar_try) AS vergi_oncesi_kar_try,
       sum(kurumlar_vergisi_try) AS kurumlar_vergisi_try,
       sum(net_kar_try) AS net_kar_try, sum(net_kar_eur) AS net_kar_eur,
       sum(net_kar_usd) AS net_kar_usd,
       round(100 * sum(net_kar_try) / NULLIF(sum(net_satislar_try), 0), 2) AS net_kar_marj_pct,
       sum(toplam_bordro_maliyeti_try) AS toplam_bordro_maliyeti_try
FROM v_pnl_monthly GROUP BY 1 ORDER BY 1;""")

    v.append("""
CREATE VIEW v_opex_by_category AS
SELECT date_trunc('month', e.expense_date)::date AS ay,
       e.period_year AS yil, ec.expense_group AS gider_grubu, ec.code AS kategori_kodu,
       ec.name AS kategori, ec.account_code AS hesap_kodu, e.source AS kaynak,
       count(*) AS kayit_adedi,
       sum(e.amount_base) AS tutar_try, sum(e.amount_eur) AS tutar_eur,
       sum(e.amount_usd) AS tutar_usd
FROM expenses e JOIN expense_categories ec ON ec.id = e.category_id
GROUP BY 1,2,3,4,5,6,7 ORDER BY 1, tutar_try DESC;""")

    v.append("""
CREATE VIEW v_opex_by_department AS
SELECT e.period_year AS yil, d.name AS departman, d.cost_center AS masraf_merkezi,
       ec.expense_group AS gider_grubu,
       sum(e.amount_base) AS tutar_try, sum(e.amount_eur) AS tutar_eur
FROM expenses e
JOIN expense_categories ec ON ec.id = e.category_id
LEFT JOIN departments d ON d.id = e.department_id
GROUP BY 1,2,3,4 ORDER BY 1, tutar_try DESC;""")

    v.append("""
CREATE VIEW v_budget_vs_actual AS
SELECT b.fiscal_year AS mali_yil, b.period_month AS ay_no, d.name AS departman,
       ec.name AS kategori, ec.expense_group AS gider_grubu,
       sum(b.budget_amount)                                 AS butce_try,
       coalesce(sum(a.gerceklesen), 0)                      AS gerceklesen_try,
       coalesce(sum(a.gerceklesen), 0) - sum(b.budget_amount) AS sapma_try,
       round(100 * (coalesce(sum(a.gerceklesen), 0) - sum(b.budget_amount))
             / NULLIF(sum(b.budget_amount), 0), 2)          AS sapma_pct
FROM budgets b
JOIN expense_categories ec ON ec.id = b.expense_category_id
LEFT JOIN departments d ON d.id = b.department_id
LEFT JOIN (SELECT period_year, period_month, department_id, category_id,
                  sum(amount_base) AS gerceklesen
           FROM expenses GROUP BY 1,2,3,4) a
       ON a.period_year = b.fiscal_year AND a.period_month = b.period_month
      AND a.category_id = b.expense_category_id
      AND a.department_id IS NOT DISTINCT FROM b.department_id
GROUP BY 1,2,3,4,5 ORDER BY 1,2, butce_try DESC;""")

    v.append(f"""
CREATE VIEW v_ar_aging AS
SELECT i.id AS fatura_id, i.invoice_no AS fatura_no, i.invoice_date AS fatura_tarihi,
       i.due_date AS vade_tarihi, c.name AS musteri, c.country AS ulke,
       c.region AS bolge, i.currency AS para_birimi, i.total AS tutar_belge_pb,
       i.total_base AS tutar_try, i.balance AS bakiye_belge_pb,
       i.balance_base AS bakiye_try, i.balance_eur AS bakiye_eur,
       i.balance_usd AS bakiye_usd, i.days_overdue AS gecikme_gun,
       CASE WHEN i.balance <= 0 THEN 'Tahsil Edildi'
            WHEN i.due_date >= DATE '{today}' THEN 'Vadesi Gelmemiş'
            WHEN i.due_date >= DATE '{today}' - 30 THEN '1-30 Gün'
            WHEN i.due_date >= DATE '{today}' - 60 THEN '31-60 Gün'
            WHEN i.due_date >= DATE '{today}' - 90 THEN '61-90 Gün'
            ELSE '90+ Gün' END AS yaslandirma
FROM invoices i JOIN customers c ON c.id = i.customer_id
WHERE i.balance > 0;""")

    v.append(f"""
CREATE VIEW v_ap_aging AS
SELECT vb.id AS fatura_id, vb.bill_no AS fatura_no, vb.bill_date AS fatura_tarihi,
       vb.due_date AS vade_tarihi, vn.name AS tedarikci, vn.vendor_type AS tedarikci_tipi,
       vb.spend_category AS harcama_kategorisi, vb.currency AS para_birimi,
       vb.total AS tutar_belge_pb, vb.total_base AS tutar_try,
       vb.balance AS bakiye_belge_pb, vb.balance_base AS bakiye_try, vb.status AS durum,
       CASE WHEN vb.balance <= 0 THEN 'Ödendi'
            WHEN vb.due_date >= DATE '{today}' THEN 'Vadesi Gelmemiş'
            WHEN vb.due_date >= DATE '{today}' - 30 THEN '1-30 Gün'
            WHEN vb.due_date >= DATE '{today}' - 60 THEN '31-60 Gün'
            ELSE '60+ Gün' END AS yaslandirma
FROM vendor_invoices vb JOIN vendors vn ON vn.id = vb.vendor_id
WHERE vb.balance > 0;""")

    v.append("""
CREATE VIEW v_cash_flow_monthly AS
SELECT date_trunc('month', txn_date)::date AS ay, category AS kategori, direction AS yon,
       count(*) AS islem_adedi,
       sum(CASE WHEN direction = 'Giriş' THEN amount_base ELSE -amount_base END) AS net_nakit_try,
       sum(CASE WHEN direction = 'Giriş' THEN amount_eur ELSE -amount_eur END) AS net_nakit_eur,
       min(balance_after) AS ay_ici_min_bakiye, max(balance_after) AS ay_ici_max_bakiye
FROM bank_transactions GROUP BY 1,2,3 ORDER BY 1,2;""")

    v.append("""
CREATE VIEW v_trial_balance AS
SELECT g.period_year AS yil, g.account_code AS hesap_kodu,
       coa.account_name AS hesap_adi, coa.account_type AS hesap_tipi,
       coa.pnl_section AS gelir_tablosu_bolumu,
       sum(g.debit_base) AS borc_try, sum(g.credit_base) AS alacak_try,
       sum(g.debit_base) - sum(g.credit_base) AS bakiye_try
FROM gl_entries g
JOIN chart_of_accounts coa ON coa.account_code = g.account_code
GROUP BY 1,2,3,4,5 ORDER BY 1,2;""")

    v.append("""
CREATE VIEW v_fx_exposure AS
SELECT extract(year FROM i.invoice_date)::int AS yil, i.currency AS para_birimi,
       count(*)                AS fatura_adedi,
       sum(i.total)            AS fatura_tutari_belge_pb,
       sum(i.total_base)       AS fatura_tutari_try,
       sum(i.balance)          AS acik_bakiye_belge_pb,
       sum(i.balance_base)     AS acik_bakiye_try,
       round(avg(i.fx_rate), 6) AS ortalama_kur
FROM invoices i GROUP BY 1,2 ORDER BY 1,2;""")

    v.append("""
CREATE VIEW v_collection_performance AS
SELECT date_trunc('month', p.payment_date)::date AS ay, p.method AS odeme_yontemi,
       p.currency AS para_birimi,
       count(*)                  AS tahsilat_adedi,
       sum(p.amount_base)        AS tahsilat_try,
       sum(p.amount_eur)         AS tahsilat_eur,
       sum(p.fx_gain_loss)       AS kambiyo_kar_zarar_try,
       round(avg(p.days_to_pay), 1) AS ortalama_tahsilat_gunu
FROM payments p GROUP BY 1,2,3 ORDER BY 1, tahsilat_try DESC;""")

    return _part3(v, selected, today)


def _part3(v, selected, today):
    # ================================================================ üretim ==
    v.append("""
CREATE VIEW v_production_summary AS
SELECT date_trunc('month', w.actual_start)::date AS ay,
       count(*)                       AS is_emri_adedi,
       sum(w.planned_qty)             AS planlanan_adet,
       sum(w.produced_qty)            AS uretilen_adet,
       sum(w.good_qty)                AS saglam_adet,
       sum(w.scrap_qty)               AS hurda_adet,
       sum(w.rework_qty)              AS yeniden_isleme_adet,
       round(100 * sum(w.scrap_qty) / NULLIF(sum(w.planned_qty), 0), 3) AS hurda_orani_pct,
       round(100 * sum(w.produced_qty) / NULLIF(sum(w.planned_qty), 0), 2) AS verim_pct,
       sum(w.material_cost)           AS malzeme_maliyeti_try,
       sum(w.labor_cost)              AS iscilik_maliyeti_try,
       sum(w.machine_cost)            AS tezgah_maliyeti_try,
       sum(w.tooling_cost)            AS kesici_takim_maliyeti_try,
       sum(w.subcontract_cost)        AS fason_maliyeti_try,
       sum(w.overhead_cost)           AS genel_uretim_gideri_try,
       sum(w.total_cost)              AS toplam_maliyet_try,
       sum(w.total_cost_eur)          AS toplam_maliyet_eur,
       sum(w.std_total_cost)          AS standart_maliyet_try,
       sum(w.cost_variance)           AS maliyet_sapmasi_try,
       sum(w.setup_minutes_total)     AS kurulum_dakika,
       sum(w.run_minutes_total)       AS isleme_dakika,
       sum(w.downtime_minutes_total)  AS durus_dakika,
       count(*) FILTER (WHERE w.is_on_time) AS zamaninda_is_emri,
       round(100.0 * count(*) FILTER (WHERE w.is_on_time) / NULLIF(count(*), 0), 2)
                                      AS is_emri_otd_pct
FROM production_orders w
WHERE w.status <> 'İptal'
GROUP BY 1 ORDER BY 1;""")

    v.append("""
CREATE VIEW v_work_order_cost AS
SELECT w.id AS is_emri_id, w.wo_no AS is_emri_no, w.status AS durum, w.priority AS oncelik,
       p.sku AS parca_kodu, p.name AS parca_adi, p.category AS kategori,
       c.name AS musteri, w.lot_no AS parti_no, w.shift AS vardiya,
       pl.full_name AS planlamaci, sp.full_name AS vardiya_amiri,
       w.planned_start AS planlanan_baslangic, w.planned_end AS planlanan_bitis,
       w.actual_start AS fiili_baslangic, w.actual_end AS fiili_bitis,
       w.delay_days AS gecikme_gun, w.is_on_time AS zamaninda_mi,
       w.planned_qty AS planlanan_adet, w.produced_qty AS uretilen_adet,
       w.good_qty AS saglam_adet, w.scrap_qty AS hurda_adet, w.rework_qty AS yeniden_isleme,
       w.yield_pct AS verim_pct, w.scrap_pct AS hurda_orani_pct,
       w.material_cost AS malzeme_try, w.labor_cost AS iscilik_try,
       w.machine_cost AS tezgah_try, w.tooling_cost AS kesici_takim_try,
       w.subcontract_cost AS fason_try, w.overhead_cost AS genel_uretim_gideri_try,
       w.total_cost AS toplam_maliyet_try, w.total_cost_eur AS toplam_maliyet_eur,
       w.unit_cost AS birim_maliyet_try, w.std_total_cost AS standart_maliyet_try,
       w.cost_variance AS maliyet_sapmasi_try,
       w.setup_minutes_total AS kurulum_dk, w.run_minutes_total AS isleme_dk,
       w.downtime_minutes_total AS durus_dk, w.notes AS notlar
FROM production_orders w
JOIN products p ON p.id = w.product_id
LEFT JOIN customers c ON c.id = w.customer_id
LEFT JOIN employees pl ON pl.id = w.planner_id
LEFT JOIN employees sp ON sp.id = w.supervisor_id;""")

    v.append("""
CREATE VIEW v_operation_performance AS
SELECT date_trunc('month', po.op_date)::date AS ay, wc.code AS is_merkezi_kodu,
       wc.name AS is_merkezi, wc.process_family AS proses_ailesi,
       po.operation_name AS operasyon, po.shift AS vardiya,
       count(*)                        AS operasyon_adedi,
       sum(po.input_qty)               AS giren_adet,
       sum(po.good_qty)                AS saglam_adet,
       sum(po.scrap_qty)               AS hurda_adet,
       sum(po.rework_qty)              AS yeniden_isleme_adet,
       round(100 * sum(po.scrap_qty) / NULLIF(sum(po.input_qty), 0), 3) AS hurda_orani_pct,
       sum(po.setup_minutes_actual)    AS kurulum_dk,
       sum(po.run_minutes_actual)      AS isleme_dk,
       sum(po.run_minutes_std)         AS standart_isleme_dk,
       sum(po.downtime_minutes)        AS durus_dk,
       round(100 * sum(po.run_minutes_std) / NULLIF(sum(po.run_minutes_actual), 0), 2)
                                       AS verimlilik_pct,
       sum(po.labor_cost)              AS iscilik_try,
       sum(po.machine_cost)            AS tezgah_try,
       sum(po.tooling_cost)            AS kesici_takim_try,
       sum(po.total_cost)              AS toplam_maliyet_try
FROM production_operations po
JOIN work_centers wc ON wc.id = po.work_center_id
GROUP BY 1,2,3,4,5,6 ORDER BY 1, toplam_maliyet_try DESC;""")

    v.append("""
CREATE VIEW v_oee_by_work_center AS
WITH t AS (
  SELECT date_trunc('month', po.op_date)::date AS ay, po.work_center_id,
         sum(po.setup_minutes_actual + po.run_minutes_actual) AS calisma_dk,
         sum(po.downtime_minutes)     AS durus_dk,
         sum(po.run_minutes_std)      AS standart_dk,
         sum(po.run_minutes_actual)   AS fiili_isleme_dk,
         sum(po.input_qty)            AS giren_adet,
         sum(po.good_qty)             AS saglam_adet
  FROM production_operations po GROUP BY 1,2
)
SELECT t.ay, wc.code AS is_merkezi_kodu, wc.name AS is_merkezi,
       wc.machine_count AS tezgah_adedi, wc.shift_count AS vardiya_sayisi,
       wc.target_oee_pct AS oee_hedefi_pct,
       round(t.calisma_dk / 60.0, 2) AS calisma_saati,
       round(t.durus_dk / 60.0, 2)   AS durus_saati,
       round(100 * t.calisma_dk / NULLIF(t.calisma_dk + t.durus_dk, 0), 2) AS kullanilabilirlik_pct,
       round(100 * t.standart_dk / NULLIF(t.fiili_isleme_dk, 0), 2)        AS performans_pct,
       round(100 * t.saglam_adet / NULLIF(t.giren_adet, 0), 2)             AS kalite_pct,
       round(100 * (t.calisma_dk / NULLIF(t.calisma_dk + t.durus_dk, 0))
               * (t.standart_dk / NULLIF(t.fiili_isleme_dk, 0))
               * (t.saglam_adet / NULLIF(t.giren_adet, 0)), 2)             AS oee_pct
FROM t JOIN work_centers wc ON wc.id = t.work_center_id
ORDER BY t.ay, wc.code;""")

    v.append("""
CREATE VIEW v_machine_utilization AS
SELECT m.id AS tezgah_id, m.code AS tezgah_kodu, m.name AS tezgah,
       m.machine_type AS tezgah_tipi, m.manufacturer AS marka, m.model,
       m.control_system AS kontrol_unitesi, m.year_installed AS kurulum_yili,
       m.status AS durum, wc.name AS is_merkezi,
       extract(year FROM po.op_date)::int AS yil,
       count(*)                          AS operasyon_adedi,
       round(sum(po.setup_minutes_actual + po.run_minutes_actual) / 60.0, 2) AS calisma_saati,
       round(sum(po.downtime_minutes) / 60.0, 2) AS durus_saati,
       sum(po.good_qty)                  AS uretilen_saglam_adet,
       sum(po.scrap_qty)                 AS hurda_adet,
       sum(po.total_cost)                AS operasyon_maliyeti_try,
       round(100 * sum(po.setup_minutes_actual + po.run_minutes_actual)
             / NULLIF(sum(po.setup_minutes_actual + po.run_minutes_actual
                          + po.downtime_minutes), 0), 2) AS kullanilabilirlik_pct
FROM machines m
JOIN work_centers wc ON wc.id = m.work_center_id
LEFT JOIN production_operations po ON po.machine_id = m.id
GROUP BY 1,2,3,4,5,6,7,8,9,10,11 ORDER BY yil DESC, calisma_saati DESC;""")

    v.append("""
CREATE VIEW v_downtime_analysis AS
SELECT date_trunc('month', po.op_date)::date AS ay, wc.name AS is_merkezi,
       po.downtime_reason AS durus_nedeni, po.shift AS vardiya,
       count(*) AS olay_adedi,
       round(sum(po.downtime_minutes) / 60.0, 2) AS toplam_durus_saati,
       round(avg(po.downtime_minutes), 2)        AS ortalama_durus_dk
FROM production_operations po
JOIN work_centers wc ON wc.id = po.work_center_id
WHERE po.downtime_minutes > 0 AND po.downtime_reason IS NOT NULL
GROUP BY 1,2,3,4 ORDER BY 1, toplam_durus_saati DESC;""")

    v.append("""
CREATE VIEW v_routing_standard_cost AS
SELECT p.sku AS parca_kodu, p.name AS parca_adi, r.operation_no AS operasyon_no,
       r.operation_name AS operasyon, r.operation_type AS operasyon_tipi,
       wc.name AS is_merkezi, m.name AS tezgah,
       r.setup_minutes AS kurulum_dk, r.cycle_time_sec AS cevrim_saniye,
       r.pieces_per_hour AS saatte_adet, r.std_labor_rate AS iscilik_saat_ucreti_try,
       r.std_machine_rate AS tezgah_saat_ucreti_try,
       r.tooling_cost_per_part AS parca_basi_takim_try,
       r.is_subcontract AS fason_mu, vn.name AS fason_tedarikci,
       r.subcontract_unit_price AS fason_birim_fiyat_eur, r.scrap_pct AS hurda_orani_pct
FROM routings r
JOIN products p ON p.id = r.product_id
LEFT JOIN work_centers wc ON wc.id = r.work_center_id
LEFT JOIN machines m ON m.id = r.machine_id
LEFT JOIN vendors vn ON vn.id = r.subcontract_vendor_id
ORDER BY p.sku, r.operation_no;""")

    v.append("""
CREATE VIEW v_subcontract_performance AS
SELECT date_trunc('month', s.sent_date)::date AS ay, vn.name AS tedarikci,
       s.process_type AS proses,
       count(*)                    AS sevk_adedi,
       sum(s.qty_sent)             AS gonderilen_adet,
       sum(coalesce(s.qty_received, 0)) AS gelen_adet,
       sum(coalesce(s.qty_scrapped, 0)) AS hurda_adet,
       sum(s.total_cost_base)      AS maliyet_try,
       round(avg(s.lead_days), 1)  AS ortalama_temin_gunu,
       round(avg(s.planned_lead_days), 1) AS planlanan_temin_gunu,
       round(100.0 * count(*) FILTER (WHERE s.is_on_time) /
             NULLIF(count(*) FILTER (WHERE s.is_on_time IS NOT NULL), 0), 2) AS zamaninda_pct
FROM subcontract_operations s JOIN vendors vn ON vn.id = s.vendor_id
GROUP BY 1,2,3 ORDER BY 1, maliyet_try DESC;""")

    v.append("""
CREATE VIEW v_material_consumption AS
SELECT date_trunc('month', pc.issue_date)::date AS ay, rm.code AS hammadde_kodu,
       rm.name AS hammadde, rm.category AS kategori, rm.material_grade AS malzeme_kalitesi,
       rm.uom AS birim,
       count(DISTINCT pc.production_order_id) AS is_emri_adedi,
       sum(pc.planned_qty)   AS planlanan_miktar,
       sum(pc.consumed_qty)  AS tuketilen_miktar,
       sum(pc.variance_qty)  AS sapma_miktar,
       sum(pc.total_cost)    AS maliyet_try,
       round(avg(pc.unit_cost), 4) AS ortalama_birim_maliyet_try
FROM production_consumption pc
JOIN raw_materials rm ON rm.id = pc.raw_material_id
GROUP BY 1,2,3,4,5,6 ORDER BY 1, maliyet_try DESC;""")

    v.append("""
CREATE VIEW v_capacity_by_work_center AS
SELECT extract(year FROM po.op_date)::int AS yil, wc.code AS is_merkezi_kodu,
       wc.name AS is_merkezi, wc.machine_count AS tezgah_adedi,
       wc.shift_count AS vardiya_sayisi, wc.area_sqm AS alan_m2,
       round(sum(po.setup_minutes_actual + po.run_minutes_actual + po.downtime_minutes)
             / 60.0, 1) AS yuklenen_saat,
       round(wc.machine_count * wc.shift_count * 7.5 * 25.5 * 12, 1) AS teorik_kapasite_saat,
       round(100 * sum(po.setup_minutes_actual + po.run_minutes_actual + po.downtime_minutes)
             / 60.0 / NULLIF(wc.machine_count * wc.shift_count * 7.5 * 25.5 * 12, 0), 2)
             AS kapasite_kullanim_pct
FROM work_centers wc
JOIN production_operations po ON po.work_center_id = wc.id
GROUP BY 1,2,3,4,5,6 ORDER BY 1, kapasite_kullanim_pct DESC;""")

    # ================================================================ kalite ==
    v.append("""
CREATE VIEW v_quality_summary AS
SELECT date_trunc('month', qi.inspection_date)::date AS ay,
       qi.inspection_type AS kontrol_tipi, qi.result AS sonuc,
       count(*)                  AS kontrol_adedi,
       sum(qi.inspected_qty)     AS kontrol_edilen_adet,
       sum(qi.defect_qty)        AS hatali_adet,
       round(1e6 * sum(qi.defect_qty) / NULLIF(sum(qi.inspected_qty), 0), 1) AS ppm,
       round(avg(qi.cpk), 3)     AS ortalama_cpk
FROM quality_inspections qi
GROUP BY 1,2,3 ORDER BY 1,2,3;""")

    v.append("""
CREATE VIEW v_ppm_by_customer AS
SELECT extract(year FROM n.ncr_date)::int AS yil, c.name AS musteri,
       c.country AS ulke, c.ppm_target AS ppm_hedefi,
       count(*)                 AS sikayet_adedi,
       sum(n.qty_affected)      AS etkilenen_adet,
       sum(n.total_cost)        AS kalite_maliyeti_try,
       count(*) FILTER (WHERE n.is_8d) AS sekiz_d_adedi,
       round(avg(n.days_to_close), 1)  AS ortalama_kapanma_gunu
FROM nonconformances n JOIN customers c ON c.id = n.customer_id
WHERE n.is_customer_complaint
GROUP BY 1,2,3,4 ORDER BY 1, kalite_maliyeti_try DESC;""")

    v.append("""
CREATE VIEW v_nonconformance_cost AS
SELECT date_trunc('month', n.ncr_date)::date AS ay, n.source AS kaynak,
       n.defect_code AS hata_kodu, n.defect_description AS hata_aciklamasi,
       n.root_cause_category AS kok_neden_kategorisi, n.disposition AS karar,
       n.severity AS onem_derecesi, n.capa_status AS duzeltici_faaliyet_durumu,
       count(*)               AS ncr_adedi,
       sum(n.qty_affected)    AS etkilenen_adet,
       sum(n.scrap_cost)      AS hurda_maliyeti_try,
       sum(n.rework_cost)     AS yeniden_isleme_maliyeti_try,
       sum(n.other_cost)      AS diger_maliyet_try,
       sum(n.total_cost)      AS toplam_kalite_maliyeti_try,
       round(avg(n.days_to_close), 1) AS ortalama_kapanma_gunu
FROM nonconformances n
GROUP BY 1,2,3,4,5,6,7,8 ORDER BY 1, toplam_kalite_maliyeti_try DESC;""")

    v.append("""
CREATE VIEW v_scrap_analysis AS
SELECT extract(year FROM w.actual_start)::int AS yil, p.category AS kategori,
       wc.name AS is_merkezi,
       sum(w.planned_qty) AS planlanan_adet,
       sum(w.scrap_qty)   AS hurda_adet,
       round(100 * sum(w.scrap_qty) / NULLIF(sum(w.planned_qty), 0), 3) AS hurda_orani_pct,
       round(sum(w.scrap_qty * w.unit_cost), 2) AS tahmini_hurda_maliyeti_try
FROM production_orders w
JOIN products p ON p.id = w.product_id
JOIN work_centers wc ON wc.id = w.work_center_id
WHERE w.status <> 'İptal'
GROUP BY 1,2,3 ORDER BY 1, tahmini_hurda_maliyeti_try DESC;""")

    v.append("""
CREATE VIEW v_supplier_quality AS
SELECT vn.id AS tedarikci_id, vn.name AS tedarikci, vn.vendor_type AS tedarikci_tipi,
       vn.country AS ulke, vn.quality_score AS kalite_puani, vn.otd_score AS termin_puani,
       vn.iso_certified AS iso_belgeli,
       count(DISTINCT n.id)            AS uygunsuzluk_adedi,
       coalesce(sum(n.total_cost), 0)  AS uygunsuzluk_maliyeti_try,
       count(DISTINCT po.id)           AS siparis_adedi,
       coalesce(sum(po.total_base), 0) AS satinalma_tutari_try
FROM vendors vn
LEFT JOIN nonconformances n ON n.vendor_id = vn.id
LEFT JOIN purchase_orders po ON po.vendor_id = vn.id AND po.status <> 'İptal'
GROUP BY 1,2,3,4,5,6,7 ORDER BY satinalma_tutari_try DESC;""")

    return _part4(v, selected, today)


def _part4(v, selected, today):
    # ============================================= bakım, İSG, stok, satınalma ==
    v.append("""
CREATE VIEW v_maintenance_summary AS
SELECT date_trunc('month', mo.start_date)::date AS ay, m.code AS tezgah_kodu,
       m.name AS tezgah, wc.name AS is_merkezi, mo.maintenance_type AS bakim_tipi,
       mo.is_planned AS planli_mi,
       count(*)                  AS bakim_adedi,
       sum(mo.downtime_hours)    AS durus_saati,
       sum(mo.labor_hours)       AS iscilik_saati,
       sum(mo.labor_cost)        AS iscilik_try,
       sum(mo.parts_cost)        AS yedek_parca_try,
       sum(mo.external_cost)     AS dis_servis_try,
       sum(mo.total_cost)        AS toplam_bakim_maliyeti_try
FROM maintenance_orders mo
JOIN machines m ON m.id = mo.machine_id
LEFT JOIN work_centers wc ON wc.id = mo.work_center_id
GROUP BY 1,2,3,4,5,6 ORDER BY 1, toplam_bakim_maliyeti_try DESC;""")

    v.append("""
CREATE VIEW v_machine_reliability AS
SELECT m.id AS tezgah_id, m.code AS tezgah_kodu, m.name AS tezgah,
       m.manufacturer AS marka, m.model, m.year_installed AS kurulum_yili,
       wc.name AS is_merkezi,
       count(*) FILTER (WHERE NOT mo.is_planned)          AS ariza_adedi,
       count(*) FILTER (WHERE mo.is_planned)              AS planli_bakim_adedi,
       round(sum(mo.downtime_hours) FILTER (WHERE NOT mo.is_planned), 2) AS ariza_durus_saati,
       round(sum(mo.downtime_hours), 2)                   AS toplam_durus_saati,
       sum(mo.total_cost)                                 AS toplam_bakim_maliyeti_try,
       mode() WITHIN GROUP (ORDER BY mo.failure_mode)     AS en_sik_ariza_tipi
FROM machines m
JOIN maintenance_orders mo ON mo.machine_id = m.id
LEFT JOIN work_centers wc ON wc.id = m.work_center_id
GROUP BY 1,2,3,4,5,6,7 ORDER BY ariza_durus_saati DESC NULLS LAST;""")

    v.append("""
CREATE VIEW v_hse_summary AS
SELECT extract(year FROM h.incident_date)::int AS yil, d.name AS departman,
       h.incident_type AS olay_tipi, h.severity AS onem_derecesi,
       count(*)                     AS olay_adedi,
       sum(h.lost_days)             AS kayip_gun,
       count(*) FILTER (WHERE h.is_lost_time) AS kayip_gunlu_kaza_adedi
FROM hse_incidents h LEFT JOIN departments d ON d.id = h.department_id
GROUP BY 1,2,3,4 ORDER BY 1, olay_adedi DESC;""")

    v.append("""
CREATE VIEW v_inventory_valuation AS
SELECT s.item_type AS stok_sinifi,
       CASE WHEN s.item_type = 'Hammadde' THEN rm.name ELSE p.name END AS malzeme,
       CASE WHEN s.item_type = 'Hammadde' THEN rm.category ELSE p.category END AS kategori,
       CASE WHEN s.item_type = 'Hammadde' THEN rm.uom ELSE p.uom END AS birim,
       sum(CASE WHEN s.move_type = 'Çıkış' THEN -s.qty ELSE s.qty END) AS eldeki_miktar,
       sum(CASE WHEN s.move_type = 'Çıkış' THEN -s.value_base ELSE s.value_base END)
                                                                       AS stok_degeri_try
FROM stock_moves s
LEFT JOIN raw_materials rm ON rm.id = s.item_id AND s.item_type = 'Hammadde'
LEFT JOIN products p ON p.id = s.item_id AND s.item_type = 'Mamul'
GROUP BY 1,2,3,4 ORDER BY stok_degeri_try DESC;""")

    v.append("""
CREATE VIEW v_stock_movement_monthly AS
SELECT date_trunc('month', s.move_date)::date AS ay, s.item_type AS stok_sinifi,
       s.move_type AS hareket_tipi, s.reference_type AS referans_tipi,
       w.name AS ambar,
       count(*)          AS hareket_adedi,
       sum(s.qty)        AS miktar,
       sum(s.value_base) AS tutar_try
FROM stock_moves s LEFT JOIN warehouses w ON w.id = s.warehouse_id
GROUP BY 1,2,3,4,5 ORDER BY 1,2,3;""")

    v.append("""
CREATE VIEW v_purchase_by_vendor AS
SELECT extract(year FROM po.order_date)::int AS yil, vn.name AS tedarikci,
       vn.vendor_type AS tedarikci_tipi, vn.country AS ulke, vn.currency AS para_birimi,
       po.spend_category AS harcama_kategorisi,
       count(*)              AS siparis_adedi,
       sum(po.subtotal_base) AS tutar_try,
       sum(po.total_eur)     AS tutar_eur,
       sum(po.total_usd)     AS tutar_usd,
       round(avg(vn.lead_time_days), 1) AS ortalama_temin_gunu
FROM purchase_orders po JOIN vendors vn ON vn.id = po.vendor_id
WHERE po.status <> 'İptal'
GROUP BY 1,2,3,4,5,6 ORDER BY 1, tutar_try DESC;""")

    v.append("""
CREATE VIEW v_purchase_by_category AS
SELECT date_trunc('month', po.order_date)::date AS ay,
       po.spend_category AS harcama_kategorisi, po.po_type AS siparis_tipi,
       count(*)              AS siparis_adedi,
       sum(po.subtotal_base) AS tutar_try,
       sum(po.total_eur)     AS tutar_eur
FROM purchase_orders po
WHERE po.status <> 'İptal'
GROUP BY 1,2,3 ORDER BY 1, tutar_try DESC;""")

    v.append("""
CREATE VIEW v_vendor_performance AS
SELECT vn.id AS tedarikci_id, vn.name AS tedarikci, vn.vendor_type AS tedarikci_tipi,
       vn.country AS ulke, vn.rating AS puan, vn.quality_score AS kalite_puani,
       vn.otd_score AS termin_puani, vn.payment_terms_days AS vade_gun,
       vn.is_approved AS onayli_mi,
       count(DISTINCT po.id)                    AS siparis_adedi,
       coalesce(sum(po.subtotal_base), 0)       AS satinalma_try,
       coalesce(sum(vb.balance_base), 0)        AS acik_borc_try,
       count(DISTINCT n.id)                     AS uygunsuzluk_adedi
FROM vendors vn
LEFT JOIN purchase_orders po ON po.vendor_id = vn.id AND po.status <> 'İptal'
LEFT JOIN vendor_invoices vb ON vb.vendor_id = vn.id
LEFT JOIN nonconformances n ON n.vendor_id = vn.id
GROUP BY 1,2,3,4,5,6,7,8,9 ORDER BY satinalma_try DESC;""")

    # ================================================================ İK ==
    v.append("""
CREATE VIEW v_payroll_monthly AS
SELECT pi.period_date AS ay, d.name AS departman, pi.shift AS vardiya,
       count(*)                     AS personel_adedi,
       sum(pi.base_salary)          AS temel_ucret_try,
       sum(pi.overtime_pay)         AS fazla_mesai_try,
       sum(pi.overtime_hours)       AS fazla_mesai_saat,
       sum(pi.shift_premium)        AS vardiya_primi_try,
       sum(pi.bonus)                AS ikramiye_try,
       sum(pi.allowances)           AS yol_yemek_try,
       sum(pi.gross_pay)            AS brut_ucret_try,
       sum(pi.employee_social)      AS sgk_isci_payi_try,
       sum(pi.income_tax)           AS gelir_vergisi_try,
       sum(pi.net_pay)              AS net_ucret_try,
       sum(pi.employer_social)      AS sgk_isveren_payi_try,
       sum(pi.severance_provision)  AS kidem_karsiligi_try,
       sum(pi.employer_cost)        AS toplam_isveren_maliyeti_try,
       sum(pi.employer_cost_eur)    AS toplam_isveren_maliyeti_eur,
       sum(pi.employer_cost_usd)    AS toplam_isveren_maliyeti_usd
FROM payroll_items pi JOIN departments d ON d.id = pi.department_id
GROUP BY 1,2,3 ORDER BY 1,2,3;""")

    v.append(f"""
CREATE VIEW v_headcount AS
SELECT d.name AS departman, e.job_family AS gorev_ailesi, e.skill_level AS kademe,
       e.shift AS vardiya, e.gender AS cinsiyet, e.education AS egitim,
       count(*) FILTER (WHERE e.is_active)                   AS aktif_personel,
       count(*) FILTER (WHERE NOT e.is_active)               AS ayrilan_personel,
       round(avg(e.annual_gross) FILTER (WHERE e.is_active), 2) AS ortalama_yillik_brut_try,
       round(avg(e.monthly_gross_try) FILTER (WHERE e.is_active), 2) AS ortalama_aylik_brut_try,
       round(avg(DATE '{today}' - e.hire_date) / 365.25, 2)  AS ortalama_kidem_yil,
       round(avg(extract(year FROM DATE '{today}') - e.birth_year), 1) AS ortalama_yas
FROM employees e JOIN departments d ON d.id = e.department_id
GROUP BY 1,2,3,4,5,6 ORDER BY 1,2;""")

    v.append("""
CREATE VIEW v_employee_directory AS
SELECT e.employee_no AS sicil_no, e.full_name AS ad_soyad, d.name AS departman,
       e.role AS unvan, e.job_family AS gorev_ailesi, e.skill_level AS kademe,
       e.shift AS vardiya, wc.name AS is_merkezi, e.hire_date AS ise_giris,
       e.termination_date AS cikis_tarihi, e.is_active AS aktif_mi,
       e.seniority_years AS kidem_yil, e.education AS egitim, e.gender AS cinsiyet,
       e.birth_year AS dogum_yili, e.marital_status AS medeni_durum,
       e.children_count AS cocuk_sayisi, e.city AS sehir, e.phone AS telefon,
       e.email AS e_posta, e.employment_type AS calisma_sekli,
       e.monthly_gross_try AS aylik_brut_try, e.annual_gross AS yillik_brut_try,
       e.leave_entitlement_days AS yillik_izin_hakki_gun,
       e.overtime_eligible AS mesai_yapabilir, e.union_member AS sendika_uyesi,
       e.cost_center AS masraf_merkezi, m.full_name AS yonetici
FROM employees e
JOIN departments d ON d.id = e.department_id
LEFT JOIN work_centers wc ON wc.id = e.work_center_id
LEFT JOIN employees m ON m.id = e.manager_id
ORDER BY d.name, e.full_name;""")

    v.append("""
CREATE VIEW v_leave_summary AS
SELECT extract(year FROM l.start_date)::int AS yil, d.name AS departman,
       l.leave_type AS izin_tipi, l.status AS durum,
       count(*)     AS izin_adedi,
       sum(l.days)  AS toplam_gun
FROM leave_records l
JOIN employees e ON e.id = l.employee_id
JOIN departments d ON d.id = e.department_id
GROUP BY 1,2,3,4 ORDER BY 1,2, toplam_gun DESC;""")

    # =============================================== CRM, lojistik, varlıklar ==
    v.append("""
CREATE VIEW v_sales_pipeline AS
SELECT o.stage AS asama, o.status AS durum, o.product_category AS urun_kategorisi,
       count(*)               AS firsat_adedi,
       sum(o.amount_base)     AS yillik_potansiyel_try,
       round(avg(o.probability_pct), 1) AS ortalama_olasilik_pct,
       round(avg(o.close_date - o.created_date), 1) AS ortalama_kapanma_gunu
FROM opportunities o
GROUP BY 1,2,3 ORDER BY yillik_potansiyel_try DESC;""")

    v.append("""
CREATE VIEW v_win_rate AS
SELECT extract(year FROM o.created_date)::int AS yil, e.full_name AS satis_personeli,
       count(*)                                          AS toplam_firsat,
       count(*) FILTER (WHERE o.status = 'Kazanıldı')    AS kazanilan,
       count(*) FILTER (WHERE o.status = 'Kaybedildi')   AS kaybedilen,
       round(100.0 * count(*) FILTER (WHERE o.status = 'Kazanıldı')
             / NULLIF(count(*) FILTER (WHERE o.status IN ('Kazanıldı','Kaybedildi')), 0), 2)
                                                         AS kazanma_orani_pct,
       sum(o.amount_base) FILTER (WHERE o.status = 'Kazanıldı')  AS kazanilan_tutar_try,
       sum(o.amount_base) FILTER (WHERE o.status = 'Kaybedildi') AS kaybedilen_tutar_try,
       mode() WITHIN GROUP (ORDER BY o.win_loss_reason)  AS en_sik_neden
FROM opportunities o LEFT JOIN employees e ON e.id = o.owner_id
GROUP BY 1,2 ORDER BY 1, kazanilan_tutar_try DESC NULLS LAST;""")

    v.append("""
CREATE VIEW v_lead_conversion AS
SELECT extract(year FROM l.created_date)::int AS yil, l.source AS kaynak,
       l.country AS ulke, l.interest_category AS ilgi_alani,
       count(*)                                                AS aday_adedi,
       count(*) FILTER (WHERE l.status = 'Müşteriye Dönüştü')  AS donusen,
       round(100.0 * count(*) FILTER (WHERE l.status = 'Müşteriye Dönüştü')
             / NULLIF(count(*), 0), 2)                          AS donusum_orani_pct,
       round(avg(l.score), 1)                                   AS ortalama_puan
FROM leads l GROUP BY 1,2,3,4 ORDER BY 1, aday_adedi DESC;""")

    v.append("""
CREATE VIEW v_quotation_performance AS
SELECT extract(year FROM q.quote_date)::int AS yil, q.status AS durum,
       c.name AS musteri, q.currency AS para_birimi,
       count(*)             AS teklif_adedi,
       sum(q.total_base)    AS teklif_tutari_try,
       round(avg(q.lead_time_days), 1) AS ortalama_termin_gun
FROM quotations q JOIN customers c ON c.id = q.customer_id
GROUP BY 1,2,3,4 ORDER BY 1, teklif_tutari_try DESC;""")

    v.append("""
CREATE VIEW v_part_approval_status AS
SELECT pa.approval_no AS onay_no, p.sku AS parca_kodu, p.name AS parca_adi,
       c.name AS musteri, pa.program_name AS proje, pa.submission_level AS sunum_seviyesi,
       pa.request_date AS talep_tarihi, pa.submission_date AS sunum_tarihi,
       pa.approval_date AS onay_tarihi, pa.status AS durum,
       pa.days_to_approve AS onay_suresi_gun, e.full_name AS sorumlu_muhendis,
       pa.reject_reason AS red_nedeni
FROM part_approvals pa
JOIN products p ON p.id = pa.product_id
JOIN customers c ON c.id = pa.customer_id
LEFT JOIN employees e ON e.id = pa.engineer_id
ORDER BY pa.request_date DESC;""")

    v.append("""
CREATE VIEW v_logistics_cost AS
SELECT date_trunc('month', s.ship_date)::date AS ay, s.mode AS tasima_sekli,
       s.dest_country AS varis_ulkesi, s.incoterm AS teslim_sekli,
       s.packaging_type AS ambalaj_tipi,
       count(*)                       AS sevkiyat_adedi,
       sum(s.gross_weight_kg)         AS brut_agirlik_kg,
       sum(s.pallet_count)            AS palet_adedi,
       sum(s.freight_cost)            AS navlun_try,
       sum(s.insurance_cost)          AS sigorta_try,
       sum(s.packing_cost)            AS ambalaj_try,
       sum(s.handling_cost)           AS elleclemetry,
       sum(s.total_logistics_cost)    AS toplam_lojistik_try,
       sum(s.cost_eur)                AS toplam_lojistik_eur,
       sum(s.billed_to_customer)      AS musteriye_yansitilan_try,
       sum(s.total_logistics_cost - s.billed_to_customer) AS net_lojistik_gideri_try,
       round(avg(s.transit_days), 1)  AS ortalama_transit_gun
FROM shipments s GROUP BY 1,2,3,4,5 ORDER BY 1, toplam_lojistik_try DESC;""")

    v.append("""
CREATE VIEW v_customs_summary AS
SELECT extract(year FROM cd.decl_date)::int AS yil, cd.dest_country AS varis_ulkesi,
       cd.document_type AS belge_tipi, cd.customs_office AS gumruk_mudurlugu,
       cd.status AS durum,
       count(*)                    AS beyanname_adedi,
       sum(cd.customs_value_base)  AS gumruk_kiymeti_try,
       sum(cd.duty_amount)         AS gumruk_vergisi_try,
       sum(cd.broker_fee)          AS musavirlik_try
FROM customs_declarations cd
GROUP BY 1,2,3,4,5 ORDER BY 1, gumruk_kiymeti_try DESC;""")

    v.append("""
CREATE VIEW v_shipment_performance AS
SELECT date_trunc('month', s.ship_date)::date AS ay,
       CASE WHEN s.is_export THEN 'İhracat' ELSE 'Yurt İçi' END AS pazar,
       s.mode AS tasima_sekli,
       count(*)                                            AS sevkiyat_adedi,
       count(*) FILTER (WHERE s.status = 'Teslim Edildi')  AS teslim_edilen,
       round(avg(s.transit_days), 1)                       AS ortalama_transit_gun,
       sum(s.gross_weight_kg)                              AS brut_agirlik_kg,
       round(sum(s.total_logistics_cost) / NULLIF(sum(s.gross_weight_kg), 0), 2)
                                                           AS kg_basi_lojistik_try
FROM shipments s GROUP BY 1,2,3 ORDER BY 1,2,3;""")

    v.append("""
CREATE VIEW v_fixed_asset_register AS
SELECT fa.asset_no AS varlik_no, fa.name AS varlik_adi, fa.category AS kategori,
       d.name AS departman, m.code AS tezgah_kodu, fa.acquisition_date AS alim_tarihi,
       fa.acquisition_cost AS alis_bedeli_try, fa.acquisition_cost_eur AS alis_bedeli_eur,
       fa.fx_rate AS alim_kuru, fa.useful_life_years AS faydali_omur_yil,
       fa.accumulated_depreciation AS birikmis_amortisman_try,
       fa.net_book_value AS net_defter_degeri_try, fa.status AS durum,
       fa.serial_no AS seri_no
FROM fixed_assets fa
LEFT JOIN departments d ON d.id = fa.department_id
LEFT JOIN machines m ON m.id = fa.machine_id
ORDER BY fa.acquisition_cost DESC;""")

    v.append("""
CREATE VIEW v_depreciation_schedule AS
SELECT de.period_date AS ay, fa.category AS varlik_kategorisi, d.name AS departman,
       count(DISTINCT de.asset_id) AS varlik_adedi,
       sum(de.depreciation_amount) AS amortisman_try,
       sum(de.book_value_after)    AS donem_sonu_net_deger_try
FROM depreciation_entries de
JOIN fixed_assets fa ON fa.id = de.asset_id
LEFT JOIN departments d ON d.id = fa.department_id
GROUP BY 1,2,3 ORDER BY 1,2;""")

    v.append("""
CREATE VIEW v_machine_telemetry_daily AS
SELECT date_trunc('day', ir.reading_ts)::date AS gun, m.code AS tezgah_kodu,
       m.name AS tezgah, wc.name AS is_merkezi, ir.shift AS vardiya,
       ir.metric AS olcum, ir.unit AS birim,
       count(*)              AS okuma_adedi,
       round(avg(ir.value), 3) AS ortalama,
       round(min(ir.value), 3) AS minimum,
       round(max(ir.value), 3) AS maksimum
FROM iot_readings ir
JOIN machines m ON m.id = ir.source_id
LEFT JOIN work_centers wc ON wc.id = ir.work_center_id
GROUP BY 1,2,3,4,5,6,7 ORDER BY 1, 2, 6;""")

    v.append("""
CREATE VIEW v_lot_traceability AS
SELECT lt.lot_no AS parti_no, p.sku AS parca_kodu, p.name AS parca_adi,
       c.name AS musteri, lt.production_date AS uretim_tarihi, lt.qty AS miktar,
       lt.heat_no AS dokum_parti_no, lt.material_lot AS hammadde_parti_no,
       lt.certificate_no AS sertifika_no, w.wo_no AS is_emri_no, lt.status AS durum
FROM lots lt
JOIN products p ON p.id = lt.product_id
LEFT JOIN customers c ON c.id = lt.customer_id
LEFT JOIN production_orders w ON w.id = lt.production_order_id
ORDER BY lt.production_date DESC;""")

    return "\n".join(v)
