"""erp-demo-gen CLI.

  python3 engine/run.py plan  --spec out/<slug>/spec.json
  python3 engine/run.py build --spec out/<slug>/spec.json --seeds out/<slug>/seeds.json
  python3 engine/run.py validate --slug <slug> --spec out/<slug>/spec.json

`plan`  derives the company profile + selected tables and writes a seeds
template for the LLM to fill. `build` generates, loads, and validates.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import catalog, sizing, seeds as seeds_mod, generate, load, validate  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out")


def _load_profile(spec):
    industry, tables_cfg, tuning_cfg = catalog.load_industry(spec["industry"])
    spec["industry"] = industry
    tables = catalog.select_tables(tables_cfg)
    profile = sizing.build_profile(spec, tuning_cfg, tables)
    return profile, tuning_cfg, tables


def cmd_plan(args):
    spec = json.load(open(args.spec))
    profile, tuning, tables = _load_profile(spec)
    out_dir = os.path.join(OUT, profile.slug)
    os.makedirs(out_dir, exist_ok=True)

    needs_raw = "raw_materials" in tables
    needs_wc = "work_centers" in tables
    tpl = seeds_mod.template(profile, needs_raw, needs_wc)
    tpl_path = os.path.join(out_dir, "seeds.template.json")
    with open(tpl_path, "w") as f:
        json.dump(tpl, f, indent=2)

    print(f"Company : {profile.company_name}  [{profile.slug}]")
    print(f"Industry: {profile.industry}   Currency: {profile.currency}   Seed: {profile.seed}")
    print(f"Period  : {profile.start_year}-{profile.end_year()} ({profile.years} years)")
    print(f"Size    : ${profile.annual_revenue:,.0f}/yr final, "
          f"{profile.annual_invoices:,} invoices/yr, {profile.employees} employees")
    print(f"Derived : {profile.n_customers} customers, {profile.n_vendors} vendors, "
          f"{profile.n_products} products, {profile.n_warehouses} warehouses, "
          f"AOV ${profile.avg_order_value:,.0f}, growth {profile.growth_rate:.0%}")
    print(f"Tables ({len(tables)}): {', '.join(tables)}")
    print("\nRevenue by year:")
    prev = None
    for yi in range(profile.years):
        rev = profile.revenue_for_year(yi)
        yoy = "" if prev is None else f"  ({(rev/prev-1)*100:+.1f}%)"
        partial = "  [YTD]" if (yi == profile.years - 1 and profile.end_month < 12) else ""
        print(f"  {profile.start_year+yi}: {profile.currency} {rev:,.0f}{yoy}{partial}")
        prev = rev
    print(f"\nSeed template written: {tpl_path}")
    print("Fill it as seeds.json (meet the *_target counts), then run `build`.")


def cmd_build(args):
    spec = json.load(open(args.spec))
    profile, tuning, tables = _load_profile(spec)
    out_dir = os.path.join(OUT, profile.slug)

    raw_seeds = seeds_mod.load_seeds(args.seeds)
    from engine.util import Rng
    filled = seeds_mod.validate_and_fill(
        raw_seeds, profile, Rng(profile.seed).stream("seedfill"),
        needs_raw="raw_materials" in tables, needs_work_centers="work_centers" in tables,
        name_style=tuning.get("company_name_style", "us"))

    print("Generating rows...")
    g = generate.run_generation(profile, filled, tuning)
    counts = generate.write_outputs(g, out_dir)
    total_rows = sum(counts.values())
    print(f"Generated {total_rows:,} rows across {len(counts)} tables -> {out_dir}")
    for t, n in counts.items():
        print(f"  {t:<24} {n:>10,}")

    if args.generate_only:
        print("\n--generate-only: skipped Docker load.")
        return

    print("\nStarting Postgres (docker compose up)...")
    load.compose_up()
    print(f"Loading database erp_{profile.slug} ...")
    db = load.load_database(profile.slug)

    print("\nValidating...")
    checks = validate.run_checks(db, profile, set(tables))
    passed = sum(1 for _, ok, _ in checks if ok)
    for name, ok, detail in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}  ({detail})")
    m = validate.metrics(db, profile, set(tables))

    print("\n=== SUMMARY ===")
    print(f"Connection: {load.connection_string(profile.slug)}")
    print(f"Checks    : {passed}/{len(checks)} passed")
    cur = profile.currency
    if "total_revenue" in m:
        print(f"Revenue   : {m['total_revenue']:,.0f} {cur} net "
              f"({m.get('gross_with_tax', 0):,.0f} {cur} incl. tax) "
              f"over {m.get('date_min')}..{m.get('date_max')}")
    if "units_sold" in m:
        print(f"Units sold: {m['units_sold']:,.0f} pcs")
    if "open_ar" in m:
        print(f"Open AR   : {m['open_ar']:,.0f} {cur}")
    if m.get("pnl"):
        print(f"P&L       : {m['pnl']}")
    print(f"Rows      : {total_rows:,}")
    print("\nTry these queries:")
    print(f'  psql "{load.connection_string(profile.slug)}" -c "SELECT * FROM v_monthly_sales LIMIT 24;"')
    print(f'  psql "{load.connection_string(profile.slug)}" -c "SELECT * FROM v_customer_revenue LIMIT 10;"')
    if "production_orders" in tables:
        print(f'  psql "{load.connection_string(profile.slug)}" -c "SELECT * FROM v_production_summary LIMIT 12;"')

    _append_changelog(profile, total_rows, passed, len(checks))


def cmd_validate(args):
    spec = json.load(open(args.spec))
    profile, tuning, tables = _load_profile(spec)
    db = f"erp_{args.slug or profile.slug}"
    checks = validate.run_checks(db, profile, set(tables))
    for name, ok, detail in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}  ({detail})")


def _append_changelog(profile, rows, passed, total):
    path = os.path.join(ROOT, "memory", "changelog.md")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    line = (f"- {date.today().isoformat()} · {profile.industry} · {profile.company_name} · "
            f"{profile.years}y · {rows:,} rows · checks {passed}/{total} · seed {profile.seed}\n")
    with open(path, "a") as f:
        f.write(line)


def main():
    ap = argparse.ArgumentParser(prog="erp-demo-gen")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("plan"); p.add_argument("--spec", required=True); p.set_defaults(fn=cmd_plan)
    b = sub.add_parser("build")
    b.add_argument("--spec", required=True); b.add_argument("--seeds", required=True)
    b.add_argument("--generate-only", action="store_true"); b.set_defaults(fn=cmd_build)
    v = sub.add_parser("validate")
    v.add_argument("--spec", required=True); v.add_argument("--slug", default=None)
    v.set_defaults(fn=cmd_validate)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
