# -*- coding: utf-8 -*-
"""Yuklenen veritabani uzerinde tutarlilik kontrolleri."""
from __future__ import annotations

import sys

from . import load as L

KONTROLLER = [
    ("Tablo sayısı", "SELECT count(*) FROM information_schema.tables "
                     "WHERE table_schema='public' AND table_type='BASE TABLE';"),
    ("View sayısı", "SELECT count(*) FROM information_schema.views WHERE table_schema='public';"),
    ("Toplam satır", "SELECT sum(n_live_tup)::bigint FROM pg_stat_user_tables;"),
    ("Mahalle sayısı", "SELECT count(*) FROM neighborhood;"),
    ("2026 nüfus", "SELECT sum(population) FROM population_stat WHERE year=2026;"),
    ("Aktif personel", "SELECT count(*) FROM employee WHERE status <> 'Ayrıldı';"),
    ("2025 gelir (mlr TL)",
     "SELECT round(sum(amount)/1e9, 3) FROM revenue_transaction WHERE year=2025;"),
    ("2025 gider (mlr TL)",
     "SELECT round(sum(total_amount)/1e9, 3) FROM expense_transaction WHERE year=2025;"),
    ("2025 personel gideri payı %",
     "SELECT round(100.0*(SELECT sum(employer_cost) FROM payroll WHERE year=2025)"
     "/(SELECT sum(total_amount) FROM expense_transaction WHERE year=2025), 2);"),
    ("2025 işsizlik oranı %",
     "SELECT round(100.0*sum(unemployed_count)/sum(labor_force), 2) "
     "FROM unemployment_stat WHERE year=2025;"),
    ("Emlak tahsilat oranı % (2024)",
     "SELECT round(100.0*(SELECT sum(p.amount) FROM property_tax_payment p "
     "JOIN property_tax_assessment a USING (property_tax_assessment_id) WHERE a.tax_year=2024)"
     "/(SELECT sum(assessed_amount) FROM property_tax_assessment WHERE tax_year=2024), 2);"),
    ("2021 COVID ölüm payı %",
     "SELECT round(100.0*count(*) FILTER (WHERE cause_detail='COVID-19')/count(*), 2) "
     "FROM death_record WHERE extract(year FROM death_date)=2021;"),
    ("Başvuru SLA uyumu % (2025)",
     "SELECT round(100.0*count(*) FILTER (WHERE sla_met)/count(*), 2) "
     "FROM service_request WHERE extract(year FROM created_date)=2025;"),
    ("Geri kazanım oranı % (2019→2026)",
     "SELECT round(avg(recycling_rate) FILTER (WHERE extract(year FROM period_month)=2019), 2)"
     " || ' → ' || round(avg(recycling_rate) FILTER (WHERE extract(year FROM period_month)=2026), 2)"
     " FROM recycling_stat;"),
    ("Yetim FK kaydı (olmamalı)",
     "SELECT count(*) FROM service_request s LEFT JOIN citizen c USING (citizen_id) "
     "WHERE s.citizen_id IS NOT NULL AND c.citizen_id IS NULL;"),
    ("Tarih aralığı dışı kayıt (olmamalı)",
     "SELECT count(*) FROM service_request "
     "WHERE created_date < DATE '2019-01-01' OR created_date > DATE '2026-08-31';"),
]


def calistir(db):
    print(f"\n  Doğrulama — {db}\n")
    for ad, sql in KONTROLLER:
        deger = L.deger(db, sql)
        print(f"  {ad:.<40} {deger}")
    print()


if __name__ == "__main__":
    calistir(sys.argv[1] if len(sys.argv) > 1 else "bld_bahcelievler")
