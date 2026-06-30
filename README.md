# demo-data-generator agent skills

A collection of Claude Code **agent skills** for producing and configuring
realistic fictional data for analytics demos and presales. Each subdirectory is a
self-contained skill (its own `SKILL.md`, engine, and docs).

## Skills

### [`erp-demo-gen/`](erp-demo-gen/)
Generates realistic, internally-consistent fictional **ERP-style Postgres
databases** (sales, purchases, invoices, payments, returns, inventory, production,
IoT, GL, bank). Hybrid generation: the LLM authors qualitative seeds (names), a
deterministic stdlib-only Python engine produces high-volume transactional rows
with valid foreign keys, reconciling totals, YoY growth, and seasonality. Four
industries (manufacturing, wholesale, retail, food & beverage); loads into local
Docker Postgres via bulk `COPY`.

### [`snapshot-builder/`](snapshot-builder/)
Writes the best possible **"snapshot"** — the JSON config an analytics platform
uses to make its LLM SQL query-writer accurate (selected tables/columns, joins, and
rich per-table METRIC/DIMENSION/routing instructions). Connects to a database
(default: the demo Postgres above), introspects it, fires **read-only** queries to
learn real distinct values and verify every metric recipe, then emits a snapshot in
the platform's exact format.

Typical pairing: build a demo database with `erp-demo-gen`, then build its snapshot
with `snapshot-builder`.

## Requirements
- Docker + Docker Compose
- Python 3 (standard library only — no third-party packages)
