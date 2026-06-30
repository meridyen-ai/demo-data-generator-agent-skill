# erp-demo-gen

A Claude Code **agent skill** that generates realistic, internally-consistent
fictional **ERP-style Postgres databases** for demos and presales — fresh sample
data to feed an LLM-driven data-analysis product.

You tell it an industry, a number of years, and a company size; it asks a couple
of questions, then generates and loads a per-industry schema (15–26 tables) of
sales, purchases, invoices, payments, returns, inventory, production, IoT, GL,
and bank data into local Docker Postgres — and hands you a connection string.

## How it works (hybrid generation)

- **LLM authors the seeds** — company identity, product names, customer/vendor
  names, departments, work centers (the qualitative, on-industry content).
- **A deterministic, stdlib-only Python engine** generates the high-volume
  transactional rows with valid foreign keys, reconciling totals, YoY growth,
  and seasonality. Seeded → fully reproducible; scales to millions of rows via
  bulk `COPY`.

No third-party Python packages and no host `psql` required — only **Docker** +
**python3** (standard library). Loading goes through the Postgres container's own
`COPY` (the `out/` dir is mounted into the container).

## Industries

Each auto-selects its own table set:

| Industry        | Highlights                                              |
|-----------------|---------------------------------------------------------|
| `manufacturing` | BOMs, production orders, material consumption, machine IoT |
| `wholesale`     | Multi-warehouse buy/resell, no production               |
| `retail`        | Channels, promotions, high volume, near-immediate payment |
| `food_beverage` | Recipes, lots with expiry, cold-chain IoT               |

Plus analytics views: `v_monthly_sales`, `v_customer_revenue`,
`v_product_profitability`, `v_ar_aging`, `v_inventory_valuation`,
`v_production_summary`.

## Usage

This is a Claude Code skill — invoke it in conversation (e.g. *"generate a medium
food & beverage company with 10 years of data"*). Under the hood:

```bash
# 1. derive the company profile + write a seeds template for the LLM to fill
python3 engine/run.py plan  --spec out/<slug>/spec.json

# 2. generate CSVs + load.sql, bring up Docker Postgres, load, validate
python3 engine/run.py build --spec out/<slug>/spec.json --seeds out/<slug>/seeds.json
```

**Connection** (from host): `postgresql://demo:demo@localhost:5544/erp_<slug>`

Each generated company is its own `erp_<slug>` database in the one container.

## Layout

```
SKILL.md            orchestration instructions (skill entrypoint)
docker-compose.yml  postgres:16 target (host port 5544)
engine/             the generator: profile/sizing, catalog, ddl, generators,
                    generate (CSV+SQL), load (docker+psql), validate, run (CLI)
industries/<name>/  tables.json (table set) · tuning.json (ratios/seasonality) · notes.md
memory/             user preferences + run/learning changelog
```

`industries/*/tuning.json` and `memory/` are the editable "learning" surface —
adjust them to refine realism over time.

## Requirements

- Docker + Docker Compose
- Python 3 (standard library only)
