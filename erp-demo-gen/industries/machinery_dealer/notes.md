# Used machine-tool dealer — tuning notes

A trading business, not a manufacturer. What makes the data believable:

- **Thin blended margin (~20%).** Machines carry ~16-17%, tooling/parts ~31%,
  service ~52%. Most of the revenue and almost none of the margin percentage
  comes from machines.
- **Serialized stock.** Every machine is one `machine_units` row with its own
  acquisition cost, inbound transport, refurbishment spend and landed cost.
  COGS is per-unit; two units of the same model rarely cost the same.
- **Stock takes months to turn.** `days_in_stock` is lognormal around ~105 days
  with a long tail; a chunk of the yard is aged 365+ days and that is normal.
- **Revenue does not compound smoothly.** Author `revenue_by_year` in the spec:
  capex-driven demand crashes in a downturn (2020) and spikes when used-machine
  supply is scarce (2021-22).
- **August is dead** (European industrial holidays); September-November is the
  strongest run (post-EMO/AMB, year-end capex).
- **Multi-currency is the norm.** EUR base; Turkish, UK, Swiss, Polish, Czech,
  Hungarian, Romanian and Nordic customers often invoice in their own currency.
  Aggregate on the `*_base` columns or the numbers are meaningless.
- **Two payrolls.** German staff on EUR contracts, Türkiye workshop staff on TRY
  contracts whose nominal cost tracks the lira while the EUR cost stays flat.
- **Export paperwork matters.** EU-Türkiye trade moves under the customs union,
  so A.TR movement certificates dominate that lane; other exports use EX-A or
  EUR.1.

## Seed guidance for the LLM
- `machines`: real manufacturer + model pairs (DMG MORI, Mazak, Okuma, Haas,
  Doosan/DN Solutions, Hermle, Studer, Trumpf, TOS, Weiler ...) with a used
  acquisition cost range, build-year range, weight and HS code.
- `accessories`: go wide. Workholding, toolholding, cutting tools, metrology,
  probing, coolant and chip handling, controls and retrofit parts, spindles,
  automation, rigging, consumables, PPE, software and services. Variety here is
  what makes category analysis interesting.
- `expense_categories`: everything below gross profit, including staff catering,
  utilities, trade-fair marketing, floor-plan interest and income tax.
