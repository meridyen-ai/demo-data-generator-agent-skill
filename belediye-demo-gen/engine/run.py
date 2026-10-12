# -*- coding: utf-8 -*-
"""belediye-demo-gen CLI.

Kullanim:
    python3 -m engine.run build   [--slug bahcelievler] [--seed 20260831] [--no-load]
    python3 -m engine.run load    [--slug bahcelievler]
    python3 -m engine.run summary [--slug bahcelievler]
"""
from __future__ import annotations

import argparse
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine import (gen_base, gen_people, gen_hr, gen_econ, gen_property,   # noqa: E402
                    gen_finance, gen_services, gen_social, gen_civic, gen_gov)
from engine import load as L                                               # noqa: E402
from engine import schema, views, util as U                                # noqa: E402
from engine.spec import REGISTRY                                           # noqa: E402
from engine.world import World                                             # noqa: E402

ASAMALAR = [
    ("referans veriler (mahalle, sokak, müdürlük, tesis, tedarikçi)", gen_base),
    ("nüfus, hane, vatandaş, doğum, ölüm, göç, nikah", gen_people),
    ("personel, bordro, izin, mesai, eğitim", gen_hr),
    ("işsizlik, işyeri, ruhsat, denetim, kurslar", gen_econ),
    ("bina, bağımsız bölüm, emlak vergisi, ÇTV, ilan-reklam", gen_property),
    ("bütçe, gelir, gider, ihale, sözleşme, ödeme emri", gen_finance),
    ("imar, zabıta, fen işleri, filo, temizlik, çevre", gen_services),
    ("sosyal yardım, sağlık, veteriner, kültür, spor", gen_social),
    ("çözüm merkezi başvuruları ve anketler", gen_civic),
    ("meclis, encümen, seçim, mezarlık, otopark, acil durum", gen_gov),
]


def out_dir(slug):
    return os.path.join(ROOT, "out", slug)


def db_adi(slug):
    return f"bld_{slug}"


def build(slug, seed, load_et=True):
    klasor = out_dir(slug)
    os.makedirs(klasor, exist_ok=True)
    depo = U.Depo(klasor)
    w = World(seed, depo)

    t0 = time.time()
    for ad, modul in ASAMALAR:
        t = time.time()
        modul.uret(w)
        print(f"  ✓ {ad}  ({time.time() - t:.1f} sn)")
    sayim = depo.kapat_hepsi()
    toplam = sum(sayim.values())
    print(f"  → {len(sayim)} tablo, {toplam:,} satır CSV üretildi "
          f"({time.time() - t0:.1f} sn)".replace(",", "."))

    with open(os.path.join(klasor, "schema.sql"), "w", encoding="utf-8") as f:
        f.write(schema.schema_sql())
    with open(os.path.join(klasor, "constraints.sql"), "w", encoding="utf-8") as f:
        f.write(schema.constraints_sql())
    with open(os.path.join(klasor, "views.sql"), "w", encoding="utf-8") as f:
        f.write(views.views_sql())

    if load_et:
        yukle(slug)
    return sayim


def yukle(slug):
    db = db_adi(slug)
    klasor = out_dir(slug)
    up, durum = L.container_hazir_mi()
    if not up:
        raise SystemExit(f"'{L.CONTAINER}' konteyneri çalışmıyor (durum: {durum or 'yok'}). "
                         f"Önce `docker start {L.CONTAINER}` çalıştırın.")
    if not L.bekle_hazir():
        raise SystemExit("Postgres hazır duruma gelmedi.")
    print(f"  · konteyner: {L.CONTAINER} ({durum})")

    L.veritabani_olustur(db)
    L.sql_dosyasi_calistir(db, os.path.join(klasor, "schema.sql"))
    print(f"  ✓ şema oluşturuldu ({len(REGISTRY)} tablo)")

    for i, t in enumerate(REGISTRY, 1):
        yol = os.path.join(klasor, t.name + ".csv")
        if not os.path.exists(yol):
            continue
        L.csv_yukle(db, t.name, yol)
        if i % 15 == 0 or i == len(REGISTRY):
            print(f"  · {i}/{len(REGISTRY)} tablo yüklendi")

    L.sql_dosyasi_calistir(db, os.path.join(klasor, "constraints.sql"))
    print("  ✓ yabancı anahtarlar, indeksler ve ANALYZE tamam")
    L.sql_dosyasi_calistir(db, os.path.join(klasor, "views.sql"))
    n_view = L.deger(db, "SELECT count(*) FROM information_schema.views "
                         "WHERE table_schema='public';")
    print(f"  ✓ {n_view} analitik view oluşturuldu")
    ozet(slug)


def ozet(slug):
    db = db_adi(slug)
    satir = L.deger(db, """
        SELECT sum(n_live_tup)::bigint FROM pg_stat_user_tables;""")
    boyut = L.deger(db, "SELECT pg_size_pretty(pg_database_size(current_database()));")
    print()
    print(f"  Veritabanı : {db}")
    print(f"  Bağlantı   : {L.baglanti_dizesi(db)}")
    print(f"  Konteyner  : postgresql://demo:demo@{L.CONTAINER}:5432/{db}")
    print(f"  Satır      : {satir}")
    print(f"  Boyut      : {boyut}")


def main():
    ap = argparse.ArgumentParser(prog="belediye-demo-gen")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for ad in ("build", "load", "summary"):
        p = sub.add_parser(ad)
        p.add_argument("--slug", default="bahcelievler")
        if ad == "build":
            p.add_argument("--seed", type=int, default=20260831)
            p.add_argument("--no-load", action="store_true")
    a = ap.parse_args()
    if a.cmd == "build":
        build(a.slug, a.seed, load_et=not a.no_load)
    elif a.cmd == "load":
        yukle(a.slug)
    else:
        ozet(a.slug)


if __name__ == "__main__":
    main()
