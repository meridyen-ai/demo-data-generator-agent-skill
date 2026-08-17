# Instruction patterns that work (learning surface)

Record recipe patterns that self-tested well and gotchas worth reusing across runs.
Newest first.

## ERP demo (erp-demo-gen Postgres) — verified patterns
- **Net vs gross revenue**: net = `SUM(COALESCE(subtotal,0)-COALESCE(discount,0))`
  (exclude `status='cancelled'`); gross/collected = `SUM(COALESCE(total,0))` (incl tax).
  Always state which a metric uses — this is the most common ambiguity.
- **AR / invoices**: `amount_paid + balance = total`; open AR = `SUM(balance)`;
  status in ('paid','open','overdue'); aging compares `due_date` to the period end.
- **Inventory on-hand**: `SUM(CASE WHEN move_type='out' THEN -qty ELSE qty END)` from
  `stock_moves`; valuation multiplies by `unit_cost`, grouped by `item_id`.
- **Production scrap rate**: `100*SUM(scrap_qty)/NULLIF(SUM(planned_qty),0)`.
- **GL** is balanced overall (`SUM(debit)=SUM(credit)`); net by account = debit-credit.
- **Per-table date columns differ** — name the right one explicitly (order_date,
  invoice_date, move_date, start_date, reading_ts, entry_date, txn_date). Routing by
  the metric noun, not the leading topic word, prevents wrong-table answers.
- **IoT** is bounded to a recent window, not full history — say so.

## Gotchas
- **erp_test_mfg reconciliations (verified):** `invoice_lines.line_total` sums exactly
  to `invoices.total` (GROSS, tax-inclusive), NOT to subtotal — label it gross.
  `stock_moves` sign: `move_type='out'` is negative, `in`/`production` positive
  (on-hand = SUM(CASE WHEN move_type='out' THEN -qty ELSE qty END)). `purchase_order_lines`
  are all `item_type='raw_material'`; `received_qty <= qty` (partial receipts).
  IoT window is 2026-07-05..2026-12-31 only; the four metrics share one `value` column
  so always filter `metric=...` before aggregating. Prefer the v_* views (v_monthly_sales,
  v_product_profitability, v_ar_aging, v_inventory_valuation) when a question matches
  their grain — already reconciled.
- **erp_sahb_finance:** `ecl_staging` is a 9-quarter time series — pin the latest
  `report_date` for all ECL/exposure metrics; IFRS-9 stage 3 = NPL; `v_portfolio_report`
  is the clean current-portfolio single source; aging/DPD buckets live in `v_receivables_report`.
- psql emits a `SET` command tag on stdout; never enforce read-only via a `SET`
  statement before a `--csv` query — use the `default_transaction_read_only` session
  option instead (handled by the engine).
