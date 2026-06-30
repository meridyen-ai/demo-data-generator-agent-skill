"""Connection registry + READ-ONLY psql runner.

All queries run through a Postgres client container's `psql` (default the
`erp_demo_pg` container built by erp-demo-gen, which has psql and network access).
For the demo target, psql talks to its own local database; for a remote target it
connects with `-h host`. Every statement is forced read-only, so a customer
database can never be mutated by this skill.
"""
from __future__ import annotations

import csv
import io
import json
import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(ROOT, "config", "connections.json")
SECRETS = os.path.join(ROOT, "config", "connections.local.json")

# The container used as the psql client for every connection.
CLIENT_CONTAINER = os.environ.get("SNAPSHOT_CLIENT_CONTAINER", "erp_demo_pg")

_READ_OK = ("select", "with", "explain", "show", "table", "values")


def load_config():
    with open(CONFIG) as f:
        cfg = json.load(f)
    secrets = {}
    if os.path.exists(SECRETS):
        with open(SECRETS) as f:
            secrets = json.load(f)
    return cfg, secrets


def save_config(cfg):
    with open(CONFIG, "w") as f:
        json.dump(cfg, f, indent=2)


def save_secret(name, password):
    secrets = {}
    if os.path.exists(SECRETS):
        with open(SECRETS) as f:
            secrets = json.load(f)
    secrets[name] = password
    with open(SECRETS, "w") as f:
        json.dump(secrets, f, indent=2)
    os.chmod(SECRETS, 0o600)


def resolve(name=None):
    cfg, secrets = load_config()
    name = name or cfg.get("default", "demo")
    conns = cfg.get("connections", {})
    if name not in conns:
        raise SystemExit(f"Unknown connection '{name}'. Known: {', '.join(conns)}")
    conn = dict(conns[name])
    conn["name"] = name
    conn["password"] = secrets.get(name)
    return conn


def _psql_argv(conn, db, fmt_args, sql):
    argv = ["docker", "exec", "-i"]
    # Force the whole session read-only at connection startup (emits no output,
    # unlike a SET statement). Belt-and-suspenders with the keyword allowlist.
    argv += ["-e", "PGOPTIONS=-c default_transaction_read_only=on"]
    if conn.get("mode") == "remote" and conn.get("password"):
        argv += ["-e", f"PGPASSWORD={conn['password']}"]
    argv += [CLIENT_CONTAINER, "psql", "-v", "ON_ERROR_STOP=1", "-U", conn["user"], "-d", db]
    if conn.get("mode") == "remote":
        argv += ["-h", str(conn.get("host", "localhost")), "-p", str(conn.get("port", 5432))]
    argv += fmt_args + ["-c", sql]
    return argv


def _check_readonly(sql: str):
    head = sql.lstrip().lstrip("(").lstrip().split(None, 1)
    kw = head[0].lower() if head else ""
    if kw not in _READ_OK:
        raise SystemExit(f"Refused: only read-only queries allowed (got '{kw or sql[:20]}').")


def _run(conn, db, fmt_args, sql, check=True):
    argv = _psql_argv(conn, db, fmt_args, sql)
    r = subprocess.run(argv, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise SystemExit(f"psql error:\n{r.stderr or r.stdout}")
    return r


def run_scalar(conn, sql, db=None):
    _check_readonly(sql)
    db = db or conn["dbname"]
    r = _run(conn, db, ["-tA"], sql)
    return (r.stdout or "").strip()


def run_rows(conn, sql, db=None):
    """Return list of dict rows (CSV-parsed)."""
    _check_readonly(sql)
    db = db or conn["dbname"]
    r = _run(conn, db, ["--csv"], sql)
    text = r.stdout or ""
    if not text.strip():
        return []
    reader = csv.DictReader(io.StringIO(text))
    return list(reader)


def list_databases(conn):
    sql = ("SELECT datname FROM pg_database WHERE datistemplate=false "
           "AND datname NOT IN ('postgres') ORDER BY datname")
    # connect to a maintenance db that surely exists
    maint = conn.get("dbname") or ("postgres" if conn.get("mode") == "remote" else "postgres")
    r = _run(conn, maint, ["-tA"], sql, check=False)
    if r.returncode != 0:
        # fall back to listing including postgres
        r = _run(conn, "postgres", ["-tA"], sql, check=False)
    return [x for x in (r.stdout or "").splitlines() if x.strip()]


def resolve_dbname(conn):
    """Return the concrete dbname to introspect. For the demo connection with no
    dbname, auto-pick the single erp_* database (or list candidates to choose)."""
    if conn.get("dbname"):
        return conn["dbname"]
    dbs = list_databases(conn)
    erp = [d for d in dbs if d.startswith("erp_")]
    pool = erp or dbs
    if len(pool) == 1:
        return pool[0]
    raise SystemExit(
        "Multiple databases found; pass --dbname. Candidates: " + ", ".join(pool))


def safe_label(conn, db):
    return db or conn.get("dbname") or conn["name"]
