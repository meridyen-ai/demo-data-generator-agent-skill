"""Tablo tanim DSL'i.

Tek kaynak: her tablo hem DDL'i hem de CSV kolon sirasini buradan alir.
Kolon yorumlari (COMMENT ON) snapshot/LLM tarafinin isini kolaylastirsin diye
zorunludur.
"""
from __future__ import annotations


class Col:
    __slots__ = ("name", "type", "comment")

    def __init__(self, name, type_, comment):
        self.name = name
        self.type = type_
        self.comment = comment


class Table:
    def __init__(self, name, comment, cols, pk=None, fks=(), indexes=(), checks=()):
        self.name = name
        self.comment = comment
        self.cols = [Col(*c) for c in cols]
        self.pk = pk
        self.fks = list(fks)          # (kolonlar, hedef_tablo, hedef_kolonlar)
        self.indexes = list(indexes)  # kolon ifadeleri: "mahalle_id" | "tarih, mahalle_id"
        self.checks = list(checks)

    @property
    def colnames(self):
        return [c.name for c in self.cols]

    def ddl(self):
        lines = [f'CREATE TABLE {self.name} (']
        body = [f"    {c.name} {c.type}" for c in self.cols]
        if self.pk:
            body.append(f"    PRIMARY KEY ({self.pk})")
        for ck in self.checks:
            body.append(f"    CHECK ({ck})")
        lines.append(",\n".join(body))
        lines.append(");")
        out = ["\n".join(lines)]
        out.append(f"COMMENT ON TABLE {self.name} IS {q(self.comment)};")
        for c in self.cols:
            out.append(f"COMMENT ON COLUMN {self.name}.{c.name} IS {q(c.comment)};")
        return "\n".join(out)

    def fk_ddl(self):
        out = []
        for i, (cols, ref_t, ref_c) in enumerate(self.fks, 1):
            out.append(
                f"ALTER TABLE {self.name} ADD CONSTRAINT fk_{self.name}_{i} "
                f"FOREIGN KEY ({cols}) REFERENCES {ref_t} ({ref_c});"
            )
        return out

    def index_ddl(self):
        out = []
        for i, expr in enumerate(self.indexes, 1):
            out.append(f"CREATE INDEX ix_{self.name}_{i} ON {self.name} ({expr});")
        return out


def q(s):
    return "'" + str(s).replace("'", "''") + "'"


REGISTRY = []


def T(*args, **kw):
    t = Table(*args, **kw)
    REGISTRY.append(t)
    return t


def by_name(name):
    for t in REGISTRY:
        if t.name == name:
            return t
    raise KeyError(name)
