"""Introspect a Postgres database into a structured profile.

Produces tables/views, columns (+ role classification), primary/foreign keys,
row counts, and per-column profiling (distinct count, null fraction, min/max,
top values) so the agent can write verified instructions. Read-only throughout.
"""
from __future__ import annotations

from . import db

NUMERIC = {"integer", "bigint", "smallint", "numeric", "double precision", "real", "money"}
DATE = {"date", "timestamp without time zone", "timestamp with time zone", "time without time zone"}
TEXT = {"text", "character varying", "character"}

MEASURE_HINTS = ("qty", "price", "cost", "total", "amount", "subtotal", "discount",
                 "tax", "margin", "balance", "value", "salary", "debit", "credit",
                 "paid", "revenue", "rate", "capacity", "limit")
TOPN = 15
LOW_CARD = 60  # only fetch top values for text columns with <= this many distincts


def _q(ident):
    return '"' + ident.replace('"', '""') + '"'


def classify(col, pk_cols, fk_cols):
    name = col["name"].lower()
    dt = col["data_type"]
    is_id = (name == "id" or name.endswith("_id") or name.endswith("_no")
             or name in ("sku", "code", "iban") or name in pk_cols or name in fk_cols)
    if dt in DATE:
        role = "date"
    elif dt == "boolean":
        role = "dimension"
    elif dt in TEXT:
        role = "id" if is_id else "dimension"
    elif dt in NUMERIC:
        if is_id:
            role = "id"
        elif any(h in name for h in MEASURE_HINTS):
            role = "measure"
        else:
            role = "measure"  # default numeric -> measure
    else:
        role = "dimension"
    hidden = is_id  # technical/surrogate columns hidden from UI by default
    return role, is_id, hidden


def get_tables(conn, schema, dbname):
    rows = db.run_rows(conn,
        f"SELECT table_name, table_type FROM information_schema.tables "
        f"WHERE table_schema='{schema}' ORDER BY table_name", db=dbname)
    return [{"name": r["table_name"],
             "type": "view" if r["table_type"] == "VIEW" else "table"} for r in rows]


def get_columns(conn, schema, dbname):
    rows = db.run_rows(conn,
        f"SELECT table_name, column_name, data_type, is_nullable, ordinal_position "
        f"FROM information_schema.columns WHERE table_schema='{schema}' "
        f"ORDER BY table_name, ordinal_position", db=dbname)
    by_table = {}
    for r in rows:
        by_table.setdefault(r["table_name"], []).append({
            "name": r["column_name"], "data_type": r["data_type"],
            "nullable": r["is_nullable"] == "YES", "ordinal": int(r["ordinal_position"]),
        })
    return by_table


def get_primary_keys(conn, schema, dbname):
    rows = db.run_rows(conn,
        f"SELECT tc.table_name, kcu.column_name "
        f"FROM information_schema.table_constraints tc "
        f"JOIN information_schema.key_column_usage kcu "
        f"  ON tc.constraint_name=kcu.constraint_name AND tc.table_schema=kcu.table_schema "
        f"WHERE tc.constraint_type='PRIMARY KEY' AND tc.table_schema='{schema}'", db=dbname)
    pk = {}
    for r in rows:
        pk.setdefault(r["table_name"], []).append(r["column_name"])
    return pk


def get_foreign_keys(conn, schema, dbname):
    rows = db.run_rows(conn,
        f"SELECT tc.table_name AS src_t, kcu.column_name AS src_c, "
        f"  ccu.table_name AS tgt_t, ccu.column_name AS tgt_c "
        f"FROM information_schema.table_constraints tc "
        f"JOIN information_schema.key_column_usage kcu "
        f"  ON tc.constraint_name=kcu.constraint_name AND tc.table_schema=kcu.table_schema "
        f"JOIN information_schema.constraint_column_usage ccu "
        f"  ON tc.constraint_name=ccu.constraint_name AND tc.table_schema=ccu.table_schema "
        f"WHERE tc.constraint_type='FOREIGN KEY' AND tc.table_schema='{schema}' "
        f"ORDER BY src_t, src_c", db=dbname)
    return [{"source_table": r["src_t"], "source_column": r["src_c"],
             "target_table": r["tgt_t"], "target_column": r["tgt_c"]} for r in rows]


