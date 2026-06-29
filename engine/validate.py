"""Post-load integrity + realism checks, run against the live database via psql.

Returns a list of (name, ok, detail) and a metrics dict. Catches the failure
modes that make demo data look fake: dangling FKs, totals that don't reconcile,
payments exceeding invoices, and revenue far off the requested target.
"""
from __future__ import annotations

from . import load


def _int(db, sql):
    v = load.query_value(db, sql)
    try:
        return int(v)
    except (ValueError, TypeError):
        return None


def _float(db, sql):
    v = load.query_value(db, sql)
    try:
        return float(v)
    except (ValueError, TypeError):
        return 0.0


def table_exists(db, t):
    return _int(db, f"SELECT count(*) FROM information_schema.tables "
                    f"WHERE table_schema='public' AND table_name='{t}'") == 1


def run_checks(db, profile, selected):
    checks = []

    def fk(child, col, parent, pcol="id"):
        if child in selected and parent in selected:
            n = _int(db, f"SELECT count(*) FROM {child} c "
                         f"LEFT JOIN {parent} p ON c.{col}=p.{pcol} "
                         f"WHERE c.{col} IS NOT NULL AND p.{pcol} IS NULL")
            checks.append((f"FK {child}.{col} -> {parent}", n == 0, f"{n} orphan(s)"))

    fk("sales_order_lines", "order_id", "sales_orders")
    fk("sales_order_lines", "product_id", "products")
    fk("sales_orders", "customer_id", "customers")
    fk("invoices", "order_id", "sales_orders")
    fk("invoice_lines", "invoice_id", "invoices")
    fk("payments", "invoice_id", "invoices")
    fk("returns", "order_id", "sales_orders")
    fk("purchase_order_lines", "po_id", "purchase_orders")
    fk("purchase_orders", "vendor_id", "vendors")
    fk("production_consumption", "production_order_id", "production_orders")
    fk("bom_lines", "bom_id", "bom")

    # order totals reconcile to their line totals
    if "sales_order_lines" in selected:
        bad = _int(db, """
            SELECT count(*) FROM (
              SELECT o.id, o.total, coalesce(sum(l.line_total),0) AS lt
              FROM sales_orders o JOIN sales_order_lines l ON l.order_id=o.id
              GROUP BY o.id, o.total
              HAVING abs(o.total - coalesce(sum(l.line_total),0)) > 0.05
            ) x""")
        checks.append(("Order totals reconcile to lines", bad == 0, f"{bad} mismatched order(s)"))

    # payments never exceed invoice total
    if "payments" in selected:
        bad = _int(db, "SELECT count(*) FROM invoices WHERE amount_paid > total + 0.05")
        checks.append(("Payments <= invoice total", bad == 0, f"{bad} over-paid invoice(s)"))
        bad2 = _int(db, "SELECT count(*) FROM invoices WHERE round(amount_paid+balance,2) <> round(total,2)")
        checks.append(("Invoice paid+balance = total", bad2 == 0, f"{bad2} inconsistent invoice(s)"))

    # net revenue (subtotal - discount, excl. tax) close to target in final year
    final_year = profile.end_year()
    if "sales_orders" in selected:
        rev = _float(db, f"SELECT coalesce(sum(subtotal - discount),0) FROM sales_orders "
                         f"WHERE status<>'cancelled' AND extract(year from order_date)={final_year}")
        target = profile.annual_revenue
        ratio = rev / target if target else 0
        ok = 0.85 <= ratio <= 1.15
        checks.append((f"Final-year net revenue near target ({ratio:.0%})", ok,
                       f"actual ${rev:,.0f} vs target ${target:,.0f}"))

    return checks


def metrics(db, profile, selected):
    m = {}
    if "sales_orders" in selected:
        m["total_revenue"] = _float(db, "SELECT coalesce(sum(subtotal - discount),0) FROM sales_orders WHERE status<>'cancelled'")
        m["gross_with_tax"] = _float(db, "SELECT coalesce(sum(total),0) FROM sales_orders WHERE status<>'cancelled'")
        m["sales_orders"] = _int(db, "SELECT count(*) FROM sales_orders")
        m["date_min"] = load.query_value(db, "SELECT min(order_date) FROM sales_orders")
        m["date_max"] = load.query_value(db, "SELECT max(order_date) FROM sales_orders")
    if "invoices" in selected:
        m["open_ar"] = _float(db, "SELECT coalesce(sum(balance),0) FROM invoices")
    if "customers" in selected:
        m["customers"] = _int(db, "SELECT count(*) FROM customers")
    if "products" in selected:
        m["products"] = _int(db, "SELECT count(*) FROM products")
    return m
