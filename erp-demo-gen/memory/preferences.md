# User defaults for erp-demo-gen

These are the user's recurring preferences. Apply them as defaults during intake
so the user can answer fast (they can always override per run). Update this file
when the user expresses a new lasting preference.

- **Locale / currency**: English / Global, USD ($).
- **Purpose**: fresh fictional databases to feed an LLM-driven data-analysis
  product during demos and presales. Data should look real and meaningful.
- **Delivery**: local Postgres via Docker (connection string handed back).
- **Default span**: ask each time (user typically picks 5–15 years).
- **Default seed**: 42 unless the user wants a different/random one.
- **Naming style**: realistic, on-industry company and product names. Real
  manufacturer/model names where the industry has them (the user asks for this
  explicitly), and regionally correct legal forms and person names.
- **Completeness**: the user wants full financial analysis out of the box —
  revenue, COGS, gross profit, every operating cost (rent, utilities, staff
  catering, salaries, marketing, freight), financing and tax, down to net
  profit. Assume "any ERP with every module" unless told otherwise.
- **Currency**: base currency should follow the company's country, with
  multi-currency trading when it exports. Always store an EUR/base amount
  alongside the document amount.

## Open tuning questions to refine over time
- Preferred default company size band when the user doesn't specify? (currently "medium")
- Any industries the user demos most? (track in changelog)

## Known preferences from past runs
- **Language follows the company's country.** For a Turkish company the user
  wants Turkish content throughout — product names, company names, departments,
  job titles, chart of accounts, statuses, notes. Only counterparties outside
  Türkiye get names and legal forms from their own country. Table and column
  names stay English (the engine's contract).
- The user asks for full production depth on manufacturing demos: work orders
  (iş emri) with operation-level detail and notes, real employee records with
  their details, orders and sales — "all of it".
- Revenue should vary year to year (up AND down), not compound smoothly — use
  `spec.revenue_by_year`.
- The final year is generated as a year-to-date partial (`spec.end_month`), so
  the newest data looks like a live system.
- Cost detail matters as much as revenue detail: itemise bills, food, salaries.
