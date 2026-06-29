"""Analytics convenience views, created after load.

Each view is emitted only when its required base tables were selected, so the
generated database never references a missing table.
"""
from __future__ import annotations


def build_views(selected: set, today: str) -> str:
    out = []

    if {"sales_orders"} <= selected:
        out.append("""
CREATE VIEW v_monthly_sales AS
SELECT date_trunc('month', order_date)::date AS month,
       count(*) AS orders,
       sum(total) AS revenue,
       sum(cogs) AS cogs,
       sum(margin) AS margin
FROM sales_orders
WHERE status <> 'cancelled'
GROUP BY 1 ORDER BY 1;""")

        out.append("""
CREATE VIEW v_customer_revenue AS
SELECT c.id AS customer_id, c.name, c.segment,
       count(o.id) AS orders, coalesce(sum(o.total),0) AS revenue
FROM customers c
LEFT JOIN sales_orders o ON o.customer_id = c.id AND o.status <> 'cancelled'
GROUP BY 1,2,3 ORDER BY revenue DESC;""")

    if {"sales_order_lines", "products"} <= selected:
        out.append("""
CREATE VIEW v_product_profitability AS
SELECT p.id AS product_id, p.sku, p.name, p.category,
       sum(l.qty) AS units_sold,
       sum(l.line_subtotal) AS revenue,
       sum(l.line_cogs) AS cogs,
       sum(l.line_margin) AS margin,
       CASE WHEN sum(l.line_subtotal) > 0
            THEN round(100 * sum(l.line_margin) / sum(l.line_subtotal), 2) END AS margin_pct
FROM products p
JOIN sales_order_lines l ON l.product_id = p.id
GROUP BY 1,2,3,4 ORDER BY margin DESC;""")

    if {"invoices"} <= selected:
        out.append(f"""
CREATE VIEW v_ar_aging AS
SELECT i.id AS invoice_id, i.invoice_no, i.customer_id, c.name AS customer,
       i.total, i.balance, i.due_date,
       CASE WHEN i.balance <= 0 THEN 'paid'
            WHEN i.due_date >= DATE '{today}' THEN 'current'
            WHEN i.due_date >= DATE '{today}' - 30 THEN '1-30'
            WHEN i.due_date >= DATE '{today}' - 60 THEN '31-60'
            WHEN i.due_date >= DATE '{today}' - 90 THEN '61-90'
            ELSE '90+' END AS aging_bucket
FROM invoices i JOIN customers c ON c.id = i.customer_id
WHERE i.balance > 0;""")

    if {"stock_moves"} <= selected:
        out.append("""
CREATE VIEW v_inventory_valuation AS
SELECT item_type, item_id,
       sum(CASE WHEN move_type = 'out' THEN -qty ELSE qty END) AS on_hand_qty,
       sum(CASE WHEN move_type = 'out' THEN -qty ELSE qty END * unit_cost) AS value
FROM stock_moves
GROUP BY 1,2;""")

    if {"production_orders"} <= selected:
        out.append("""
CREATE VIEW v_production_summary AS
SELECT date_trunc('month', start_date)::date AS month,
       count(*) AS orders,
       sum(planned_qty) AS planned, sum(produced_qty) AS produced, sum(scrap_qty) AS scrap
FROM production_orders GROUP BY 1 ORDER BY 1;""")

    return "\n".join(out)
