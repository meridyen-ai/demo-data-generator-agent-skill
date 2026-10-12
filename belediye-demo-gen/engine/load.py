# -*- coding: utf-8 -*-
"""Uretilen semayi ve CSV'leri calisan erp_demo_pg konteynerine yukler.

Host tarafinda psql/psycopg gerekmez; her sey `docker exec` uzerinden yapilir.
CSV'ler client-side \\copy ile STDIN'den akitilir, bu yuzden konteynere
volume mount edilmis olmalari gerekmez.
"""
from __future__ import annotations

import os
import subprocess
import time

CONTAINER = "erp_demo_pg"
PG_USER = "demo"
PG_PASSWORD = "demo"
PG_PORT = 5544


def _docker(args, input_bytes=None, check=True):
    return subprocess.run(["docker", *args], input=input_bytes,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          check=check)


def container_hazir_mi():
    r = _docker(["ps", "--filter", f"name=^{CONTAINER}$", "--format", "{{.Status}}"],
                check=False)
    durum = (r.stdout or b"").decode().strip()
    return durum.startswith("Up"), durum


def bekle_hazir(timeout=60):
    son = time.time() + timeout
    while time.time() < son:
        r = _docker(["exec", CONTAINER, "pg_isready", "-U", PG_USER, "-d", "postgres"],
                    check=False)
        if r.returncode == 0:
            return True
        time.sleep(2)
    return False


def psql(db, sql=None, stdin=None, check=True, quiet=False):
    args = ["exec", "-i", CONTAINER, "psql", "-U", PG_USER, "-d", db,
            "-v", "ON_ERROR_STOP=1"]
    if quiet:
        args += ["-t", "-A"]
    if sql is not None:
        args += ["-c", sql]
    r = _docker(args, input_bytes=stdin, check=False)
    cikti = (r.stdout or b"").decode(errors="replace")
    if check and r.returncode != 0:
        raise SystemExit(f"psql hatasi (db={db}):\n{cikti}")
    return cikti


def veritabani_olustur(db):
    psql("postgres", sql=(
        f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
        f"WHERE datname = '{db}' AND pid <> pg_backend_pid();"), check=False)
    psql("postgres", sql=f'DROP DATABASE IF EXISTS "{db}";')
    psql("postgres", sql=f'CREATE DATABASE "{db}" ENCODING \'UTF8\';')


def sql_dosyasi_calistir(db, yol):
    with open(yol, "rb") as f:
        return psql(db, stdin=f.read())


def csv_yukle(db, tablo_adi, csv_yolu):
    komut = (f"\\copy {tablo_adi} FROM STDIN WITH "
             f"(FORMAT csv, HEADER true, NULL '')")
    args = ["exec", "-i", CONTAINER, "psql", "-U", PG_USER, "-d", db,
            "-v", "ON_ERROR_STOP=1", "-c", komut]
    with open(csv_yolu, "rb") as f:
        r = _docker(args, input_bytes=f.read(), check=False)
    if r.returncode != 0:
        raise SystemExit(f"{tablo_adi} yuklenemedi:\n{(r.stdout or b'').decode(errors='replace')}")


def deger(db, sql):
    return psql(db, sql=sql, quiet=True).strip()


def baglanti_dizesi(db):
    return f"postgresql://{PG_USER}:{PG_PASSWORD}@localhost:{PG_PORT}/{db}"
