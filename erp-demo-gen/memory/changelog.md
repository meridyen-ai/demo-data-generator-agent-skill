# Run & learning changelog

`build` auto-appends one line per generated database (date · industry · company ·
years · rows · checks · seed). Below that, keep dated notes on what was tuned and
why, so future runs get better. Newest notes first.

## Tuning notes

### 2026-08-29 — new industry `contract_machining` (talaşlı imalat / fason metal parça)
Built for Alkan Precision (Gaziantep 2. OSB, 30.000 m², ~500 mn TL ciro, TRY base
with EUR/USD reporting). The user asked for Turkish content throughout — product,
company, department, account and status values are Turkish; only companies outside
Türkiye carry foreign names and legal forms. New engine surfaces: `ddl_mfg.py`
(9 new tables + multi-currency/manufacturing columns, installed only when
`tables.json` sets `"ddl_extension": "mfg"`), `gen_contract.py`, `views_mfg.py`
(50+ Turkish analytics views), `validate._contract_checks` (80 checks).

Things that had to be fixed to make the data believable — worth remembering:

- **FX anchors are ANNUAL AVERAGES.** Interpolating them from year-start pushes
  each year's mean toward the next year's rate; EUR-denominated revenue came out
  ~25% low. Anchor them at 1 July and interpolate between mid-years.
- **Store the rate as base-per-unit (53.40 TL/EUR), not unit-per-base (0.0187).**
  At four decimals the latter loses ~0.1% precision, so `amount_eur` no longer
  reconciled with `amount_base * fx_rate`. Also flipped `_fmt` to 6 decimals.
- **Price and cost in a hard-currency reference.** In a 40%-inflation economy a
  static local-currency price makes early years look 3x higher in units.
- **COGS must be direct-only when overhead sits in `expenses`.** Production-
  department payroll and machine depreciation are absorbed in COGS *or* expensed,
  never both. Direct operators are identified by `job_family = 'Üretim'`.
- **Aggregate operating expenses by expense_group, not by `source`.** Bank fees
  and stamp duty are `source = 'purchased'` yet belong to financing/tax; a
  source-based sum double-counted them.
- **Derive cycle times from the part's machine-cost allocation**, so total
  machine hours and the machine fleet agree and capacity analysis is meaningful.
- **`lot_min/lot_max` are ANNUAL volumes**; OEM customers draw them down through
  weekly call-offs (`call_off_divisor`). Used directly as order quantities they
  produced EUR 40k average orders and only ~160 orders a year.
- **OEE needs real downtime and performance loss.** Without `downtime_chance` /
  `downtime_share` / `performance_loss_factor` every work centre ran at 95%+ OEE.
- **Capacity must stay under 100%.** Adding machines at the bottleneck beats
  lowering operation time weights, which just shifts the load elsewhere.
- **ABC class has to be derived from actual revenue**, else the largest customer
  shows up as class C.
- **Opening stock must also absorb the period deficit** — one cancelled work
  order was enough to drive a product's on-hand quantity negative.
- **Headcount drives the P&L.** 11 mn EUR of revenue supports ~130 people
  (~85k EUR/head); the first draft's 220 people put payroll at 41% of revenue.

### 2026-08-27 — new industry `machinery_dealer` (used machine-tool dealer)
Built for Demirci Machine Tools GmbH (Hamburg). The generic wholesale path could
not express the business, so the engine gained a dedicated generator plus a set
of modules every "full ERP" demo needs. Things that had to be fixed to make the
data believable — worth remembering for any similar build:

- **Serialized stock.** Used machines are unique units with their own
  acquisition, inbound transport and refurbishment cost. Per-SKU costing makes
  machine margin analysis meaningless. `machine_units` + `refurbishment_jobs`.
- **Order archetypes.** A machine deal and a parts order cannot share one value
  distribution — mixing them produced orders for four coordinate measuring
  machines. Quantity is now chosen from the item's price band (`_acc_qty`).
- **Replenishment must match consumption in UNITS, not value.** Buying to a
  spend target while picking products uniformly drove stock-on-hand negative.
  Purchase orders are now built from the quantities actually sold, plus an
  opening balance. Guarded by the "No negative stock on hand" check.
- **Revenue curve is authored, not compounded.** `spec.revenue_by_year` lets the
  history rise and fall (COVID collapse, used-machine scarcity boom). A
  per-month carry-over of the overshoot keeps annual totals within ~0.3%.
- **Cancelled orders must not count toward the revenue target**, or every year
  lands ~3% light.
- **Multi-currency needs wider numerics.** A EUR 340k machine priced in forint
  overflows NUMERIC(12,4). See `ddl_ext.WIDEN`.
- **Legal form has to match the country.** Synthesized company names now get
  their suffix after the country is chosen (`locales.company_suffix`), otherwise
  the data is full of Turkish firms called "S.L.".
- **Views must use the generator's own `_today()`.** With a partial final year
  (`spec.end_month`), a Dec-31 "today" marks every not-yet-due invoice overdue.
- **One `expenses` table for everything below gross profit**, with a `source`
  column (purchased / payroll / depreciation / logistics / financing / tax). A
  single table is far easier for an LLM query-writer than a UNION across five.
  The P&L view now reconciles to the ledger to the cent — enforced by a check.

- (older note) none

## Run log
<!-- build auto-appends run records here -->
- 2026-08-27 · machinery_dealer · Demirci Machine Tools GmbH · 10y · 502,449 rows · checks 46/46 · seed 42
- 2026-08-27 · machinery_dealer · Demirci Machine Tools GmbH · 10y · 502,389 rows · checks 46/46 · seed 42
- 2026-08-29 · contract_machining · Alkan Precision · 5y · 691,122 rows · checks 77/80 · seed 42
- 2026-08-29 · contract_machining · Alkan Precision · 5y · 691,472 rows · checks 79/80 · seed 42
- 2026-08-29 · contract_machining · Alkan Precision · 5y · 691,472 rows · checks 80/80 · seed 42
- 2026-08-29 · contract_machining · Alkan Precision · 5y · 691,654 rows · checks 80/80 · seed 42
- 2026-08-29 · contract_machining · Alkan Precision · 5y · 691,626 rows · checks 80/80 · seed 42
- 2026-08-29 · contract_machining · Alkan Precision · 5y · 691,713 rows · checks 80/80 · seed 42
