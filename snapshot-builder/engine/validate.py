"""Validate a finished snapshot against the format + the introspected schema.

Returns a list of (level, ok, message). level is 'error' or 'warn'. Catches the
things that would make the platform reject or misuse the snapshot: malformed
shape, references to non-existent tables/columns, missing instruction sections,
and leftover empty instructions on selected tables.
"""
from __future__ import annotations

REQUIRED_TOP = ["selected_schema", "joins_data", "instructions", "prompts_data", "settings_data"]
MARKERS = ["[ENRICHMENT ONLY]", "[/ENRICHMENT ONLY]", "[SQL GEN]", "[/SQL GEN]"]


def validate(snap: dict, introspection: dict):
    checks = []

    def err(ok, msg):
        checks.append(("error", ok, msg))

    def warn(ok, msg):
        checks.append(("warn", ok, msg))

    schema = introspection["schema"]
    real_cols = {f"{schema}.{t['name']}": {c['name'] for c in t['columns']}
                 for t in introspection["tables"]}

    for k in REQUIRED_TOP:
        err(k in snap, f"top-level key present: {k}")

    ss = snap.get("selected_schema", {})
    err("_connection_meta" in ss, "_connection_meta present")

    # tables/columns reference real schema
    bad_tables, bad_cols = [], []
    selected_tables = []
    for key, tv in ss.items():
        if key == "_connection_meta":
            continue
        if key not in real_cols:
            bad_tables.append(key)
            continue
        if tv.get("selected"):
            selected_tables.append(key)
        for col in tv.get("columns", {}):
            if col not in real_cols[key]:
                bad_cols.append(f"{key}.{col}")
    err(not bad_tables, f"all schema tables exist ({len(bad_tables)} unknown: {bad_tables[:5]})")
    err(not bad_cols, f"all schema columns exist ({len(bad_cols)} unknown: {bad_cols[:5]})")

    # global instructions + markers + mirror
    gi = snap.get("instructions", "") or ""
    err(bool(gi.strip()), "global instructions non-empty")
    for m in MARKERS:
        err(m in gi, f"global instructions contain marker {m}")
    mirror = ss.get("_connection_meta", {}).get("instructions", "")
    err(mirror == gi, "_connection_meta.instructions mirrors global instructions")

    # per-table instructions present for selected tables
    empty = [k for k in selected_tables if not (ss[k].get("instructions") or "").strip()]
    warn(not empty, f"selected tables have instructions ({len(empty)} empty: {empty[:5]})")

    # joins reference real tables/columns
    bad_joins = []
    for j in snap.get("joins_data", []):
        for side in ("source", "target"):
            t = j.get(f"{side}_table")
            c = j.get(f"{side}_column")
            if t not in real_cols or c not in real_cols.get(t, set()):
                bad_joins.append(f"{j.get('name')} ({side})")
    err(not bad_joins, f"joins reference real columns ({len(bad_joins)} bad: {bad_joins[:5]})")

    err(isinstance(snap.get("prompts_data"), list), "prompts_data is a list")
    return checks
