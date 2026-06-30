---
name: snapshot-builder
description: Write the best possible "snapshot" config for a database so an analytics platform's LLM query-writer is maximally accurate. Use when the user wants to build/generate/improve a snapshot, enrich a database connection with instructions, or prepare a DB for the SQL-writing agent. Connects to the target (default = the local demo Postgres), introspects it, fires read-only queries to learn real distinct values and verify metric formulas, then emits a snapshot JSON in the platform's exact format.
---

# snapshot-builder

Produces a **snapshot** — the JSON config the user's analytics platform uses to make
its LLM query-writer accurate. A snapshot declares which tables/columns are exposed,
the joins between them, and rich `instructions` (table routing + per-table
METRIC/DIMENSION/filter recipes + global SQL rules). This skill connects to a
database, learns it by running **read-only** queries, and writes the best snapshot it
can — every metric recipe **verified by execution**.

Skill directory (paths below are relative to it): `.claude/skills/snapshot-builder/`

**Read first:** `reference/snapshot_format.md` (exact output format) and
`reference/instruction_style.md` (how to write great instructions). The provided
real export is at `reference/example-snapshot.json` (style exemplar — note it is
MSSQL/Turkish; the demo target is Postgres/English, so write **PostgreSQL** SQL).

## Target databases
- **Default = the demo Postgres** built by the sibling `erp-demo-gen` skill (the
  `erp_demo_pg` container). Connection name `demo`; if its `dbname` is unset the
  engine auto-detects the single `erp_*` database.
- **Custom = any reachable Postgres.** Save it once:
  `run.py connect --name <n> --host <h> --port 5432 --dbname <db> --user <u> --password <pw>`
  (password is written to `config/connections.local.json`, gitignored). All queries
  run through the `erp_demo_pg` container's `psql`, so the target must be reachable
  from that container.
- Everything is **read-only** (session forced `read_only` + a SELECT/WITH/EXPLAIN
  allowlist) — safe to point at a customer database.

## Workflow — follow these steps

### 1. Choose the connection
Default to `demo`. If the user named another saved connection use it; if they want a
new database, run `run.py connect ...` first. Confirm which `erp_*`/database if
ambiguous (`run.py list-dbs`).

### 2. Prepare (introspect + scaffold)
```
python3 engine/run.py prepare [--name demo] [--dbname <db>]
```
Writes `out/<db>/introspection.json` (tables, columns+roles, PK/FK, row counts, and
per-column **distinct values / ranges / null fractions**) and
`out/<db>/snapshot.draft.json` (skeleton: every column selected, `is_hidden` on
technical/id columns, `joins_data` from the real foreign keys, settings stub). Read
the printed summary and `introspection.json` thoroughly.

### 3. Explore freely (you have ~10 minutes — use it)
Run as many read-only probes as you need to get recipes right:
```
python3 engine/run.py query --name demo --sql "SELECT status, count(*) FROM sales_orders GROUP BY 1"
```
Check distinct values, sign conventions, how totals reconcile (net vs gross/tax),
which date column each fact uses, what joins are meaningful, edge cases. Don't guess —
look.

### 4. Author `out/<db>/instructions.json`
This is the core value. Shape (see `instruction_style.md` for full templates):
```jsonc
{
  "global": "=== CONNECTION INSTRUCTIONS ===\n[ENRICHMENT ONLY] ...routing... [/ENRICHMENT ONLY]\n[SQL GEN] ...PostgreSQL rules... [/SQL GEN]",
  "tables": { "public.sales_orders": "METRIC: ...\nDIMENSIONS: ...\nGOTCHAS: ...", ... },
  "hidden_overrides": { "public.<t>": { "<col>": false } },   // optional: unhide/hide
  "deselect_tables": [ ],                                      // optional
  "prompts": [ "What was net revenue in 2026?", ... ]          // optional example questions
}
```
Requirements:
- `global` MUST contain the four markers `[ENRICHMENT ONLY] [/ENRICHMENT ONLY]
  [SQL GEN] [/SQL GEN]`. Route each business intent to the **fewest** tables; only
  mention tables that are actually selected.
- Write a per-table recipe for **every meaningful table** (the big fact tables first;
  cover dimension tables and useful views too). Use **real discovered distinct
  values**, exact Postgres expressions, the correct date column, and net-vs-gross
  notes.
- Use PostgreSQL dialect: `COALESCE`, `EXTRACT(YEAR FROM d)`, `ILIKE`, `::numeric`.

### 5. Back every METRIC with a runnable test in `out/<db>/metric_tests.json`
```jsonc
[ { "table": "public.sales_orders", "name": "net revenue 2026",
    "sql": "SELECT SUM(COALESCE(subtotal,0)-COALESCE(discount,0)) AS t FROM sales_orders WHERE status<>'cancelled' AND EXTRACT(YEAR FROM order_date)=2026" } ]
```

### 6. Self-test → repair → repeat
```
python3 engine/run.py selftest --db <db>
```
Every test must run; fix anything `FAIL` (SQL error) or `SUSPECT` (returned
empty/zero when it shouldn't) by correcting the recipe and the instruction text, then
re-run until clean.

### 7. Assemble + validate
```
python3 engine/run.py assemble --db <db>
```
Merges `instructions.json` into the draft → `out/<db>/snapshot.json`, then validates
shape + that every table/column/join reference exists and the instruction markers/
mirror are present. Fix any `ERROR`; `WARN` (e.g. a table left without instructions)
is acceptable but prefer to fill them.

### 8. Deliver + learn
Give the user the path to `out/<db>/snapshot.json` and a short summary (tables
covered, metrics verified, self-test pass count). It is **content-only**: platform
IDs are null — they import it and the platform wires connection/space IDs.
Then update memory: append a run line to `memory/changelog.md`, and record any recipe
pattern that worked well (or a gotcha) in `memory/patterns.md`.

## Notes
- Stdlib-only Python; no pip. Requires Docker (the `erp_demo_pg` client container) +
  python3.
- The demo DB already has real FKs (→ joins) and clean column names — excellent source
  material. For other databases without FKs, infer joins from column names and verify
  with a probe before adding them to `instructions.json` via the draft.
- Re-running `prepare` overwrites introspection + draft; your `instructions.json` and
  `metric_tests.json` are preserved.
