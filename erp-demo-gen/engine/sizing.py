"""Turn intake answers (spec.json) into a concrete CompanyProfile.

The spec is deliberately forgiving: the user may give revenue, invoice count,
employees, or just a size band. We derive everything else from industry tuning
defaults so the engine always has concrete numbers to generate against.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date

from .util import add_months


SIZE_BANDS = {
    # band -> (annual_revenue_usd, annual_invoices, employees)
    "small": (3_000_000, 1_200, 25),
    "medium": (40_000_000, 12_000, 180),
    "large": (350_000_000, 90_000, 1400),
}


@dataclass
class CompanyProfile:
    company_name: str
    slug: str
    industry: str
    currency: str
    seed: int

    start_year: int
    years: int

    annual_revenue: float          # revenue in the final (most recent) year
    annual_invoices: int           # sales orders/invoices in the final year
    employees: int

    growth_rate: float             # YoY compound growth (0.10 = 10%)
    seasonality: list              # 12 monthly multipliers, mean ~1.0
    return_rate: float
    overdue_rate: float
    avg_margin: float

    n_customers: int
    n_vendors: int
    n_products: int
    n_warehouses: int
    n_work_centers: int

    avg_order_value: float
    lines_per_order_mean: float

    tables: list = field(default_factory=list)

    def end_year(self) -> int:
        return self.start_year + self.years - 1

    def year_revenue(self, year_index: int) -> float:
        """Revenue for year ``year_index`` (0 = oldest), compounding up to the
        final year's ``annual_revenue``."""
        # final year index = years-1 has the full annual_revenue
        delta = (self.years - 1) - year_index
        return self.annual_revenue / ((1 + self.growth_rate) ** delta)

    def year_invoices(self, year_index: int) -> int:
        delta = (self.years - 1) - year_index
        return max(1, int(round(self.annual_invoices / ((1 + self.growth_rate) ** delta))))

    def as_dict(self) -> dict:
        return asdict(self)


def _slugify(name: str) -> str:
    s = "".join(c if (c.isalnum() or c == " ") else " " for c in name.lower())
    return "_".join(s.split())[:40] or "company"


def build_profile(spec: dict, tuning: dict, tables: list) -> CompanyProfile:
    industry = spec["industry"]
    band = spec.get("size_band", "medium")
    band_rev, band_inv, band_emp = SIZE_BANDS.get(band, SIZE_BANDS["medium"])

    annual_revenue = float(spec.get("annual_revenue") or band_rev)
    annual_invoices = int(spec.get("annual_invoices") or band_inv)
    employees = int(spec.get("employees") or band_emp)

    avg_order_value = annual_revenue / max(1, annual_invoices)

    years = int(spec.get("years", 5))
    end_year = int(spec.get("end_year", date.today().year))
    start_year = end_year - years + 1

    growth_rate = float(spec.get("growth_rate", tuning.get("growth_rate", 0.10)))
    seasonality = spec.get("seasonality") or tuning.get("seasonality") or [1.0] * 12
    # normalise seasonality to mean 1.0 so annual totals stay on target
    s_mean = sum(seasonality) / 12.0
    seasonality = [round(x / s_mean, 4) for x in seasonality]

    # Entity counts scale with sqrt of revenue ratio vs the medium band so they
    # grow sub-linearly (a 10x bigger company doesn't have 10x the SKUs).
    scale = (annual_revenue / SIZE_BANDS["medium"][0]) ** 0.5

    def scaled(base: int, lo: int) -> int:
        return max(lo, int(round(base * scale)))

    counts = tuning.get("counts", {})
    n_customers = int(spec.get("n_customers") or scaled(counts.get("customers", 400), 15))
    n_vendors = int(spec.get("n_vendors") or scaled(counts.get("vendors", 80), 8))
    n_products = int(spec.get("n_products") or scaled(counts.get("products", 250), 12))
    n_warehouses = int(spec.get("n_warehouses") or counts.get("warehouses", 2))
    n_work_centers = int(spec.get("n_work_centers") or counts.get("work_centers", 6))

    return CompanyProfile(
        company_name=spec["company_name"],
        slug=spec.get("slug") or _slugify(spec["company_name"]),
        industry=industry,
        currency=spec.get("currency", "USD"),
        seed=int(spec.get("seed", 42)),
        start_year=start_year,
        years=years,
        annual_revenue=annual_revenue,
        annual_invoices=annual_invoices,
        employees=employees,
        growth_rate=growth_rate,
        seasonality=seasonality,
        return_rate=float(spec.get("return_rate", tuning.get("return_rate", 0.04))),
        overdue_rate=float(spec.get("overdue_rate", tuning.get("overdue_rate", 0.12))),
        avg_margin=float(spec.get("avg_margin", tuning.get("avg_margin", 0.32))),
        n_customers=n_customers,
        n_vendors=n_vendors,
        n_products=n_products,
        n_warehouses=n_warehouses,
        n_work_centers=n_work_centers,
        avg_order_value=avg_order_value,
        lines_per_order_mean=float(tuning.get("lines_per_order_mean", 3.0)),
        tables=tables,
    )
