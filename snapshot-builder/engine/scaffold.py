"""Build the snapshot skeleton from an introspection profile.

Emits selected_schema (all columns selected; is_hidden on technical/id columns),
joins_data (one per foreign key), a content-only settings_data stub, and empty
instruction placeholders for the agent to fill. assemble.py later merges the
agent's authored instructions in.
"""
from __future__ import annotations


def _key(schema, table):
    return f"{schema}.{table}"


def build(introspection, conn, created_at):
    schema = introspection["schema"]
    selected_schema = {}

    for t in introspection["tables"]:
        cols = {}
        for c in t["columns"]:
            entry = {"selected": True}
            if c.get("hidden_suggested"):
                entry["is_hidden"] = True
            cols[c["name"]] = entry
        selected_schema[_key(schema, t["name"])] = {
            "selected": True,
            "instructions": "",          # agent fills
            "columns": cols,
        }
    selected_schema["_connection_meta"] = {"instructions": ""}

    joins = []
    for fk in introspection["foreign_keys"]:
        joins.append({
            "name": f"{fk['source_table']}-{fk['target_table']}",
            "description": "",
            "source_table": _key(schema, fk["source_table"]),
            "source_column": fk["source_column"],
            "target_table": _key(schema, fk["target_table"]),
            "target_column": fk["target_column"],
            "join_type": "LEFT",
            "cardinality": "MANY_TO_ONE",
        })

    settings = {
        "local_db_host": conn.get("host", "localhost") if conn.get("mode") != "remote" else conn.get("host"),
        "local_db_port": conn.get("port", 5432),
        "local_db_name": introspection["database"],
        "local_db_user": conn.get("user"),
        "local_db_pass_set": bool(conn.get("pass_set") or conn.get("password")),
        "sql_validation_enabled": False,
    }

    return {
        "id": None,
        "space_id": None,
        "connection_id": None,
        "comment": None,
        "created_by": None,
        "author_name": "snapshot-builder",
        "created_at": created_at,
        "selected_schema": selected_schema,
        "connection_config": None,
        "joins_data": joins,
        "instructions": "",              # agent fills (global)
        "prompts_data": [],
        "settings_data": settings,
    }
