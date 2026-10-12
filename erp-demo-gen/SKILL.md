---
name: erp-demo-gen
description: Generate a realistic fictional ERP-style Postgres database for demos/presales. Use when the user wants demo company data, fake/sample ERP data, an analytics demo database, or asks to "generate a fictional company / demo database" for sales, purchases, invoices, production, inventory, IoT, etc. Asks a few intake questions (industry, years, company size), then builds and loads a per-industry schema into local Docker Postgres.
---

# erp-demo-gen

Generates a fully-loaded, internally-consistent fictional ERP database in local
Docker Postgres. The qualitative seed data (company identity, product/customer/
vendor names) is authored by you (the LLM); the high-volume transactional rows
are produced by a deterministic Python engine that guarantees valid foreign keys,
reconciling totals, seasonality, and YoY growth. Built to feed an LLM data-analysis
product during demos. **No third-party Python packages and no host psql are
needed — only Docker + python3 (stdlib).**

Skill directory (all paths below are relative to it):
`.claude/skills/erp-demo-gen/`

## Supported industries
`manufacturing`, `wholesale`, `retail`, `food_beverage`, `machinery_dealer`,
`contract_machining` (aliases like "discrete manufacturing", "distribution",
"e-commerce", "process manufacturing", "talaşlı imalat", "precision machining"
resolve automatically). Each picks its own table set automatically.

Two industries carry a full multi-currency ERP back office (company, FX rates,
chart of accounts, payroll, fixed assets, expenses, budgets, CRM, logistics,
customs, GL) and their own generator + views + checks:

* `machinery_dealer` — used machine-tool dealer, EUR base, serialized stock.
* `contract_machining` — high-volume Turkish precision-machining subcontractor,
  **TRY base with EUR/USD reporting on every document**, operation-level work
  orders (routings, production_operations), subcontract processes, quality/NCR,
  maintenance, OEE and HSE. Values are in Turkish; see
  `industries/contract_machining/notes.md`.

## Workflow — follow these steps

### 1. Load memory
Read `memory/preferences.md` (user defaults) and `memory/changelog.md` (past runs
+ tuning notes). Apply preferences as defaults. After the industry is known, also
read `industries/<industry>/notes.md` for that industry's seed guidance.

### 2. Intake (ask the user, using their defaults)
Collect — offer defaults from preferences so they can answer in one line:
- **Industry** (one of the four above).
- **Company name** (invent a fitting one if they don't care).
- **Years of history** and **end year** (default end = current year).
- **Company size** — either a band (`small` / `medium` / `large`) OR concrete
  numbers: `annual_revenue` (USD, final year), `annual_invoices` (per year),
  `employees`. Any subset is fine; the engine fills the rest from the size band.
- **Seed** (default 42) and **currency** (default USD).
Don't over-ask — if they say e.g. "a medium manufacturer, 10 years", that's enough.

### 3. Write the spec
Create `out/<slug>/spec.json` (pick a short snake_case `<slug>`). Schema:
```json
{
  "company_name": "Summit Forge Industries",
  "industry": "manufacturing",
  "slug": "summit_forge",
  "years": 10,
  "end_year": 2026,
  "size_band": "medium",
  "annual_revenue": 40000000,   // optional; overrides band
  "annual_invoices": 12000,      // optional
  "employees": 180,              // optional
  "currency": "USD",
  "seed": 42
}
```
Only `company_name` and `industry` are required; everything else has defaults.

### 4. Plan
Run:
```
python3 .claude/skills/erp-demo-gen/engine/run.py plan --spec out/<slug>/spec.json
```
This prints the derived profile (entity counts, revenue-by-year, selected tables)
and writes `out/<slug>/seeds.template.json`. Sanity-check the numbers with the user
if anything looks off.

### 5. Author the seeds
Read `out/<slug>/seeds.template.json`, then write `out/<slug>/seeds.json` with
**realistic, on-industry** content. Follow the industry's `notes.md` seed guidance.
Meet each `*_target` count (more is fine; the engine extends the long tail of
customer/vendor names with stdlib generators, but products/raw materials/work
centers should come from you). Schema (drop sections the template omits):
```json
{
  "company": {"name": "...", "tagline": "...", "hq_city": "...", "domain": "..."},
  "products": [
    {"name": "CNC Spindle Motor 5kW", "category": "Motors", "uom": "ea",
     "unit_cost_min": 420, "unit_cost_max": 680, "margin_pct": 38}
  ],
  "raw_materials": [{"name": "Cold-Rolled Steel Sheet", "category": "Metal", "uom": "kg", "unit_cost": 1.2}],
  "work_centers": [{"name": "CNC Cell A", "capacity_per_hour": 40, "cost_per_hour": 120}],
  "customer_names": ["Atlas Heavy Equipment", "Meridian Robotics", "..."],
  "vendor_names": ["Granite Steel Supply", "..."],
  "departments": ["Sales", "Procurement", "Production", "Quality", "Finance", "..."]
}
```
Make `unit_cost_min/max` plausible for each product and vary categories. The engine
derives list price from cost + margin, so costs drive everything downstream.

### 6. Build (generate + load + validate)
```
python3 .claude/skills/erp-demo-gen/engine/run.py build --spec out/<slug>/spec.json --seeds out/<slug>/seeds.json
```
This generates CSVs + `load.sql`, brings up Docker Postgres, creates `erp_<slug>`,
loads it, runs integrity/realism checks, and prints the connection string + a
summary + sample queries. (Add `--generate-only` to produce artifacts without
Docker, useful for a quick dry run.)

### 7. Report
The container also joins the external `meridyen-network`, so the user's other
apps on that network connect using the **container hostname** and the internal
port: `postgresql://demo:demo@erp_demo_pg:5432/erp_<slug>` (NOT `postgres` as the
host — that alias is ambiguous on the shared network; NOT 5544 — that is only the
host-side mapping for localhost access).

Give the user the **connection string**, the row totals, the validation result
(should be all PASS), and 2–3 sample queries (the engine prints these — they use
the analytics views `v_monthly_sales`, `v_customer_revenue`, `v_product_profitability`,
`v_ar_aging`, `v_inventory_valuation`, and where relevant `v_production_summary`).

### 8. Learn (update memory)
- If the user stated a lasting preference (favorite industry, default size, naming
  style), update `memory/preferences.md`.
- If a generated dataset looked off (e.g. margins or seasonality wrong, a check
  FAILed, too few/many of something), adjust the relevant
  `industries/<industry>/tuning.json` and add a dated note explaining why to both
  that industry's `notes.md` and `memory/changelog.md`. (`build` already appends a
  one-line run record automatically.)

## Notes & troubleshooting
- **Validation FAILs**: read the detail. Revenue-off-target usually means the seed
  product costs/margins don't fit the requested revenue ÷ invoices average order
  value — adjust seeds or size numbers. Orphan FKs / non-reconciling totals would
  indicate an engine bug; report it.
- **Scale**: 100k+ invoices/year works; generation is in-memory then bulk `COPY`.
  Large IoT is intentionally bounded to the most recent `iot_days`.
- **Reproducible**: same spec + seeds + seed ⇒ identical database. Change `seed`
  for a different-but-similar company.
- **Rebuild**: re-running `build` drops and recreates `erp_<slug>` cleanly.
- **Multiple companies** coexist as separate `erp_<slug>` databases in the one
  container. `docker compose down -v` (in the skill dir) wipes everything.
