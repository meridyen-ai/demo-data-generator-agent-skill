"""Orchestrate generation and write artifacts (CSVs + load.sql).

Generation order respects FK dependencies. Lookups are built after the orders
exist so downstream domains (stock, bank) can resolve dates/names. Output:
  out/<slug>/<table>.csv     one per selected table (header row)
  out/<slug>/load.sql        DDL + COPY + indexes + views, run via psql -f
"""
from __future__ import annotations

import csv
import os
from datetime import date

from . import ddl, views
from .generators import Gen
from .util import Rng


def run_generation(profile, seeds, tuning) -> Gen:
    if profile.industry == "machinery_dealer":
        return _run_machinery(profile, seeds, tuning)
    if profile.industry == "contract_machining":
        return _run_contract(profile, seeds, tuning)
    g = Gen(profile, seeds, tuning, Rng(profile.seed))

    g.gen_departments()
    g.gen_employees()
    g.gen_customers()
    g.gen_vendors()
    g.gen_warehouses()
    if g.has("work_centers"):
        g.gen_work_centers()
    g.gen_products()
    if g.has("raw_materials"):
        g.gen_raw_materials()
    if g.has("price_list"):
        g.gen_price_list()
    if g.has("promotions"):
        g.gen_promotions()
    if g.has("bom"):
        g.gen_bom()

    g.gen_sales()            # sales_orders, lines, invoices, invoice_lines, payments, returns
    g.gen_purchasing()
    if g.has("production_orders"):
        g.gen_production()

    g.build_lookups()
    g.gen_stock_moves()
    g.gen_bank()
    g.gen_gl()
    g.gen_iot()
    return g


def _run_machinery(profile, seeds, tuning):
    """Used machine-tool dealer: serialized stock, multi-currency, full ERP
    back office. Order matters — machine units are created by the sales pass,
    the purchasing pass then builds the acquisition paperwork behind them."""
    from .gen_machinery import MachineryGen
    g = MachineryGen(profile, seeds, tuning, Rng(profile.seed))
    g.gen_company()
    g.gen_currencies()
    g.gen_fx_rates()
    g.gen_tax_codes()
    g.gen_chart_of_accounts()
    g.gen_expense_categories()
    g.gen_departments()
    g.gen_warehouses()
    g.gen_employees()
    g.gen_customers()
    g.gen_vendors()
    g.gen_carriers()
    g.gen_products()
    g.gen_price_list()
    g.gen_sales()
    g.gen_stock_units()
    g.gen_purchasing()
    g.gen_refurbishment()
    g.build_lookups()
    g.gen_crm()
    g.gen_logistics()
    g.gen_service()
    g.gen_payroll()
    g.gen_leave()
    g.gen_fixed_assets()
    g.gen_expenses()
    g.gen_budgets()
    g.gen_stock_moves()
    g.gen_bank()
    g.gen_gl()
    return g


def _run_contract(profile, seeds, tuning):
    """Talaşlı imalat / fason metal parça üreticisi. Sıralama önemlidir: üretim
    satıştan doğar, satınalma üretimden doğar, giderler ise bordro, amortisman
    ve lojistik hesaplandıktan sonra toplanabilir."""
    from .gen_contract import ContractMachiningGen
    g = ContractMachiningGen(profile, seeds, tuning, Rng(profile.seed))
    g.gen_company()
    g.gen_currencies()
    g.gen_fx_rates()
    g.gen_tax_codes()
    g.gen_chart_of_accounts()
    g.gen_expense_categories()
    g.gen_departments()
    g.gen_warehouses()
    g.gen_work_centers()
    g.gen_employees()
    g.gen_machines()
    g.gen_customers()
    g.gen_vendors()
    g.gen_carriers()
    g.gen_raw_materials()
    g.gen_products()
    g.gen_bom()
    g.gen_routings()
    g.gen_price_list()
    g.gen_part_approvals()
    g.gen_sales()
    g.gen_production()
    g.gen_subcontract()
    g.gen_quality()
    g.gen_purchasing()
    g.build_lookups()
    g.gen_crm()
    g.gen_logistics()
    g.gen_maintenance()
    g.gen_hse()
    g.gen_payroll()
    g.gen_leave()
    g.gen_fixed_assets()
    g.gen_expenses()
    g.gen_budgets()
    g.gen_stock_moves()
    g.gen_bank()
    g.gen_gl()
    g.gen_iot()
    return g


def _fmt(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return "t" if v else "f"
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, float):
        # avoid scientific notation; trim trailing zeros sensibly
        return f"{v:.6f}".rstrip("0").rstrip(".") if v != int(v) else str(int(v))
    return str(v)


def write_outputs(g: Gen, out_dir: str, schema_prefix: str = "") -> dict:
    os.makedirs(out_dir, exist_ok=True)
    p = g.p
    counts = {}
    selected = [t for t in ddl.TABLE_ORDER if t in g.selected]

    for table in selected:
        cols = ddl.COLUMNS[table]
        rows = g.rows(table)
        counts[table] = len(rows)
        with open(os.path.join(out_dir, f"{table}.csv"), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(cols)
            for row in rows:
                w.writerow([_fmt(row.get(c)) for c in cols])

    today = (g._today() if hasattr(g, "_today") else date(p.end_year(), 12, 31)).isoformat()
    sql = [f"-- erp-demo-gen :: {p.company_name} ({p.industry})", "BEGIN;"]
    s = schema_prefix
    for table in selected:
        sql.append(ddl.DDL[table].format(s=s).strip())
    for table in selected:
        data_path = f"/data/{p.slug}/{table}.csv"
        sql.append(
            f"COPY {s}{table} FROM '{data_path}' WITH (FORMAT csv, HEADER true);"
        )
    for table in selected:
        for col in ddl.INDEXES.get(table, []):
            sql.append(f"CREATE INDEX ix_{table}_{col} ON {s}{table} ({col});")
    # reset sequences not needed (explicit ids). Add views:
    sql.append(views.build_views(g.selected, today))
    sql.append("COMMIT;")

    with open(os.path.join(out_dir, "load.sql"), "w") as f:
        f.write("\n".join(sql) + "\n")

    return counts
