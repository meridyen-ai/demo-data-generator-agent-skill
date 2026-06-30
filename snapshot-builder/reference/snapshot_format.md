# Snapshot JSON format

The platform configures each data source with a **snapshot** JSON. This skill
emits one in that exact shape. `reference/example-snapshot.json` is a real export
(an MSSQL/T-SQL Turkish ERP source) — use it as the structural/style exemplar.

## Top-level keys

| key                | type        | content-only policy |
|--------------------|-------------|---------------------|
| `id`               | int/null    | platform-assigned → **null** |
| `space_id`         | int/null    | platform-assigned → **null** |
| `connection_id`    | int/null    | platform-assigned → **null** |
| `comment`          | str/null    | null (or a short note) |
| `created_by`       | int/null    | null |
| `author_name`      | str         | `"snapshot-builder"` |
| `created_at`       | str (ISO)   | generation timestamp |
| `selected_schema`  | object      | **generated** (see below) |
| `connection_config`| null        | null |
| `joins_data`       | list        | **generated** from FKs |
| `instructions`     | str         | **generated** global instructions |
| `prompts_data`     | list        | example prompts (may be `[]`) |
| `settings_data`    | object      | minimal stub: target DB host/port/name/user + `*_set` flags |

We emit **content-only**: the meaningful fields are generated; platform IDs are
left null for the user to wire on import.

## `selected_schema`

```jsonc
{
  "public.sales_orders": {
    "selected": true,
    "instructions": "<<per-table METRIC/DIMENSION/FILTER recipe>>",
    "columns": {
      "id":         { "selected": true, "is_hidden": true },   // technical → hidden
      "order_date": { "selected": true },                       // business dim → visible
      "total":      { "selected": true }
    }
  },
  "_connection_meta": { "instructions": "<<mirror of top-level `instructions`>>" }
}
```

- Key format: `"<schema>.<table>"` (Postgres default schema is `public`).
- Every exposed column appears with `selected: true`.
- `is_hidden: true` keeps a column **queryable by the engine but hidden from the
  end-user UI**. Apply to technical/id/code/surrogate columns (`id`, `*_id`,
  `*_no`, internal codes). Leave business-meaningful columns visible (no
  `is_hidden` key).
- `_connection_meta` is a **special pseudo-table** carrying only `instructions`,
  which must be an **exact copy** of the top-level `instructions` string.

## `joins_data`

One object per relationship (generated from foreign keys):

```jsonc
{
  "name": "sales_order_lines-sales_orders",
  "description": "",
  "source_table": "public.sales_order_lines",
  "source_column": "order_id",
  "target_table": "public.sales_orders",
  "target_column": "id",
  "join_type": "LEFT",
  "cardinality": "MANY_TO_ONE"
}
```

FK child→parent ⇒ `join_type: "LEFT"`, `cardinality: "MANY_TO_ONE"`. (The platform
may add `id/connection_id/created_at` on import; omit or null them in content-only.)

## `instructions` (global) — two bracketed sections

The string MUST contain these two sections (the platform parses on the markers):

```
[ENRICHMENT ONLY]
... table routing: question intent -> table; "pick the FEWEST tables"; routing
    hints (net vs gross, which date column, sales vs returns, etc.) ...
[/ENRICHMENT ONLY]
[SQL GEN]
GLOBAL SQL RULES (PostgreSQL):
... NULL-safe sums, date filters, text matching, data span, scalar alias AS t ...
[/SQL GEN]
```

See `instruction_style.md` for exactly how to write both these and the per-table
`instructions`.

## `settings_data` (content-only stub)

Carry the target connection so the platform can reconnect; leave models empty and
secrets unset:

```jsonc
{
  "local_db_host": "<host>", "local_db_port": 5432,
  "local_db_name": "<db>",   "local_db_user": "<user>",
  "local_db_pass_set": true,
  "sql_validation_enabled": false
}
```
