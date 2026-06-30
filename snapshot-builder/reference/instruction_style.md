# How to write great snapshot instructions (PostgreSQL)

The `instructions` text is what makes the platform's query-writer accurate. There
are two layers: **global** (top-level `instructions`, mirrored into
`_connection_meta`) and **per-table** (`selected_schema[table].instructions`).
Every recipe you write must be **verified by executing it** (full self-test).

Golden rules:
- **Be concrete and verified.** Give exact column names, exact SQL expressions,
  and **real distinct values** you discovered via probing — never guesses.
- **Route to the FEWEST tables** that answer a question (usually ONE fact table).
- **Postgres dialect**: `COALESCE` (not `ISNULL`), `EXTRACT(YEAR FROM d)`,
  `ILIKE`/`LIKE`, no `N'...'` literals, `::date`/`::numeric` casts.

---

## Global `instructions` — template

```
=== CONNECTION INSTRUCTIONS ===
[ENRICHMENT ONLY]
<one line: what this database is and its grain — e.g. "Fictional discrete-
manufacturing ERP. One row per order line / invoice / stock move ...">.
Pick the FEWEST tables that answer the question — usually ONE fact table.

TABLE ROUTING (question intent -> table):
- sales / revenue / orders / customers / "satış"        -> public.sales_orders (+ sales_order_lines for product/qty detail)
- invoices / AR / receivable / overdue / aging / paid   -> public.invoices (+ payments)
- purchasing / suppliers / spend / "alış"               -> public.purchase_orders (+ purchase_order_lines)
- production / work orders / output / scrap             -> public.production_orders (+ production_consumption)
- inventory / stock on hand / moves / valuation         -> public.stock_moves
- machine / IoT / uptime / temperature                  -> public.iot_readings
- general ledger / debit / credit / account             -> public.gl_entries
- cash / bank / payments in-out                         -> public.bank_transactions

ROUTING HINTS (pick the RIGHT table, not more):
- "revenue/sales total" -> sales_orders (header) for order-level totals; join
  sales_order_lines only when the question is per-product / per-qty.
- NET vs GROSS: revenue = subtotal - discount (excl. tax). "with tax / collected"
  uses total. State which the metric uses.
- Exclude cancelled orders for revenue (status <> 'cancelled').
- Returns are a SEPARATE table (returns); don't subtract them unless asked.
- The date column differs per table — name it explicitly (sales_orders.order_date,
  invoices.invoice_date, purchase_orders.order_date, stock_moves.move_date, ...).
[/ENRICHMENT ONLY]
[SQL GEN]
GLOBAL SQL RULES (PostgreSQL):
- Wrap every summed numeric in COALESCE(col,0) so NULLs don't void the SUM.
- Totals: return a single scalar aliased AS t -> SELECT SUM(COALESCE(<amt>,0)) AS t FROM ...
- Date filters: EXTRACT(YEAR FROM <date>)=2025; MONTH via EXTRACT(MONTH ...);
  ranges: <date> >= DATE '2024-01-01' AND <date> < DATE '2026-01-01'.
- DATA SPANS <min>..<max> (from probing). Apply a filter only when the question
  names a period; otherwise aggregate all rows.
- Text matching: prefer ILIKE '%fragment%' over exact equality for names/categories.
- Money columns are NUMERIC; round only for display (ROUND(x,2)).
- Do the aggregation DIRECTLY in one query; a dimension-only probe that omits the
  amount column is NOT evidence the metric is missing.
[/SQL GEN]
```

Keep routing lines aligned to the **tables that are actually selected** (some
industries omit production/iot). Only mention tables present in `selected_schema`.

---

## Per-table `instructions` — template

```
<1-line business description and grain>.
METRIC:
- <name> = <exact Postgres expression>.  e.g.
  net revenue = SUM(COALESCE(subtotal,0) - COALESCE(discount,0)) (exclude status='cancelled')
  gross/collected = SUM(COALESCE(total,0))
  margin = SUM(COALESCE(margin,0))
DIMENSIONS:
- <col> (group/filter) — values: <real distinct values discovered>.
  e.g. status one of ('completed','open','cancelled'); channel one of (...).
- date column = <order_date>. customer via customer_id -> customers.name.
FILTERS / GOTCHAS:
- <e.g. exclude cancelled for revenue; join sales_order_lines for per-product>.
```

Write one METRIC entry per important measure, and **back each with a runnable
query** recorded in `out/<db>/metric_tests.json`:

```jsonc
[
  { "table": "public.sales_orders", "name": "net revenue 2026",
    "sql": "SELECT SUM(COALESCE(subtotal,0)-COALESCE(discount,0)) AS t FROM sales_orders WHERE status<>'cancelled' AND EXTRACT(YEAR FROM order_date)=2026" }
]
```

`selftest` runs every entry; fix any that error or return a wrong/empty scalar,
then re-run until clean. The self-tested SQL IS the evidence the recipe is right.

---

## `is_hidden` guidance
Hide technical/surrogate columns (`id`, `*_id`, `*_no`, internal codes, line ids)
so the UI stays clean — but keep them `selected:true` so joins/filters still work.
Keep business columns (names, dates, amounts, statuses, categories) visible.

## `prompts_data` (optional)
A few realistic business questions the snapshot should nail, e.g.
"What was net revenue in 2026?", "Top 5 customers by revenue", "Total open AR",
"Production scrap rate by month". Keep them answerable by the routing above.
