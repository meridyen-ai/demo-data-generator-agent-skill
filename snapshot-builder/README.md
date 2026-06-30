# snapshot-builder

A Claude Code **agent skill** that writes the best possible **"snapshot"** — the
JSON config an analytics platform uses to make its LLM SQL query-writer accurate.

Given a database, the agent connects, introspects it, fires **read-only** queries to
learn real distinct values and verify metric formulas (it may run ~10 minutes), and
emits a snapshot JSON in the platform's exact format: which tables/columns are
exposed, the joins, and rich `instructions` (table routing + per-table
METRIC/DIMENSION/filter recipes + global SQL rules). Every metric recipe is
**verified by execution**.

## What's in a snapshot

- `selected_schema` — every exposed table/column; `is_hidden` on technical/id columns.
- `joins_data` — relationships (auto-derived from foreign keys).
- `instructions` — global routing + SQL rules, in two bracketed sections
  `[ENRICHMENT ONLY] … [/ENRICHMENT ONLY]` and `[SQL GEN] … [/SQL GEN]`; mirrored into
  a `_connection_meta` entry.
- per-table `instructions` — the METRIC/DIMENSION/GOTCHA recipes that do the real work.
- `prompts_data`, `settings_data` (content-only stub).

See `reference/snapshot_format.md` and `reference/instruction_style.md`.
`reference/example-snapshot.json` is a real export used as the style exemplar.

## Targets

- **Default:** the local demo Postgres built by the sibling `erp-demo-gen` skill
  (`erp_demo_pg` container).
- **Custom:** any reachable Postgres — `run.py connect --name … --host … --dbname …
  --user … --password …` (secret stored in the gitignored
  `config/connections.local.json`).

All access is **read-only** (session `default_transaction_read_only` + a
SELECT/WITH/EXPLAIN allowlist), safe for customer databases. Queries run through the
demo container's `psql`, so the target must be reachable from it.

## Usage (driven by the skill; CLI underneath)

```bash
python3 engine/run.py prepare  [--name demo] [--dbname <db>]   # introspect + scaffold
python3 engine/run.py query    --name demo --sql "SELECT ..."  # read-only exploration
# (agent authors out/<db>/instructions.json + out/<db>/metric_tests.json)
python3 engine/run.py selftest --db <db>                       # execute every metric recipe
python3 engine/run.py assemble --db <db>                       # merge -> snapshot.json + validate
```

Output: `out/<db>/snapshot.json` (content-only; platform IDs null for import).

## Requirements

- Docker (the `erp_demo_pg` client container) + Python 3 (standard library only).
