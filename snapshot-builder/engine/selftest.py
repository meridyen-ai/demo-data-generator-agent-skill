"""Execute the agent's metric test queries against the live database.

metric_tests.json: [ { "table": "...", "name": "...", "sql": "SELECT ... AS t ..." } ]
Each is run read-only; we capture the scalar result or the error. This is the
evidence that every METRIC recipe in the snapshot actually works.
"""
from __future__ import annotations

from . import db


def run(conn, tests, dbname=None):
    results = []
    for t in tests:
        entry = {"table": t.get("table"), "name": t.get("name"), "sql": t.get("sql")}
        try:
            val = db.run_scalar(conn, t["sql"], db=dbname)
            entry["ok"] = True
            entry["result"] = val
            # flag suspicious (empty / null) results so the agent can revisit
            entry["suspect"] = (val is None or val == "" or val == "0")
        except SystemExit as e:
            entry["ok"] = False
            entry["error"] = str(e)
        results.append(entry)
    passed = sum(1 for r in results if r.get("ok"))
    suspect = sum(1 for r in results if r.get("ok") and r.get("suspect"))
    return {"total": len(results), "passed": passed, "failed": len(results) - passed,
            "suspect": suspect, "results": results}
