"""snapshot-builder CLI.

  run.py connect   --name acme --host 10.0.0.5 --dbname sales --user reader --password ***
  run.py list-dbs  [--name demo]
  run.py prepare   [--name demo] [--dbname erp_acme] [--no-profile]   # introspect + scaffold
  run.py query     [--name demo] --sql "SELECT ..."                   # read-only ad-hoc
  run.py selftest  --db erp_acme
  run.py assemble  --db erp_acme         # merge instructions.json -> snapshot.json (+ validate)
  run.py validate  --db erp_acme

Typical flow: prepare -> (agent reads introspection.json, writes instructions.json
+ metric_tests.json) -> selftest -> assemble.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import db, introspect as introspect_mod, scaffold as scaffold_mod  # noqa: E402
from engine import selftest as selftest_mod, validate as validate_mod, assemble as assemble_mod  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out")


def _out_dir(label):
    d = os.path.join(OUT, label)
    os.makedirs(d, exist_ok=True)
    return d


def _now():
    return datetime.datetime.now().isoformat()


def _load(path):
    with open(path) as f:
        return json.load(f)


def _dump(path, obj):
    with open(path, "w") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)


def cmd_connect(args):
    cfg, _ = db.load_config()
    cfg.setdefault("connections", {})[args.name] = {
        "mode": "remote", "host": args.host, "port": args.port,
        "user": args.user, "dbname": args.dbname, "schema": args.schema,
        "dialect": "postgres", "pass_set": bool(args.password),
    }
    db.save_config(cfg)
    if args.password:
        db.save_secret(args.name, args.password)
    print(f"Saved connection '{args.name}' ({args.user}@{args.host}:{args.port}/{args.dbname}).")
    print("Password stored in config/connections.local.json (gitignored)." if args.password
          else "No password stored (assuming trust / .pgpass).")


def cmd_list_dbs(args):
    conn = db.resolve(args.name)
    for d in db.list_databases(conn):
        print(d)


def cmd_query(args):
    conn = db.resolve(args.name)
    dbname = args.dbname or db.resolve_dbname(conn)
    db._check_readonly(args.sql)
    r = db._run(conn, dbname, [], args.sql, check=False)
    sys.stdout.write(r.stdout)
    if r.returncode != 0:
        sys.stderr.write(r.stderr)
        sys.exit(1)


def cmd_prepare(args):
    conn = db.resolve(args.name)
    dbname = args.dbname or db.resolve_dbname(conn)
    schema = conn.get("schema", "public")
    print(f"Introspecting {dbname} (schema {schema}) via {conn['name']}...")
    intro = introspect_mod.introspect(conn, schema, dbname, profile=not args.no_profile)
    out = _out_dir(dbname)
    _dump(os.path.join(out, "introspection.json"), intro)

    draft = scaffold_mod.build(intro, conn, _now())
    _dump(os.path.join(out, "snapshot.draft.json"), draft)

    nt = len(intro["tables"])
    nfk = len(intro["foreign_keys"])
    print(f"Tables/views: {nt}   Foreign keys: {nfk}")
    for t in intro["tables"]:
        roles = {}
        for c in t["columns"]:
            roles[c["role"]] = roles.get(c["role"], 0) + 1
        rolestr = " ".join(f"{k}:{v}" for k, v in sorted(roles.items()))
        print(f"  {t['name']:<26} {str(t.get('rows')):>9} rows  [{rolestr}]")
    print(f"\nWrote {out}/introspection.json and snapshot.draft.json")
    print("Next: read introspection.json, write instructions.json + metric_tests.json, "
          "then `selftest` and `assemble`.")


def cmd_selftest(args):
    out = _out_dir(args.db)
    tests_path = os.path.join(out, "metric_tests.json")
    if not os.path.exists(tests_path):
        raise SystemExit(f"Missing {tests_path}. Author metric tests first.")
    conn = db.resolve(args.name)
    tests = _load(tests_path)
    report = selftest_mod.run(conn, tests, dbname=args.db)
    _dump(os.path.join(out, "selftest.json"), report)
    print(f"Self-test: {report['passed']}/{report['total']} passed, "
          f"{report['failed']} failed, {report['suspect']} suspect (ok but empty/zero).")
    for r in report["results"]:
        if not r["ok"]:
            print(f"  [FAIL] {r['table']} :: {r['name']}\n         {r.get('error','').strip()[:200]}")
        elif r["suspect"]:
            print(f"  [SUSPECT={r['result']!r}] {r['table']} :: {r['name']}")
    if report["failed"]:
        sys.exit(1)


def cmd_assemble(args):
    out = _out_dir(args.db)
    draft = _load(os.path.join(out, "snapshot.draft.json"))
    instr_path = os.path.join(out, "instructions.json")
    if not os.path.exists(instr_path):
        raise SystemExit(f"Missing {instr_path}. Author instructions first.")
    instr = _load(instr_path)
    snap = assemble_mod.assemble(draft, instr)
    snap_path = os.path.join(out, "snapshot.json")
    _dump(snap_path, snap)
    print(f"Assembled {snap_path}")
    _run_validate(out, snap)


def cmd_validate(args):
    out = _out_dir(args.db)
    snap = _load(os.path.join(out, "snapshot.json"))
    _run_validate(out, snap)


def _run_validate(out, snap):
    intro = _load(os.path.join(out, "introspection.json"))
    checks = validate_mod.validate(snap, intro)
    errs = sum(1 for lvl, ok, _ in checks if lvl == "error" and not ok)
    warns = sum(1 for lvl, ok, _ in checks if lvl == "warn" and not ok)
    for lvl, ok, msg in checks:
        if not ok:
            print(f"  [{lvl.upper()}] {msg}")
    print(f"Validation: {'PASS' if errs == 0 else 'FAIL'} ({errs} errors, {warns} warnings)")
    if errs:
        sys.exit(1)


def main():
    ap = argparse.ArgumentParser(prog="snapshot-builder")
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("connect")
    c.add_argument("--name", required=True); c.add_argument("--host", required=True)
    c.add_argument("--port", type=int, default=5432); c.add_argument("--dbname", required=True)
    c.add_argument("--user", required=True); c.add_argument("--password", default=None)
    c.add_argument("--schema", default="public"); c.set_defaults(fn=cmd_connect)

    l = sub.add_parser("list-dbs"); l.add_argument("--name", default=None); l.set_defaults(fn=cmd_list_dbs)

    q = sub.add_parser("query"); q.add_argument("--name", default=None)
    q.add_argument("--dbname", default=None); q.add_argument("--sql", required=True)
    q.set_defaults(fn=cmd_query)

    p = sub.add_parser("prepare"); p.add_argument("--name", default=None)
    p.add_argument("--dbname", default=None); p.add_argument("--no-profile", action="store_true")
    p.set_defaults(fn=cmd_prepare)

    s = sub.add_parser("selftest"); s.add_argument("--db", required=True)
    s.add_argument("--name", default=None); s.set_defaults(fn=cmd_selftest)

    a = sub.add_parser("assemble"); a.add_argument("--db", required=True); a.set_defaults(fn=cmd_assemble)
    v = sub.add_parser("validate"); v.add_argument("--db", required=True); v.set_defaults(fn=cmd_validate)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
