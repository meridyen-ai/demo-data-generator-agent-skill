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
- psql emits a `SET` command tag on stdout; never enforce read-only via a `SET`
  statement before a `--csv` query — use the `default_transaction_read_only` session
  option instead (handled by the engine).
