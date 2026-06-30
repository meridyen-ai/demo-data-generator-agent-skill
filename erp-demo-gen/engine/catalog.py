"""Industry config loading and table selection.

Industry behaviour lives in industries/<industry>/{tables.json,tuning.json,notes.md}
which are the editable "learning" surface. tables.json lists the tables that
industry should include; we intersect with the canonical TABLE_ORDER so the
create/load order stays valid regardless of how the JSON is written.
"""
from __future__ import annotations

import json
import os

from . import ddl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDUSTRIES_DIR = os.path.join(ROOT, "industries")

ALIASES = {
    "discrete manufacturing": "manufacturing",
    "manufacturing": "manufacturing",
    "wholesale": "wholesale",
    "distribution": "wholesale",
    "wholesale/distribution": "wholesale",
    "retail": "retail",
    "e-commerce": "retail",
    "retail/e-commerce": "retail",
    "food & beverage": "food_beverage",
    "food and beverage": "food_beverage",
    "food_beverage": "food_beverage",
    "process manufacturing": "food_beverage",
}


def resolve_industry(name: str) -> str:
    key = name.strip().lower()
    return ALIASES.get(key, key.replace(" ", "_").replace("/", "_"))


def industry_path(industry: str) -> str:
    return os.path.join(INDUSTRIES_DIR, industry)


def load_industry(industry: str):
    """Return (tables_cfg, tuning_cfg) dicts for the resolved industry."""
    industry = resolve_industry(industry)
    path = industry_path(industry)
    if not os.path.isdir(path):
        raise SystemExit(
            f"Unknown industry '{industry}'. Available: "
            + ", ".join(sorted(os.listdir(INDUSTRIES_DIR)))
        )
    with open(os.path.join(path, "tables.json")) as f:
        tables_cfg = json.load(f)
    with open(os.path.join(path, "tuning.json")) as f:
        tuning_cfg = json.load(f)
    return industry, tables_cfg, tuning_cfg


def select_tables(tables_cfg: dict) -> list:
    """Filter canonical order to the industry's included set."""
    included = set(tables_cfg.get("include", []))
    excluded = set(tables_cfg.get("exclude", []))
    selected = [t for t in ddl.TABLE_ORDER if t in included and t not in excluded]
    missing = included - set(ddl.TABLE_ORDER)
    if missing:
        raise SystemExit(f"tables.json includes unknown tables: {sorted(missing)}")
    return selected
