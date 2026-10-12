# -*- coding: utf-8 -*-
"""Tablo spesifikasyonundan DDL uretir."""
from __future__ import annotations

from . import tables  # noqa: F401  (REGISTRY'yi doldurur)
from .spec import REGISTRY


def schema_sql():
    parcalar = ["-- Bahcelievler Belediyesi demo veritabani semasi",
                "-- Otomatik uretildi: belediye-demo-gen", ""]
    for t in REGISTRY:
        parcalar.append(t.ddl())
        parcalar.append("")
    return "\n".join(parcalar)


def constraints_sql():
    parcalar = ["-- Yabanci anahtarlar ve indeksler", ""]
    for t in REGISTRY:
        parcalar.extend(t.fk_ddl())
    parcalar.append("")
    for t in REGISTRY:
        parcalar.extend(t.index_ddl())
    parcalar.append("")
    for t in REGISTRY:
        parcalar.append(f"ANALYZE {t.name};")
    return "\n".join(parcalar)