def profile_table(conn, schema, dbname, tname, cols):
    """One aggregate pass for counts/nulls/distinct/min-max, then top-N for
    low-cardinality text columns."""
    n = int(db.run_scalar(conn, f"SELECT count(*) FROM {schema}.{_q(tname)}", db=dbname) or 0)
    if n == 0:
        for c in cols:
            c.update(rows=0, null_frac=None, distinct=0, min=None, max=None, top_values=[])
        return n

    selects = ["count(*) AS n"]
    for i, c in enumerate(cols):
        cq = _q(c["name"])
        selects.append(f"count({cq}) AS nn{i}")
        selects.append(f"count(distinct {cq}) AS d{i}")
        if c["data_type"] in NUMERIC or c["data_type"] in DATE:
            selects.append(f"min({cq})::text AS mn{i}")
            selects.append(f"max({cq})::text AS mx{i}")
    agg = db.run_rows(conn, f"SELECT {', '.join(selects)} FROM {schema}.{_q(tname)}", db=dbname)
    row = agg[0] if agg else {}
    for i, c in enumerate(cols):
        nn = int(row.get(f"nn{i}", 0) or 0)
        d = int(row.get(f"d{i}", 0) or 0)
        c["rows"] = n
        c["null_frac"] = round(1 - nn / n, 4) if n else None
        c["distinct"] = d
        c["min"] = row.get(f"mn{i}")
        c["max"] = row.get(f"mx{i}")
        c["top_values"] = []

    # top-N for low-cardinality text/boolean dimension columns
    for c in cols:
        if c["role"] == "dimension" and c["data_type"] in (TEXT | {"boolean"}) \
                and 0 < c["distinct"] <= LOW_CARD:
            cq = _q(c["name"])
            tv = db.run_rows(conn,
                f"SELECT {cq}::text AS v, count(*) AS c FROM {schema}.{_q(tname)} "
                f"WHERE {cq} IS NOT NULL GROUP BY 1 ORDER BY 2 DESC LIMIT {TOPN}", db=dbname)
            c["top_values"] = [{"value": r["v"], "count": int(r["c"])} for r in tv]
    return n


def introspect(conn, schema, dbname, profile=True):
    tables = get_tables(conn, schema, dbname)
    cols_by_table = get_columns(conn, schema, dbname)
    pks = get_primary_keys(conn, schema, dbname)
    fks = get_foreign_keys(conn, schema, dbname)
    fk_cols_by_table = {}
    for fk in fks:
        fk_cols_by_table.setdefault(fk["source_table"], set()).add(fk["source_column"])

    out_tables = []
    for t in tables:
        tname = t["name"]
        cols = cols_by_table.get(tname, [])
        pk_cols = set(pks.get(tname, []))
        fk_cols = fk_cols_by_table.get(tname, set())
        for c in cols:
            role, is_id, hidden = classify(c, pk_cols, fk_cols)
            c["role"], c["is_id"], c["hidden_suggested"] = role, is_id, hidden
        if profile:
            try:
                profile_table(conn, schema, dbname, tname, cols)
            except SystemExit:
                for c in cols:
                    c.setdefault("rows", None)
        out_tables.append({
            "name": tname, "type": t["type"],
            "primary_key": sorted(pk_cols),
            "rows": cols[0].get("rows") if cols else 0,
            "columns": cols,
        })

    return {
        "database": dbname, "schema": schema, "dialect": "postgres",
        "tables": out_tables, "foreign_keys": fks,
    }
