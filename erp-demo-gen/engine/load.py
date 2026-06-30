"""Bring up Docker Postgres and load a generated database via the container's
own psql/COPY. The host needs only docker + python stdlib (no psql/psycopg)."""
from __future__ import annotations

import os
import subprocess
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PG_USER = "demo"
PG_PASSWORD = "demo"
PG_PORT = 5544
CONTAINER = "erp_demo_pg"


def _compose(*args, check=True, capture=False, input_text=None):
    cmd = ["docker", "compose", *args]
    return subprocess.run(
        cmd, cwd=ROOT, check=check,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
        input=input_text, text=True,
    )


def compose_up(timeout=90):
    _compose("up", "-d")
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = _compose("exec", "-T", "postgres", "pg_isready", "-U", PG_USER, "-d", "postgres",
                     check=False, capture=True)
        if r.returncode == 0 and "accepting connections" in (r.stdout or ""):
            return True
        time.sleep(2)
    raise SystemExit("Postgres did not become ready in time. Check `docker compose logs`.")


def psql(db, sql=None, file=None, quiet_value=False, check=True):
    args = ["exec", "-T", "postgres", "psql", "-U", PG_USER, "-d", db, "-v", "ON_ERROR_STOP=1"]
    if quiet_value:
        args += ["-t", "-A"]
    if file:
        args += ["-f", file]
        return _compose(*args, check=check, capture=True)
    args += ["-c", sql]
    return _compose(*args, check=check, capture=True)


def create_database(slug):
    db = f"erp_{slug}"
    # terminate connections + drop + recreate for a clean rebuild
    psql("postgres", sql=(
        f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
        f"WHERE datname = '{db}' AND pid <> pg_backend_pid();"
    ), check=False)
    psql("postgres", sql=f'DROP DATABASE IF EXISTS "{db}";')
    psql("postgres", sql=f'CREATE DATABASE "{db}";')
    return db


def load_database(slug):
    db = create_database(slug)
    r = psql(db, file=f"/data/{slug}/load.sql")
    if r.returncode != 0:
        raise SystemExit(f"load.sql failed:\n{r.stdout}")
    return db


def query_value(db, sql):
    r = psql(db, sql=sql, quiet_value=True, check=False)
    return (r.stdout or "").strip()


def connection_string(slug):
    return f"postgresql://{PG_USER}:{PG_PASSWORD}@localhost:{PG_PORT}/erp_{slug}"
