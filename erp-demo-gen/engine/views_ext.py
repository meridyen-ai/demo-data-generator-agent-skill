"""Analytics views for the machinery-dealer database.

These replace the generic views because every money column here exists in two
currencies: the document currency and the EUR base. Anything that aggregates
across customers must use the ``*_base`` columns or it silently adds lira to
euros.

The P&L views are the point of the whole exercise: revenue and COGS come from
the sales tables, everything between gross profit and net profit comes from
``expenses`` (which carries payroll, depreciation, logistics, financing and tax
alongside bought-in operating costs, distinguished by ``source``).
"""
from __future__ import annotations

OPERATING_SOURCES = "('purchased','payroll','depreciation','logistics')"


def build_views(selected: set, today: str) -> str:
    v = []

    # ------------------------------------------------------------ sales core
    v.append("""
CREATE VIEW v_monthly_sales AS
SELECT date_trunc('month', o.order_date)::date AS month,
       count(DISTINCT o.id)                       AS orders,
       count(DISTINCT o.customer_id)              AS active_customers,
       sum(l.line_subtotal_base)                  AS revenue,
       sum(l.line_cogs_base)                      AS cogs,
       sum(l.line_margin_base)                    AS gross_profit,
       round(100 * sum(l.line_margin_base) / NULLIF(sum(l.line_subtotal_base), 0), 2)
                                                  AS gross_margin_pct
FROM sales_orders o
JOIN sales_order_lines l ON l.order_id = o.id
WHERE o.status <> 'cancelled'
GROUP BY 1 ORDER BY 1;""")

    v.append("""
CREATE VIEW v_revenue_by_stream AS
SELECT date_trunc('month', o.order_date)::date AS month,
       l.line_type                             AS revenue_stream,
       count(DISTINCT o.id)                    AS orders,
       sum(l.qty)                              AS units,
       sum(l.line_subtotal_base)               AS revenue,
       sum(l.line_cogs_base)                   AS cogs,
       sum(l.line_margin_base)                 AS gross_profit,
       round(100 * sum(l.line_margin_base) / NULLIF(sum(l.line_subtotal_base), 0), 2)
                                               AS gross_margin_pct
FROM sales_orders o
JOIN sales_order_lines l ON l.order_id = o.id
WHERE o.status <> 'cancelled'
GROUP BY 1, 2 ORDER BY 1, 2;""")

    v.append("""
CREATE VIEW v_yearly_sales AS
SELECT extract(year FROM o.order_date)::int AS year,
       count(DISTINCT o.id)                 AS orders,
       sum(l.line_subtotal_base)            AS revenue,
       sum(l.line_cogs_base)                AS cogs,
       sum(l.line_margin_base)              AS gross_profit,
       round(100 * sum(l.line_margin_base) / NULLIF(sum(l.line_subtotal_base), 0), 2)
                                            AS gross_margin_pct
FROM sales_orders o
JOIN sales_order_lines l ON l.order_id = o.id
WHERE o.status <> 'cancelled'
GROUP BY 1 ORDER BY 1;""")

    v.append("""
CREATE VIEW v_customer_revenue AS
SELECT c.id AS customer_id, c.name, c.segment, c.country, c.country_code, c.currency,
       c.industry, c.is_export,
       count(DISTINCT o.id)                     AS orders,
       coalesce(sum(l.line_subtotal_base), 0)   AS revenue,
       coalesce(sum(l.line_cogs_base), 0)       AS cogs,
       coalesce(sum(l.line_margin_base), 0)     AS gross_profit,
       round(100 * sum(l.line_margin_base) / NULLIF(sum(l.line_subtotal_base), 0), 2)
                                                AS gross_margin_pct,
       min(o.order_date)                        AS first_order,
       max(o.order_date)                        AS last_order
FROM customers c
LEFT JOIN sales_orders o ON o.customer_id = c.id AND o.status <> 'cancelled'
LEFT JOIN sales_order_lines l ON l.order_id = o.id
GROUP BY 1,2,3,4,5,6,7,8 ORDER BY revenue DESC NULLS LAST;""")

    v.append("""
CREATE VIEW v_country_performance AS
SELECT c.country, c.country_code,
       CASE WHEN c.country_code = 'DE' THEN 'Domestic'
            WHEN c.is_intra_eu THEN 'Intra-EU export'
            ELSE 'Non-EU export' END            AS trade_lane,
       count(DISTINCT c.id)                     AS customers,
       count(DISTINCT o.id)                     AS orders,
       sum(l.line_subtotal_base)                AS revenue,
       sum(l.line_margin_base)                  AS gross_profit,
       round(100 * sum(l.line_margin_base) / NULLIF(sum(l.line_subtotal_base), 0), 2)
                                                AS gross_margin_pct
FROM customers c
JOIN sales_orders o ON o.customer_id = c.id AND o.status <> 'cancelled'
JOIN sales_order_lines l ON l.order_id = o.id
GROUP BY 1,2,3 ORDER BY revenue DESC;""")

    v.append("""
CREATE VIEW v_product_profitability AS
SELECT p.id AS product_id, p.sku, p.name, p.item_type, p.category, p.subcategory, p.brand,
       sum(l.qty)                AS units_sold,
       sum(l.line_subtotal_base) AS revenue,
       sum(l.line_cogs_base)     AS cogs,
       sum(l.line_margin_base)   AS gross_profit,
       round(100 * sum(l.line_margin_base) / NULLIF(sum(l.line_subtotal_base), 0), 2)
                                 AS gross_margin_pct
FROM products p
JOIN sales_order_lines l ON l.product_id = p.id
JOIN sales_orders o ON o.id = l.order_id AND o.status <> 'cancelled'
GROUP BY 1,2,3,4,5,6,7 ORDER BY gross_profit DESC;""")

    v.append("""
CREATE VIEW v_salesperson_performance AS
SELECT e.id AS employee_id, e.full_name, e.country_code, d.name AS department,
       count(DISTINCT o.id)                                        AS orders,
       count(DISTINCT o.id) FILTER (WHERE o.order_type = 'Machine Deal') AS machine_deals,
       sum(l.line_subtotal_base)                                   AS revenue,
       sum(l.line_margin_base)                                     AS gross_profit,
       round(100 * sum(l.line_margin_base) / NULLIF(sum(l.line_subtotal_base), 0), 2)
                                                                   AS gross_margin_pct
FROM employees e
JOIN departments d ON d.id = e.department_id
JOIN sales_orders o ON o.salesperson_id = e.id AND o.status <> 'cancelled'
JOIN sales_order_lines l ON l.order_id = o.id
GROUP BY 1,2,3,4 ORDER BY revenue DESC;""")

    # --------------------------------------------------------- machine units
    v.append("""
CREATE VIEW v_machine_unit_profitability AS
SELECT m.id AS machine_unit_id, m.unit_no, m.manufacturer, m.model, m.serial_no,
       m.year_built, m.condition_grade, m.control_system, p.category AS machine_category,
       v.name AS source_vendor, m.source_type,
       m.acquisition_date, m.sale_date, m.days_in_stock,
       m.acquisition_cost_base, m.transport_in_cost, m.refurb_cost, m.other_cost,
       m.landed_cost, m.sale_price_base,
       m.gross_profit, m.gross_margin_pct, m.status,
       c.name AS customer, c.country AS customer_country
FROM machine_units m
JOIN products p ON p.id = m.product_id
LEFT JOIN vendors v ON v.id = m.vendor_id
LEFT JOIN sales_orders o ON o.id = m.sale_order_id
LEFT JOIN customers c ON c.id = o.customer_id;""")

    v.append(f"""
CREATE VIEW v_machine_stock AS
SELECT m.id AS machine_unit_id, m.unit_no, m.manufacturer, m.model, m.year_built,
       p.category AS machine_category, m.condition_grade, m.status,
       w.name AS warehouse, m.acquisition_date, m.landed_cost, m.asking_price,
       (DATE '{today}' - m.acquisition_date)                     AS days_on_yard,
       CASE WHEN (DATE '{today}' - m.acquisition_date) <= 90  THEN '0-90 days'
            WHEN (DATE '{today}' - m.acquisition_date) <= 180 THEN '91-180 days'
            WHEN (DATE '{today}' - m.acquisition_date) <= 365 THEN '181-365 days'
            ELSE '365+ days' END                                 AS aging_bucket
FROM machine_units m
JOIN products p ON p.id = m.product_id
LEFT JOIN warehouses w ON w.id = m.warehouse_id
WHERE m.status <> 'sold';""")

    v.append("""
CREATE VIEW v_refurbishment_cost AS
SELECT date_trunc('month', j.start_date)::date AS month, j.work_type,
       count(*) AS jobs, sum(j.labor_hours) AS labor_hours,
       sum(j.labor_cost) AS labor_cost, sum(j.parts_cost) AS parts_cost,
       sum(j.external_cost) AS external_cost, sum(j.total_cost) AS total_cost
FROM refurbishment_jobs j GROUP BY 1,2 ORDER BY 1,2;""")

    v.append("""
CREATE VIEW v_inventory_valuation AS
SELECT 'machine' AS stock_class, p.category AS category,
       count(*)::numeric AS on_hand_qty, sum(m.landed_cost) AS value
FROM machine_units m JOIN products p ON p.id = m.product_id
WHERE m.status <> 'sold'
GROUP BY 1,2
UNION ALL
SELECT 'parts_and_tooling', p.category,
       sum(CASE WHEN s.move_type = 'out' THEN -s.qty ELSE s.qty END),
       sum(CASE WHEN s.move_type = 'out' THEN -s.value_base ELSE s.value_base END)
FROM stock_moves s JOIN products p ON p.id = s.item_id
WHERE s.item_type = 'product'
GROUP BY 1,2;""")

    # ------------------------------------------------------------- P&L core
    v.append(f"""
CREATE VIEW v_pnl_monthly AS
WITH spine AS (
    SELECT generate_series(date_trunc('month', (SELECT min(order_date) FROM sales_orders)),
                           date_trunc('month', DATE '{today}'), interval '1 month')::date AS month
),
rev AS (
    SELECT date_trunc('month', o.order_date)::date AS month,
           sum(l.line_subtotal_base) AS revenue,
           sum(l.line_cogs_base)     AS cogs,
           sum(CASE WHEN l.line_type = 'machine'   THEN l.line_subtotal_base ELSE 0 END) AS machine_revenue,
           sum(CASE WHEN l.line_type = 'accessory' THEN l.line_subtotal_base ELSE 0 END) AS accessory_revenue,
           sum(CASE WHEN l.line_type = 'service'   THEN l.line_subtotal_base ELSE 0 END) AS service_revenue
    FROM sales_orders o JOIN sales_order_lines l ON l.order_id = o.id
    WHERE o.status <> 'cancelled'
    GROUP BY 1
),
ret AS (
    -- refund_amount_base is EUR; restocking_fee is in the document currency, so
    -- it is netted off separately rather than mixed into the same sum
    SELECT date_trunc('month', return_date)::date AS month,
           sum(refund_amount_base) AS returns_and_allowances
    FROM returns WHERE status <> 'Rejected' GROUP BY 1
),
ex AS (
    SELECT date_trunc('month', expense_date)::date AS month,
           sum(CASE WHEN source IN {OPERATING_SOURCES} THEN amount_base ELSE 0 END) AS operating_expenses,
           sum(CASE WHEN source = 'payroll'      THEN amount_base ELSE 0 END) AS personnel_cost,
           sum(CASE WHEN source = 'depreciation' THEN amount_base ELSE 0 END) AS depreciation,
           sum(CASE WHEN source = 'logistics'    THEN amount_base ELSE 0 END) AS logistics_cost,
           sum(CASE WHEN source = 'purchased'    THEN amount_base ELSE 0 END) AS other_operating_cost,
           sum(CASE WHEN source = 'financing'    THEN amount_base ELSE 0 END) AS financing_cost,
           sum(CASE WHEN source = 'tax'          THEN amount_base ELSE 0 END) AS income_tax
    FROM expenses GROUP BY 1
),
fx AS (
    SELECT date_trunc('month', payment_date)::date AS month,
           sum(fx_gain_loss) AS fx_gain_loss
    FROM payments GROUP BY 1
)
SELECT s.month,
       coalesce(rev.revenue, 0)                       AS revenue,
       coalesce(rev.machine_revenue, 0)               AS machine_revenue,
       coalesce(rev.accessory_revenue, 0)             AS accessory_revenue,
       coalesce(rev.service_revenue, 0)               AS service_revenue,
       coalesce(ret.returns_and_allowances, 0)        AS returns_and_allowances,
       coalesce(rev.revenue, 0) - coalesce(ret.returns_and_allowances, 0) AS net_revenue,
       coalesce(rev.cogs, 0)                          AS cogs,
       coalesce(rev.revenue, 0) - coalesce(ret.returns_and_allowances, 0)
           - coalesce(rev.cogs, 0)                    AS gross_profit,
       round(100 * (coalesce(rev.revenue,0) - coalesce(ret.returns_and_allowances,0)
             - coalesce(rev.cogs,0)) / NULLIF(coalesce(rev.revenue,0)
             - coalesce(ret.returns_and_allowances,0), 0), 2) AS gross_margin_pct,
       coalesce(ex.personnel_cost, 0)                 AS personnel_cost,
       coalesce(ex.logistics_cost, 0)                 AS logistics_cost,
       coalesce(ex.other_operating_cost, 0)           AS other_operating_cost,
       coalesce(ex.depreciation, 0)                   AS depreciation,
       coalesce(ex.operating_expenses, 0)             AS operating_expenses,
       coalesce(rev.revenue, 0) - coalesce(ret.returns_and_allowances, 0)
           - coalesce(rev.cogs, 0) - coalesce(ex.operating_expenses, 0) AS operating_profit,
       coalesce(fx.fx_gain_loss, 0)                   AS fx_gain_loss,
       coalesce(ex.financing_cost, 0)                 AS financing_cost,
       coalesce(rev.revenue, 0) - coalesce(ret.returns_and_allowances, 0)
           - coalesce(rev.cogs, 0) - coalesce(ex.operating_expenses, 0)
           - coalesce(ex.financing_cost, 0) + coalesce(fx.fx_gain_loss, 0) AS profit_before_tax,
       coalesce(ex.income_tax, 0)                     AS income_tax,
       coalesce(rev.revenue, 0) - coalesce(ret.returns_and_allowances, 0)
           - coalesce(rev.cogs, 0) - coalesce(ex.operating_expenses, 0)
           - coalesce(ex.financing_cost, 0) + coalesce(fx.fx_gain_loss, 0)
           - coalesce(ex.income_tax, 0)               AS net_profit
FROM spine s
LEFT JOIN rev ON rev.month = s.month
LEFT JOIN ret ON ret.month = s.month
LEFT JOIN ex  ON ex.month  = s.month
LEFT JOIN fx  ON fx.month  = s.month
ORDER BY 1;""")

    v.append("""
CREATE VIEW v_pnl_yearly AS
SELECT extract(year FROM month)::int AS year,
       sum(revenue) AS revenue, sum(machine_revenue) AS machine_revenue,
       sum(accessory_revenue) AS accessory_revenue, sum(service_revenue) AS service_revenue,
       sum(returns_and_allowances) AS returns_and_allowances,
       sum(net_revenue) AS net_revenue, sum(cogs) AS cogs,
       sum(gross_profit) AS gross_profit,
       round(100 * sum(gross_profit) / NULLIF(sum(net_revenue), 0), 2) AS gross_margin_pct,
       sum(personnel_cost) AS personnel_cost, sum(logistics_cost) AS logistics_cost,
       sum(other_operating_cost) AS other_operating_cost, sum(depreciation) AS depreciation,
       sum(operating_expenses) AS operating_expenses,
       sum(operating_profit) AS operating_profit,
       round(100 * sum(operating_profit) / NULLIF(sum(net_revenue), 0), 2) AS operating_margin_pct,
       sum(fx_gain_loss) AS fx_gain_loss, sum(financing_cost) AS financing_cost,
       sum(profit_before_tax) AS profit_before_tax, sum(income_tax) AS income_tax,
       sum(net_profit) AS net_profit,
       round(100 * sum(net_profit) / NULLIF(sum(net_revenue), 0), 2) AS net_margin_pct
FROM v_pnl_monthly GROUP BY 1 ORDER BY 1;""")

    # ------------------------------------------------------------- cost detail
    v.append("""
CREATE VIEW v_opex_by_category AS
SELECT date_trunc('month', e.expense_date)::date AS month,
       extract(year FROM e.expense_date)::int    AS year,
       ec.expense_group, ec.code AS category_code, ec.name AS category,
       ec.account_code, e.source,
       count(*) AS entries, sum(e.amount_base) AS amount
FROM expenses e JOIN expense_categories ec ON ec.id = e.category_id
GROUP BY 1,2,3,4,5,6,7 ORDER BY 1, amount DESC;""")

    v.append("""
CREATE VIEW v_opex_by_department AS
SELECT extract(year FROM e.expense_date)::int AS year, d.name AS department, d.cost_center,
       ec.expense_group, sum(e.amount_base) AS amount
FROM expenses e
JOIN expense_categories ec ON ec.id = e.category_id
LEFT JOIN departments d ON d.id = e.department_id
GROUP BY 1,2,3,4 ORDER BY 1, amount DESC;""")

    v.append("""
CREATE VIEW v_budget_vs_actual AS
SELECT b.fiscal_year, b.period_month, d.name AS department, ec.name AS category,
       ec.expense_group,
       sum(b.budget_amount)                        AS budget,
       coalesce(sum(a.actual), 0)                  AS actual,
       coalesce(sum(a.actual), 0) - sum(b.budget_amount) AS variance,
       round(100 * (coalesce(sum(a.actual), 0) - sum(b.budget_amount))
             / NULLIF(sum(b.budget_amount), 0), 2) AS variance_pct
FROM budgets b
JOIN expense_categories ec ON ec.id = b.expense_category_id
LEFT JOIN departments d ON d.id = b.department_id
LEFT JOIN (
    SELECT period_year, period_month, department_id, category_id,
           sum(amount_base) AS actual
    FROM expenses GROUP BY 1,2,3,4
) a ON a.period_year = b.fiscal_year AND a.period_month = b.period_month
   AND a.category_id = b.expense_category_id
   AND a.department_id IS NOT DISTINCT FROM b.department_id
GROUP BY 1,2,3,4,5 ORDER BY 1,2, budget DESC;""")

    v.append("""
CREATE VIEW v_payroll_monthly AS
SELECT pi.period_date AS month, pi.country, d.name AS department,
       count(*) AS employees,
       sum(pi.gross_pay / pi.fx_rate)       AS gross_pay_eur,
       sum(pi.bonus / pi.fx_rate)           AS bonus_eur,
       sum(pi.employer_social / pi.fx_rate) AS employer_social_eur,
       sum(pi.net_pay / pi.fx_rate)         AS net_pay_eur,
       sum(pi.employer_cost_base)           AS employer_cost_eur,
       sum(pi.gross_pay)                    AS gross_pay_local,
       sum(pi.employer_cost)                AS employer_cost_local
FROM payroll_items pi
JOIN employees e ON e.id = pi.employee_id
JOIN departments d ON d.id = e.department_id
GROUP BY 1,2,3 ORDER BY 1,2,3;""")

    v.append("""
CREATE VIEW v_headcount AS
SELECT d.name AS department, e.country, e.work_location, e.employment_type, e.currency,
       count(*) FILTER (WHERE e.is_active)        AS active_headcount,
       count(*)                                   AS total_ever,
       round(avg(e.annual_gross) FILTER (WHERE e.is_active), 0) AS avg_annual_gross_local,
       round(avg(a.employer_cost_eur), 0)         AS avg_employer_cost_eur_12m
FROM employees e
JOIN departments d ON d.id = e.department_id
LEFT JOIN (
    SELECT employee_id, sum(employer_cost_base) AS employer_cost_eur
    FROM payroll_items
    WHERE period_date > (SELECT max(period_date) FROM payroll_items) - interval '12 months'
    GROUP BY 1
) a ON a.employee_id = e.id
GROUP BY 1,2,3,4,5 ORDER BY 1;""")

    v.append("""
CREATE VIEW v_fixed_asset_register AS
SELECT a.asset_no, a.name, a.category, d.name AS department, a.acquisition_date,
       a.acquisition_cost, a.useful_life_years, a.method,
       a.accumulated_depreciation, a.net_book_value, a.status
FROM fixed_assets a LEFT JOIN departments d ON d.id = a.department_id
ORDER BY a.acquisition_date;""")

    # ------------------------------------------------------------ receivables
    v.append(f"""
CREATE VIEW v_ar_aging AS
SELECT i.id AS invoice_id, i.invoice_no, i.customer_id, c.name AS customer, c.country,
       i.currency, i.total, i.total_base, i.balance, i.balance_base, i.due_date,
       (DATE '{today}' - i.due_date) AS days_overdue,
       CASE WHEN i.balance <= 0 THEN 'paid'
            WHEN i.due_date >= DATE '{today}' THEN 'current'
            WHEN i.due_date >= DATE '{today}' - 30 THEN '1-30'
            WHEN i.due_date >= DATE '{today}' - 60 THEN '31-60'
            WHEN i.due_date >= DATE '{today}' - 90 THEN '61-90'
            ELSE '90+' END AS aging_bucket
FROM invoices i JOIN customers c ON c.id = i.customer_id
WHERE i.balance > 0;""")

    v.append(f"""
CREATE VIEW v_ap_aging AS
SELECT b.id AS vendor_invoice_id, b.bill_no, b.vendor_id, v.name AS vendor,
       v.country, b.spend_category, b.currency, b.total, b.total_base, b.balance,
       b.due_date, (DATE '{today}' - b.due_date) AS days_overdue,
       CASE WHEN b.balance <= 0 THEN 'paid'
            WHEN b.due_date >= DATE '{today}' THEN 'current'
            WHEN b.due_date >= DATE '{today}' - 30 THEN '1-30'
            WHEN b.due_date >= DATE '{today}' - 60 THEN '31-60'
            ELSE '60+' END AS aging_bucket
FROM vendor_invoices b JOIN vendors v ON v.id = b.vendor_id
WHERE b.balance > 0;""")

    v.append("""
CREATE VIEW v_cash_flow_monthly AS
SELECT date_trunc('month', txn_date)::date AS month,
       sum(CASE WHEN direction = 'in'  THEN amount_base ELSE 0 END) AS cash_in,
       sum(CASE WHEN direction = 'out' THEN amount_base ELSE 0 END) AS cash_out,
       sum(CASE WHEN direction = 'in'  THEN amount_base ELSE -amount_base END) AS net_cash_flow,
       min(balance_after) AS min_balance, max(balance_after) AS max_balance
FROM bank_transactions GROUP BY 1 ORDER BY 1;""")

    v.append("""
CREATE VIEW v_trial_balance AS
SELECT g.account_code, coa.account_name, coa.account_type, coa.pnl_section,
       extract(year FROM g.entry_date)::int AS year,
       sum(g.debit_base) AS total_debit, sum(g.credit_base) AS total_credit,
       sum(g.debit_base) - sum(g.credit_base) AS balance
FROM gl_entries g
LEFT JOIN chart_of_accounts coa ON coa.account_code = g.account_code
GROUP BY 1,2,3,4,5 ORDER BY 5, 1;""")

    # ----------------------------------------------------------- CRM & export
    v.append("""
CREATE VIEW v_sales_pipeline AS
SELECT date_trunc('month', o.created_date)::date AS month, o.stage, o.status,
       o.machine_category, e.full_name AS owner,
       count(*) AS opportunities, sum(o.amount_base) AS pipeline_value,
       sum(o.amount_base * o.probability_pct / 100.0) AS weighted_value
FROM opportunities o LEFT JOIN employees e ON e.id = o.owner_id
GROUP BY 1,2,3,4,5 ORDER BY 1;""")

    v.append("""
CREATE VIEW v_win_rate AS
SELECT date_trunc('month', coalesce(close_date, created_date))::date AS month,
       count(*) FILTER (WHERE status = 'won')  AS won,
       count(*) FILTER (WHERE status = 'lost') AS lost,
       round(100.0 * count(*) FILTER (WHERE status = 'won')
             / NULLIF(count(*) FILTER (WHERE status IN ('won','lost')), 0), 2) AS win_rate_pct,
       sum(amount_base) FILTER (WHERE status = 'won')  AS won_value,
       sum(amount_base) FILTER (WHERE status = 'lost') AS lost_value
FROM opportunities GROUP BY 1 ORDER BY 1;""")

    v.append("""
CREATE VIEW v_logistics_cost AS
SELECT date_trunc('month', s.ship_date)::date AS month, s.mode, s.incoterm,
       s.dest_country,
       CASE WHEN NOT s.is_export THEN 'Domestic'
            WHEN s.is_intra_eu THEN 'Intra-EU'
            ELSE 'Non-EU export' END AS trade_lane,
       count(*) AS shipments, sum(s.gross_weight_kg) AS weight_kg,
       sum(s.freight_cost) AS freight_cost, sum(s.insurance_cost) AS insurance_cost,
       sum(s.packing_cost) AS packing_cost, sum(s.handling_cost) AS handling_cost,
       sum(s.total_logistics_cost) AS total_cost,
       sum(s.billed_to_customer) AS recharged,
       sum(s.total_logistics_cost - s.billed_to_customer) AS net_cost,
       round(avg(s.transit_days), 1) AS avg_transit_days
FROM shipments s GROUP BY 1,2,3,4,5 ORDER BY 1;""")

    v.append("""
CREATE VIEW v_customs_summary AS
SELECT extract(year FROM cd.decl_date)::int AS year, cd.dest_country, cd.document_type,
       count(*) AS declarations, sum(cd.customs_value_base) AS declared_value,
       sum(cd.duty_amount) AS duty, sum(cd.broker_fee) AS broker_fees
FROM customs_declarations cd GROUP BY 1,2,3 ORDER BY 1, declared_value DESC;""")

    v.append("""
CREATE VIEW v_service_performance AS
SELECT date_trunc('month', sj.completion_date)::date AS month, sj.job_type, sj.country,
       sj.is_warranty,
       count(*) AS jobs, sum(sj.labor_hours) AS labor_hours,
       sum(sj.total_cost) AS cost, sum(sj.billable_base) AS billed,
       sum(sj.billable_base - sj.total_cost) AS margin,
       round(avg(sj.response_days), 2) AS avg_response_days,
       round(avg(sj.satisfaction_score), 2) AS avg_satisfaction
FROM service_jobs sj WHERE sj.completion_date IS NOT NULL
GROUP BY 1,2,3,4 ORDER BY 1;""")

    v.append("""
CREATE VIEW v_fx_exposure AS
SELECT i.currency, extract(year FROM i.invoice_date)::int AS year,
       count(*) AS invoices, sum(i.total) AS total_local, sum(i.total_base) AS total_eur,
       sum(i.balance_base) AS open_ar_eur,
       coalesce(sum(p.fx_gain_loss), 0) AS realised_fx_gain_loss
FROM invoices i LEFT JOIN payments p ON p.invoice_id = i.id
GROUP BY 1,2 ORDER BY 2, total_eur DESC;""")

    return "\n".join(v)
