"""Generator for a used machine-tool dealer (industry: machinery_dealer).

Differs from the generic wholesale path in ways that matter for the demo:

* **Serialized stock.** A used machine is a unique physical unit with its own
  acquisition cost, inbound transport, refurbishment spend and landed cost, so
  COGS is per-unit rather than per-SKU. ``machine_units`` carries that.
* **Two order archetypes.** A machine deal (one high-value serialized line plus
  a tooling/service package) behaves nothing like a parts order; mixing them in
  one value distribution produces nonsense quantities.
* **Multi-currency.** EUR base, with EU/TR/UK/CH trade in local currency and a
  daily ``fx_rates`` table, so every document stores both original and base
  amounts and FX gain/loss is derivable.
* **Revenue is driven to an explicit per-year target curve** (which rises and
  falls) rather than smooth compound growth.
"""
from __future__ import annotations

from datetime import date

from . import locales
from .gen_backoffice import BackOfficeMixin
from .generators import Gen, WeightedPicker
from .util import money, add_days, add_months, random_date_in_month, days_in_month

# Units of the quoted currency per 1 EUR, one anchor per calendar year.
FX_ANCHORS = {
    "USD": [1.130, 1.180, 1.120, 1.142, 1.183, 1.053, 1.081, 1.082, 1.093, 1.101],
    "TRY": [4.12, 5.71, 6.36, 8.05, 10.46, 17.48, 29.48, 37.55, 45.20, 53.40],
    "GBP": [0.876, 0.885, 0.878, 0.890, 0.860, 0.853, 0.870, 0.847, 0.840, 0.838],
    "CHF": [1.112, 1.155, 1.113, 1.071, 1.081, 1.005, 0.972, 0.939, 0.932, 0.936],
    "PLN": [4.257, 4.261, 4.298, 4.443, 4.565, 4.686, 4.542, 4.306, 4.252, 4.221],
    "CZK": [26.33, 25.65, 25.67, 26.46, 25.64, 24.57, 24.00, 25.12, 24.80, 24.62],
    "HUF": [309.2, 318.9, 325.3, 351.2, 358.5, 391.3, 381.9, 395.3, 400.6, 405.2],
    "RON": [4.569, 4.654, 4.745, 4.838, 4.921, 4.931, 4.947, 4.974, 5.052, 5.098],
    "SEK": [9.635, 10.258, 10.589, 10.485, 10.146, 10.630, 11.479, 11.433, 11.100, 11.020],
    "DKK": [7.439, 7.453, 7.466, 7.454, 7.437, 7.440, 7.451, 7.459, 7.462, 7.460],
    "NOK": [9.327, 9.598, 9.851, 10.723, 10.163, 10.102, 11.425, 11.630, 11.480, 11.390],
    "BGN": [1.9558] * 10,
}

CURRENCY_NAMES = {
    "EUR": ("Euro", "€"), "USD": ("US Dollar", "$"), "TRY": ("Turkish Lira", "₺"),
    "GBP": ("Pound Sterling", "£"), "CHF": ("Swiss Franc", "CHF"),
    "PLN": ("Polish Zloty", "zł"), "CZK": ("Czech Koruna", "Kč"),
    "HUF": ("Hungarian Forint", "Ft"), "RON": ("Romanian Leu", "lei"),
    "SEK": ("Swedish Krona", "kr"), "DKK": ("Danish Krone", "kr"),
    "NOK": ("Norwegian Krone", "kr"), "BGN": ("Bulgarian Lev", "лв"),
}

CONDITION_GRADES = ["A - Excellent", "B - Good", "C - Fair", "D - As-is / Project"]
CONTROLS = [
    "Fanuc 0i-MF", "Fanuc 31i-B", "Fanuc 0i-TF", "Fanuc 18i-T", "Fanuc 21i-M",
    "Siemens SINUMERIK 828D", "Siemens SINUMERIK 840D sl", "Siemens SINUMERIK 810D",
    "Heidenhain TNC 640", "Heidenhain iTNC 530", "Mitsubishi M80", "Mitsubishi M700",
    "Mazatrol SmoothG", "Mazatrol Matrix 2", "Okuma OSP-P300", "Okuma OSP-P200",
    "Fagor 8065", "Selca S4045", "Haas NGC", "Bosch Rexroth MTX",
]
INCOTERMS_EU = ["EXW", "FCA", "CPT", "DAP", "DDP"]
INCOTERMS_EXPORT = ["EXW", "FCA", "FOB", "CIF", "CFR", "DAP"]


class MachineryGen(BackOfficeMixin, Gen):
    # ------------------------------------------------------------------ setup
    def __init__(self, profile, seeds, tuning, rng):
        super().__init__(profile, seeds, tuning, rng)
        self.base_ccy = tuning.get("base_currency", "EUR")
        self.start_date = date(profile.start_year, 1, 1)
        self.end_month = int(getattr(profile, "end_month", 12) or 12)
        self.machine_share = float(tuning.get("machine_revenue_share", 0.82))
        self.accessory_share = float(tuning.get("accessory_revenue_share", 0.14))
        self.service_share = float(tuning.get("service_revenue_share", 0.04))
        self._fx_cache = {}
        self._entry_no = 0

    def _today(self):
        """Deterministic 'now' = last generated day (supports a partial final year)."""
        y = self.p.end_year()
        m = self.end_month
        return date(y, m, days_in_month(y, m))

    def months(self):
        """Yield (year_index, year, month) for every generated month."""
        for yi in range(self.p.years):
            year = self.p.start_year + yi
            last = self.end_month if yi == self.p.years - 1 else 12
            for m in range(1, last + 1):
                yield yi, year, m

    # --------------------------------------------------------------------- fx
    def gen_currencies(self):
        used = [self.base_ccy] + [c for c in self.t.get("trade_currencies", []) if c != self.base_ccy]
        for code in used:
            name, sym = CURRENCY_NAMES.get(code, (code, code))
            self.add("currencies", {
                "code": code, "name": name, "symbol": sym,
                "is_base": code == self.base_ccy,
                "decimals": 0 if code in ("HUF",) else 2,
            })

    def gen_fx_rates(self):
        """Daily rates built from yearly anchors + a seeded random walk."""
        r = self.rng.stream("fx")
        end = self._today()
        n_days = (end - self.start_date).days + 1
        for cur in [c["code"] for c in self.rows("currencies")]:
            series = []
            if cur == self.base_ccy:
                series = [1.0] * n_days
            else:
                anchors = FX_ANCHORS.get(cur)
                if not anchors:
                    continue
                drift = 0.0
                for i in range(n_days):
                    d = add_days(self.start_date, i)
                    yi = d.year - self.p.start_year
                    a0 = anchors[min(yi, len(anchors) - 1)]
                    a1 = anchors[min(yi + 1, len(anchors) - 1)]
                    frac = (d.timetuple().tm_yday - 1) / 366.0
                    smooth = a0 + (a1 - a0) * frac
                    # mean-reverting daily noise so intra-year movement looks real
                    drift = drift * 0.985 + r.rand() * 0.006 - 0.003
                    series.append(round(smooth * (1 + drift), 6))
            self._fx_cache[cur] = series
            step = 1
            for i in range(0, n_days, step):
                rate = series[i]
                self.add("fx_rates", {
                    "id": self.nid("fx_rates"), "rate_date": add_days(self.start_date, i),
                    "currency_code": cur, "base_currency": self.base_ccy,
                    "rate_per_base": rate,
                    "base_per_unit": round(1.0 / rate, 8) if rate else None,
                })

    def fx(self, currency, d) -> float:
        """Units of `currency` per 1 unit of base currency on date `d`."""
        if currency == self.base_ccy:
            return 1.0
        series = self._fx_cache.get(currency)
        if not series:
            return 1.0
        i = (d - self.start_date).days
        i = max(0, min(i, len(series) - 1))
        return series[i]

    def to_base(self, amount, currency, d) -> float:
        return money(amount / self.fx(currency, d))

    # -------------------------------------------------------------- reference
    def gen_company(self):
        c = self.s["company"]
        self.add("company", {
            "id": 1, "name": c["name"], "legal_name": c.get("legal_name", c["name"]),
            "tagline": c.get("tagline", ""), "founded_year": c.get("founded_year", self.p.start_year - 1),
            "hq_address": c.get("hq_address", ""), "hq_city": c.get("hq_city", "Hamburg"),
            "hq_postcode": c.get("hq_postcode", ""), "hq_country": c.get("hq_country", "Germany"),
            "vat_number": c.get("vat_number", ""), "registration_no": c.get("registration_no", ""),
            "domain": c["domain"], "base_currency": self.base_ccy,
            "fiscal_year_end": "12-31", "employee_count": self.p.employees,
            "website": f"https://www.{c['domain']}", "phone": c.get("phone", ""),
        })

    def gen_tax_codes(self):
        for i, tc in enumerate(self.t.get("tax_codes", []), start=1):
            self.add("tax_codes", {
                "id": i, "code": tc["code"], "name": tc["name"],
                "rate_pct": tc["rate_pct"], "tax_type": tc.get("tax_type", "VAT"),
                "region": tc.get("region", ""), "applies_to": tc.get("applies_to", "sales"),
                "description": tc.get("description", ""),
            })

    def gen_chart_of_accounts(self):
        for a in self.s.get("chart_of_accounts", []):
            self.add("chart_of_accounts", {
                "id": self.nid("chart_of_accounts"), "account_code": a["code"],
                "account_name": a["name"], "account_type": a["type"],
                "account_subtype": a.get("subtype", ""), "normal_side": a.get("side", "debit"),
                "is_pnl": a.get("is_pnl", False), "pnl_section": a.get("pnl_section", ""),
                "parent_code": a.get("parent", None),
            })
        self._acct = {a["account_code"]: a["account_name"] for a in self.rows("chart_of_accounts")}

    def gen_expense_categories(self):
        for c in self.s.get("expense_categories", []):
            self.add("expense_categories", {
                "id": self.nid("expense_categories"), "code": c["code"], "name": c["name"],
                "expense_group": c.get("group", "Operating"), "account_code": c["account_code"],
                "is_fixed": c.get("variability_pct", 0) < 25,
                "variability_pct": c.get("variability_pct", 0),
                "is_cash": c.get("is_cash", True), "description": c.get("description", ""),
            })
        # keep the *seed* spec (annual amount, frequency, vendor types) keyed by
        # code — the generated row only carries what the table stores
        self._exp_cat = {c["code"]: c for c in self.s.get("expense_categories", [])}

    # ------------------------------------------------------------- dimensions
    def gen_departments(self):
        for d in self.s["departments"]:
            if isinstance(d, str):
                d = {"name": d}
            self.add("departments", {
                "id": self.nid("departments"), "name": d["name"],
                "cost_center": d.get("cost_center", f"CC-{1000 + self._ids['departments']}"),
            })
        self._dept_seed = {d["name"]: d for d in self.s["departments"] if isinstance(d, dict)}
        self._dept_by_name = {d["name"]: d["id"] for d in self.rows("departments")}

    def gen_warehouses(self):
        r = self.rng.stream("wh")
        for w in self.s["warehouses"]:
            self.add("warehouses", {
                "id": self.nid("warehouses"), "code": w["code"], "name": w["name"],
                "type": w.get("type", "Warehouse"), "city": w["city"],
                "state": w.get("state", ""), "country": w["country"],
                "capacity_sqft": w.get("capacity_sqft", 60000),
                "country_code": w["country_code"], "address": w.get("address", ""),
                "postcode": w.get("postcode", ""), "manager_id": None,
                "is_active": True,
                "opened_date": date(w.get("opened_year", self.p.start_year), r.randint(1, 12), 1),
                "monthly_rent": w.get("monthly_rent", 0),
            })
        self._wh_by_code = {w["code"]: w["id"] for w in self.rows("warehouses")}
        self._wh_de = [w["id"] for w in self.rows("warehouses") if w["country_code"] == "DE"]
        self._wh_tr = [w["id"] for w in self.rows("warehouses") if w["country_code"] == "TR"]

    def gen_employees(self):
        """Headcount is authored per department in seeds so the org chart is
        deliberate (a 24/21 split across the Hamburg and Tuzla payrolls)."""
        r = self.rng.stream("emp")
        self.salespeople = []
        self.technicians = []
        self._emp_by_dept = {}
        managers = {}
        emp_ccy = {"DE": self.base_ccy, "TR": "TRY"}
        for dept in self.rows("departments"):
            spec = self._dept_seed.get(dept["name"], {})
            for role_spec in spec.get("roles", []):
                for _ in range(int(role_spec.get("count", 1))):
                    eid = self.nid("employees")
                    cc = role_spec.get("country_code", "DE")
                    loc_pool = locales.TR_LOCATIONS if cc == "TR" else [
                        l for l in locales.EU_LOCATIONS if l[3] == "DE"]
                    city, region, country, iso2, phone_cc, _cur, _eu = locales.location(r, loc_pool)
                    # Turkish-founded firm: Turkish names dominate on both payrolls
                    fn, ln = locales.person(r, "tr" if r.chance(0.82) else "de")
                    hire = self._hire_date(r, role_spec)
                    gross = float(role_spec["annual_gross"]) * r.jitter(1.0, 0.09)
                    ccy = emp_ccy.get(cc, self.base_ccy)
                    if ccy == "TRY":  # TRY salaries are quoted in lira, so inflate
                        gross = gross * self.fx("TRY", self._today())
                    active, term = True, None
                    self.add("employees", {
                        "id": eid, "first_name": fn, "last_name": ln, "full_name": f"{fn} {ln}",
                        "email": f"{self._ascii(fn)}.{self._ascii(ln)}@{self.domain}".lower(),
                        "department_id": dept["id"], "role": role_spec["title"],
                        "hire_date": hire, "salary": money(gross), "is_active": active,
                        "employee_no": f"EMP-{eid:04d}", "country": country, "country_code": cc,
                        "city": city, "work_location": "Hamburg" if cc == "DE" else "Tuzla",
                        "warehouse_id": (self._wh_de[0] if cc == "DE" else self._wh_tr[0])
                                        if (self._wh_de and self._wh_tr) else None,
                        "employment_type": role_spec.get("employment_type", "Full-time"),
                        "manager_id": None, "currency": ccy, "annual_gross": money(gross),
                        "employer_cost_rate": 0.205 if cc == "DE" else 0.2275,
                        "weekly_hours": 38.5 if cc == "DE" else 45.0,
                        "termination_date": term,
                        "gender": "M" if fn in locales.TR_FIRST_M or fn in locales.DE_FIRST_M else "F",
                        "birth_year": hire.year - r.randint(22, 48),
                    })
                    self._emp_by_dept.setdefault(dept["name"], []).append(eid)
                    if role_spec.get("is_sales") and active:
                        self.salespeople.append(eid)
                    if role_spec.get("is_technician") and active:
                        self.technicians.append(eid)
                    if role_spec.get("is_manager"):
                        managers[dept["name"]] = eid
        self._add_leavers(r, managers)

        # attach reporting lines now that every manager exists
        for e in self.rows("employees"):
            dname = next(d["name"] for d in self.rows("departments") if d["id"] == e["department_id"])
            mgr = managers.get(dname)
            e["manager_id"] = mgr if mgr and mgr != e["id"] else None
        for w in self.rows("warehouses"):
            pool = self._emp_by_dept.get("Warehouse & Yard", [])
            w["manager_id"] = pool[0] if pool else None
        if not self.salespeople:
            self.salespeople = [self.rows("employees")[0]["id"]]
        if not self.technicians:
            self.technicians = [self.rows("employees")[0]["id"]]

    def _add_leavers(self, r, managers):
        """People who worked here and left. Without them the payroll history has
        no churn and every early year is understaffed."""
        churn = float(self.t.get("historical_churn_ratio", 0.35))
        current = list(self.rows("employees"))
        n = int(round(len(current) * churn))
        for _ in range(n):
            tmpl = r.choice(current)
            eid = self.nid("employees")
            cc = tmpl["country_code"]
            fn, ln = locales.person(r, "tr" if r.chance(0.82) else "de")
            hire = self._hire_date(r, {})
            term = add_days(hire, r.randint(380, 2400))
            if term >= self._today():
                term = add_days(self._today(), -r.randint(20, 900))
            if term <= hire:
                continue
            gross = money(float(tmpl["annual_gross"]) * r.jitter(0.94, 0.12))
            row = dict(tmpl)
            row.update({
                "id": eid, "first_name": fn, "last_name": ln, "full_name": f"{fn} {ln}",
                "email": f"{self._ascii(fn)}.{self._ascii(ln)}.{eid}@{self.domain}".lower(),
                "hire_date": hire, "salary": gross, "annual_gross": gross,
                "is_active": False, "termination_date": term,
                "employee_no": f"EMP-{eid:04d}",
                "gender": "M" if fn in locales.TR_FIRST_M or fn in locales.DE_FIRST_M else "F",
                "birth_year": hire.year - r.randint(22, 48),
            })
            self.add("employees", row)
            self._emp_by_dept.setdefault(
                next(d["name"] for d in self.rows("departments")
                     if d["id"] == row["department_id"]), []).append(eid)

    def _hire_date(self, r, role_spec):
        """Most of the team joined when the company scaled up; the rest trickle
        in. A uniform hire date would leave the early years staffed by a handful
        of people running a thirty-million-euro business."""
        founded = self.s["company"].get("founded_year", self.p.start_year - 1)
        years = list(range(founded, self.p.end_year() + 1))
        weights = self.t.get("hire_year_weights")
        if not weights or len(weights) != len(years):
            weights = [45, 22] + [4] * max(0, len(years) - 2)
        y = r.weighted(years, weights[:len(years)])
        d = random_date_in_month(r, y, r.randint(1, 12))
        return min(d, self._today())

    @staticmethod
    def _ascii(s: str) -> str:
        table = str.maketrans({
            "ü": "ue", "ö": "oe", "ä": "ae", "ß": "ss", "İ": "i", "ı": "i", "ş": "s",
            "Ş": "s", "ğ": "g", "Ğ": "g", "ç": "c", "Ç": "c", "Ü": "ue", "Ö": "oe",
            "Ä": "ae", "é": "e", "è": "e", "ł": "l", "ń": "n", "ż": "z", "ź": "z",
            "ą": "a", "ę": "e", "ś": "s", "ć": "c", "ř": "r", "š": "s", "č": "c",
            "ě": "e", "ů": "u", "ý": "y", "á": "a", "í": "i", "ó": "o", "ú": "u",
        })
        return "".join(ch for ch in s.translate(table) if ch.isalnum() or ch in "._-")

    def gen_customers(self):
        r = self.rng.stream("cust")
        pool = locales.EU_LOCATIONS + locales.TR_LOCATIONS
        tr_pool = locales.TR_LOCATIONS
        segs = ["SMB", "Mid-Market", "Enterprise"]
        industries = self.t.get("customer_industries", ["Steel Fabrication"])
        tr_share = float(self.t.get("turkiye_customer_share", 0.30))
        de_share = float(self.t.get("germany_customer_share", 0.22))
        de_pool = [l for l in locales.EU_LOCATIONS if l[3] == "DE"]
        other_pool = [l for l in locales.EU_LOCATIONS if l[3] != "DE"]
        # hand-written names carry their own legal form, so they must land in the
        # matching country; synthesized names get a legal form after the fact
        seeded_cc = {c["name"]: c["country_code"] for c in self.s.get("customers", [])}
        by_cc = {}
        for loc in pool:
            by_cc.setdefault(loc[3], []).append(loc)
        for raw_nm in self.s["customer_names"]:
            cid = self.nid("customers")
            forced = seeded_cc.get(raw_nm)
            if forced and by_cc.get(forced):
                loc = locales.location(r, by_cc[forced])
                nm = raw_nm
            else:
                x = r.rand()
                src = tr_pool if x < tr_share else (
                    de_pool if x < tr_share + de_share else other_pool)
                loc = locales.location(r, src)
                nm = f"{raw_nm} {locales.company_suffix(r, loc[3])}"
            city, region, country, iso2, phone_cc, cur, in_eu = loc
            seg = r.weighted(segs, [52, 34, 14])
            climit = {"SMB": 90000, "Mid-Market": 450000, "Enterprise": 2200000}[seg]
            # smaller shops still invoice in EUR when their own currency is volatile
            ccy = cur if (cur == "EUR" or r.chance(0.55)) else self.base_ccy
            created = self._spread_date(r, before_start_ok=True)
            self.add("customers", {
                "id": cid, "name": nm, "segment": seg,
                "address": locales.street_for(r, iso2), "city": city, "state": region,
                "country": country, "email": f"purchasing@{self._cust_domain(nm)}",
                "phone": locales.phone_for(r, phone_cc),
                "credit_limit": money(r.jitter(climit, 0.3)), "created_at": created,
                "country_code": iso2, "postcode": locales.postcode_for(r, iso2),
                "currency": ccy,
                "payment_terms_days": r.weighted([0, 14, 30, 45, 60, 90], [14, 12, 34, 18, 15, 7]),
                "incoterm": r.choice(INCOTERMS_EU if in_eu else INCOTERMS_EXPORT),
                "tax_regime": "Domestic DE" if iso2 == "DE" else ("Intra-EU B2B" if in_eu else "Export (non-EU)"),
                "vat_number": (f"{iso2}{r.randint(100000000, 999999999)}" if in_eu else ""),
                "industry": r.choice(industries),
                "account_manager_id": r.choice(self.salespeople),
                "is_export": iso2 != "DE", "is_intra_eu": bool(in_eu and iso2 != "DE"),
                "contact_name": "%s %s" % locales.person(r, "tr" if iso2 == "TR" else "de"),
                "first_order_date": None,
                "status": r.weighted(["Active", "Active", "Dormant", "Prospect"], [70, 15, 10, 5]),
            })
        self._customer_picker = WeightedPicker(
            [c["id"] for c in self.rows("customers")],
            [{"SMB": 1.0, "Mid-Market": 4.5, "Enterprise": 18.0}[c["segment"]] * r.lognormal(1.0, 0.55)
             for c in self.rows("customers")],
            self.rng.stream("cust_pick"))
        self._cust = {c["id"]: c for c in self.rows("customers")}

    @staticmethod
    def _cust_domain(name: str) -> str:
        s = "".join(ch for ch in name.lower() if ch.isalnum() or ch == " ").split()
        return (s[0] if s else "customer") + ".example.com"

    def gen_vendors(self):
        r = self.rng.stream("vend")
        types = self.t.get("vendor_types", ["Machine Source"])
        pool = locales.EU_LOCATIONS + locales.TR_LOCATIONS
        seeded = {v["name"]: v for v in self.s.get("vendors", [])}
        for raw_nm in self.s["vendor_names"]:
            vid = self.nid("vendors")
            meta = seeded.get(raw_nm, {})
            if meta.get("country_code"):
                cand = [l for l in pool if l[3] == meta["country_code"]]
                loc = locales.location(r, cand or pool)
                nm = raw_nm
            else:
                loc = locales.location(r, pool)
                nm = f"{raw_nm} {locales.company_suffix(r, loc[3])}"
            city, region, country, iso2, phone_cc, cur, in_eu = loc
            vtype = meta.get("type") or r.choice(types)
            self.add("vendors", {
                "id": vid, "name": nm, "category": vtype,
                "address": locales.street_for(r, iso2), "city": city, "state": region,
                "country": country, "email": f"sales@{self._cust_domain(nm)}",
                "phone": locales.phone_for(r, phone_cc),
                "lead_time_days": r.choice([3, 7, 10, 14, 21, 30, 45]),
                "created_at": self._spread_date(r, before_start_ok=True),
                "country_code": iso2, "postcode": locales.postcode_for(r, iso2),
                "currency": cur if (cur == "EUR" or r.chance(0.5)) else self.base_ccy,
                "vendor_type": vtype,
                "payment_terms_days": r.weighted([0, 14, 30, 45, 60], [22, 18, 36, 14, 10]),
                "vat_number": (f"{iso2}{r.randint(100000000, 999999999)}" if in_eu else ""),
                "rating": round(r.jitter(4.1, 0.18), 2), "contact_name": "%s %s" % locales.person(
                    r, "tr" if iso2 == "TR" else "de"),
                "status": r.weighted(["Active", "Active", "Inactive"], [80, 12, 8]),
            })
        self._vend = {v["id"]: v for v in self.rows("vendors")}
        self._vend_by_type = {}
        for v in self.rows("vendors"):
            self._vend_by_type.setdefault(v["vendor_type"], []).append(v["id"])

    def gen_carriers(self):
        r = self.rng.stream("carrier")
        for c in self.s.get("carriers", []):
            self.add("carriers", {
                "id": self.nid("carriers"), "name": c["name"],
                "carrier_type": c.get("type", "Freight Forwarder"), "mode": c.get("mode", "Road"),
                "country": c.get("country", "Germany"), "city": c.get("city", "Hamburg"),
                "scac": c.get("scac", ""), "is_customs_broker": c.get("is_customs_broker", False),
                "email": f"ops@{self._cust_domain(c['name'])}",
                "phone": locales.phone_for(r, "49"),
            })
        self._carriers_by_mode = {}
        for c in self.rows("carriers"):
            self._carriers_by_mode.setdefault(c["mode"], []).append(c["id"])
        self._brokers = [c["id"] for c in self.rows("carriers") if c["is_customs_broker"]]

    # --------------------------------------------------------------- products
    def gen_products(self):
        r = self.rng.stream("prod")
        self.machine_products = []
        self.accessory_products = []
        self.service_products = []

        for m in self.s["machines"]:
            pid = self.nid("products")
            row = {
                "id": pid, "sku": f"MCH-{pid:05d}",
                "name": f"{m['manufacturer']} {m['model']}", "category": m["category"],
                "uom": "unit", "unit_cost": float(m["cost_min"]),
                "list_price": round(float(m["cost_min"]) / (1 - float(m.get("margin_pct", 17)) / 100.0), 2),
                "is_active": True, "created_at": date(self.p.start_year, 1, 1),
                "item_type": "machine", "subcategory": m.get("subcategory", m["category"]),
                "brand": m["manufacturer"], "condition": "Used",
                "weight_kg": m.get("weight_kg", 5000), "hs_code": m.get("hs_code", "8458.11"),
                "origin_country": m.get("origin_country", "DE"),
                "lead_time_days": 0, "is_stocked": True, "reorder_point": 0,
                "target_margin_pct": float(m.get("margin_pct", 17)),
            }
            self.add("products", row)
            row["_cost_min"] = float(m["cost_min"])
            row["_cost_max"] = float(m["cost_max"])
            row["_popularity"] = float(m.get("popularity", 1.0))
            row["_manufacturer"] = m["manufacturer"]
            row["_model"] = m["model"]
            row["_year_min"] = int(m.get("year_min", 1998))
            row["_year_max"] = int(m.get("year_max", 2020))
            row["_power_kw"] = float(m.get("power_kw", 15))
            row["_controls"] = m.get("controls") or CONTROLS
            self.machine_products.append(row)

        for a in self.s["accessories"]:
            for variant in self._variants(a):
                pid = self.nid("products")
                is_service = a.get("item_type") == "service"
                lo, hi = float(a["cost_min"]), float(a["cost_max"])
                unit_cost = round(lo + r.rand() * max(hi - lo, 0.01), 4)
                margin = float(a.get("margin_pct", 31)) / 100.0
                row = {
                    "id": pid, "sku": f"{'SRV' if is_service else 'ACC'}-{pid:05d}",
                    "name": variant, "category": a["category"], "uom": a.get("uom", "ea"),
                    "unit_cost": unit_cost,
                    "list_price": round(unit_cost / (1 - min(max(margin, 0.05), 0.85)), 4),
                    "is_active": r.chance(0.97), "created_at": self._spread_date(r, True),
                    "item_type": "service" if is_service else a.get("item_type", "accessory"),
                    "subcategory": a.get("subcategory", a["category"]),
                    "brand": a.get("brand", ""), "condition": a.get("condition", "New"),
                    "weight_kg": a.get("weight_kg", 2), "hs_code": a.get("hs_code", "8466.93"),
                    "origin_country": a.get("origin_country", "DE"),
                    "lead_time_days": r.choice([0, 2, 5, 7, 14, 21]),
                    "is_stocked": not is_service,
                    "reorder_point": 0 if is_service else r.choice([0, 2, 5, 10, 20]),
                    "target_margin_pct": float(a.get("margin_pct", 31)),
                }
                self.add("products", row)
                row["_popularity"] = float(a.get("popularity", 1.0))
                (self.service_products if is_service else self.accessory_products).append(row)

        self._product_by_id = {p["id"]: p for p in self.rows("products")}
        self._machine_picker = WeightedPicker(
            [p["id"] for p in self.machine_products],
            [p["_popularity"] * r.lognormal(1.0, 0.5) for p in self.machine_products],
            self.rng.stream("mch_pick"))
        # Cheap consumables are ordered constantly; a coordinate measuring
        # machine is ordered once a quarter. Damping by price keeps a normal
        # parts order looking like inserts and collets rather than capex.
        self._accessory_picker = WeightedPicker(
            [p["id"] for p in self.accessory_products],
            [p["_popularity"] * r.lognormal(1.0, 0.85)
             / (1.0 + p["list_price"] / 1500.0) ** 0.55
             for p in self.accessory_products],
            self.rng.stream("acc_pick"))
        self._service_picker = WeightedPicker(
            [p["id"] for p in self.service_products],
            [p["_popularity"] * r.lognormal(1.0, 0.4) for p in self.service_products],
            self.rng.stream("srv_pick"))
        self._product_picker = self._accessory_picker  # base-class compatibility

    @staticmethod
    def _variants(a: dict):
        """Expand an accessory into its real variant axis (taper, size, grade)."""
        vs = a.get("variants") or []
        if not vs:
            return [a["name"]]
        return [f"{a['name']} {v}" for v in vs]

    # ------------------------------------------------------------------ sales
    def gen_sales(self):
        """Drive revenue to the authored per-year curve, split across three
        revenue streams, using two very different order archetypes."""
        r = self.rng.stream("sales")
        self.machine_units_sold = []
        self._deal_index = []            # (order, invoice, [unit rows]) for later modules
        # Orders are lumpy, so a month almost always overshoots its slice of the
        # target. Carrying the overshoot into the next month keeps the annual
        # totals on the authored curve instead of drifting a few per cent high.
        carry = {"machine": 0.0, "accessory": 0.0, "service": 0.0}

        for yi, year, m in self.months():
            year_target = self.p.revenue_for_year(yi)
            share = self.p.seasonality[m - 1] / 12.0
            month_target = year_target * share
            self._month_sales(r, year, m, carry,
                              month_target * self.machine_share,
                              month_target * self.accessory_share,
                              month_target * self.service_share)

    def _month_sales(self, r, year, month, carry, machine_target, acc_target, svc_target):
        machine_target = max(0.0, machine_target - carry["machine"])
        acc_target = max(0.0, acc_target - carry["accessory"])
        svc_target = max(0.0, svc_target - carry["service"])
        acc_spent = svc_spent = machine_spent = 0.0
        guard = 0
        while machine_spent < machine_target and guard < 400:
            guard += 1
            got = self._machine_deal(r, year, month)
            machine_spent += got[0]
            acc_spent += got[1]
            svc_spent += got[2]
        guard = 0
        while acc_spent < acc_target and guard < 900:
            guard += 1
            acc_spent += self._parts_order(r, year, month, acc_target)
        guard = 0
        while svc_spent < svc_target and guard < 600:
            guard += 1
            svc_spent += self._service_order(r, year, month, svc_target)
        carry["machine"] = machine_spent - machine_target
        carry["accessory"] = acc_spent - acc_target
        carry["service"] = svc_spent - svc_target

    # --- order archetype 1: machine deal ------------------------------------
    def _machine_deal(self, r, year, month):
        cust = self._cust[self._customer_picker.pick()]
        odate = random_date_in_month(r, year, month)
        if odate > self._today():
            odate = self._today()
        ccy = cust["currency"]
        rate = self.fx(ccy, odate)
        lines = []
        machine_base = acc_base = svc_base = 0.0

        n_machines = r.weighted([1, 2, 3], [86, 11, 3])
        units = []
        for _ in range(n_machines):
            unit = self._acquire_unit(r, odate)
            units.append(unit)
            machine_base += unit["sale_price_base"]
            lines.append({
                "line_type": "machine", "product_id": unit["product_id"],
                "machine_unit_id": unit["id"], "qty": 1,
                "price_base": unit["sale_price_base"], "cost_base": unit["landed_cost"],
                "description": (f"{unit['manufacturer']} {unit['model']} "
                                f"({unit['year_built']}) S/N {unit['serial_no']}"),
                "discount_pct": 0.0,
            })

        # tooling / accessory package attached to the machine
        if r.chance(0.50):
            for _ in range(r.randint(2, 6)):
                p = self._product_by_id[self._accessory_picker.pick()]
                qty = self._acc_qty(r, p["list_price"])
                disc = r.weighted([0.0, 0.05, 0.10, 0.15], [45, 28, 18, 9])
                price_base = round(p["list_price"] * r.jitter(1.0, 0.05), 4)
                gross = price_base * qty * (1 - disc)
                acc_base += gross
                lines.append({
                    "line_type": "accessory", "product_id": p["id"], "machine_unit_id": None,
                    "qty": qty, "price_base": price_base, "cost_base": p["unit_cost"] * qty,
                    "description": p["name"], "discount_pct": disc,
                })
        # commissioning / transport / training
        if r.chance(0.62):
            for _ in range(r.randint(1, 2)):
                p = self._product_by_id[self._service_picker.pick()]
                qty = 1 if r.chance(0.82) else max(1, r.poisson(1.5))
                price_base = round(p["list_price"] * r.jitter(1.0, 0.08), 4)
                svc_base += price_base * qty
                lines.append({
                    "line_type": "service", "product_id": p["id"], "machine_unit_id": None,
                    "qty": qty, "price_base": price_base, "cost_base": p["unit_cost"] * qty,
                    "description": p["name"], "discount_pct": 0.0,
                })

        oid, status = self._write_order(r, cust, odate, ccy, rate, lines, "Machine Deal", units)
        if status == "cancelled":
            return 0.0, 0.0, 0.0
        return machine_base, acc_base, svc_base

    # --- order archetype 2: parts / tooling order ---------------------------
    def _parts_order(self, r, year, month, remaining):
        cust = self._cust[self._customer_picker.pick()]
        odate = random_date_in_month(r, year, month)
        if odate > self._today():
            odate = self._today()
        ccy = cust["currency"]
        rate = self.fx(ccy, odate)
        big = r.chance(0.13)
        n_lines = r.randint(5, 16) if big else max(1, r.poisson(3.4))
        lines = []
        total_base = 0.0
        for _ in range(n_lines):
            p = self._product_by_id[self._accessory_picker.pick()]
            qty = self._acc_qty(r, p["list_price"], bulk=1.5 if big else 1.0)
            disc = r.weighted([0.0, 0.05, 0.10, 0.15, 0.20], [50, 22, 15, 9, 4])
            price_base = round(p["list_price"] * r.jitter(1.0, 0.05), 4)
            total_base += price_base * qty * (1 - disc)
            lines.append({
                "line_type": "accessory", "product_id": p["id"], "machine_unit_id": None,
                "qty": qty, "price_base": price_base, "cost_base": p["unit_cost"] * qty,
                "description": p["name"], "discount_pct": disc,
            })
        _, status = self._write_order(r, cust, odate, ccy, rate, lines,
                                      "Tooling Package" if big else "Parts Order", [])
        return 0.0 if status == "cancelled" else total_base

    # --- order archetype 3: service order -----------------------------------
    def _service_order(self, r, year, month, remaining):
        cust = self._cust[self._customer_picker.pick()]
        odate = random_date_in_month(r, year, month)
        if odate > self._today():
            odate = self._today()
        ccy = cust["currency"]
        rate = self.fx(ccy, odate)
        lines = []
        total_base = 0.0
        for _ in range(r.randint(1, 3)):
            p = self._product_by_id[self._service_picker.pick()]
            qty = 1 if r.chance(0.85) else 2
            price_base = round(p["list_price"] * r.jitter(1.0, 0.07), 4)
            total_base += price_base * qty
            lines.append({
                "line_type": "service", "product_id": p["id"], "machine_unit_id": None,
                "qty": qty, "price_base": price_base, "cost_base": p["unit_cost"] * qty,
                "description": p["name"], "discount_pct": 0.0,
            })
        _, status = self._write_order(r, cust, odate, ccy, rate, lines, "Service Order", [])
        return 0.0 if status == "cancelled" else total_base

    # --- shared order writer -------------------------------------------------
    def _write_order(self, r, cust, odate, ccy, rate, lines, order_type, units):
        oid = self.nid("sales_orders")
        tax_code, tax_rate = self._tax_for(cust)
        subtotal = discount = tax = total = cogs = 0.0
        sub_b = disc_b = tax_b = tot_b = cogs_b = 0.0
        line_no = 0
        idx = []

        for L in lines:
            line_no += 1
            lid = self.nid("sales_order_lines")
            qty = L["qty"]
            unit_price = round(L["price_base"] * rate, 4)
            unit_cost_ccy = round((L["cost_base"] / max(qty, 1)) * rate, 4)
            disc = L["discount_pct"]
            line_sub = money(qty * unit_price)
            line_disc = money(line_sub * disc)
            taxable = line_sub - line_disc
            line_tax = money(taxable * tax_rate)
            line_total = money(taxable + line_tax)
            line_cogs = money(L["cost_base"] * rate)
            line_margin = money(taxable - line_cogs)
            b_sub = money(taxable / rate)
            b_total = money(line_total / rate)
            b_cogs = money(L["cost_base"])
            self.add("sales_order_lines", {
                "id": lid, "order_id": oid, "line_no": line_no, "product_id": L["product_id"],
                "qty": qty, "unit_price": unit_price, "discount_pct": round(disc * 100, 2),
                "line_subtotal": line_sub, "tax": line_tax, "line_total": line_total,
                "unit_cost": unit_cost_ccy, "line_cogs": line_cogs, "line_margin": line_margin,
                "machine_unit_id": L["machine_unit_id"], "line_type": L["line_type"],
                "description": L["description"], "fx_rate": rate,
                "line_subtotal_base": b_sub, "line_total_base": b_total,
                "line_cogs_base": b_cogs, "line_margin_base": money(b_sub - b_cogs),
            })
            idx.append((lid, L["product_id"], qty, unit_price, line_total, L["machine_unit_id"],
                        L["line_type"]))
            subtotal += line_sub; discount += line_disc; tax += line_tax
            total += line_total; cogs += line_cogs
            sub_b += b_sub; tax_b += money(line_tax / rate); tot_b += b_total; cogs_b += b_cogs
            disc_b += money(line_disc / rate)

        recent = (odate >= add_days(self._today(), -45))
        status = r.weighted(["completed", "open", "cancelled"],
                            [8, 88, 4] if recent else [95, 2, 3])
        terms = cust["payment_terms_days"]
        self.add("sales_orders", {
            "id": oid, "order_no": f"SO-{odate.year}-{oid:06d}", "customer_id": cust["id"],
            "salesperson_id": cust["account_manager_id"] or r.choice(self.salespeople),
            "warehouse_id": self._wh_for(r, cust), "channel": self._channel(r, order_type),
            "order_date": odate, "status": status, "currency": ccy,
            "subtotal": money(subtotal), "discount": money(discount), "tax": money(tax),
            "total": money(total), "cogs": money(cogs),
            "margin": money(subtotal - discount - cogs),
            "quote_id": None, "opportunity_id": None, "order_type": order_type,
            "fx_rate": rate, "subtotal_base": money(sub_b), "discount_base": money(disc_b),
            "tax_base": money(tax_b), "total_base": money(tot_b), "cogs_base": money(cogs_b),
            "margin_base": money(sub_b - cogs_b), "incoterm": cust["incoterm"],
            "dest_country": cust["country_code"], "is_export": cust["is_export"],
            "is_intra_eu": cust["is_intra_eu"], "tax_code": tax_code,
            "payment_terms_days": terms,
            "delivery_date": add_days(odate, r.randint(5, 60) if units else r.randint(1, 14)),
        })
        if cust["first_order_date"] is None or odate < cust["first_order_date"]:
            cust["first_order_date"] = odate

        inv_id = None
        if status != "cancelled":
            inv_id = self._make_invoice_mc(r, oid, cust, odate, ccy, rate, sub_b, disc_b,
                                           tax_b, tot_b, idx, terms, recent)
        for u in units:
            u["sale_order_id"] = oid
            u["sale_invoice_id"] = inv_id
            if status == "cancelled":
                u["status"] = "in_stock"
                u["sale_order_id"] = None
                u["sale_invoice_id"] = None
                u["sale_date"] = None
                u["sale_order_line_id"] = None
                u["days_in_stock"] = (self._today() - u["acquisition_date"]).days
                u["gross_profit"] = None
                u["gross_margin_pct"] = None
                u["sale_price_base"] = None
            else:
                for (lid, pid, qty, up, lt, muid, ltype) in idx:
                    if muid == u["id"]:
                        u["sale_order_line_id"] = lid
        if status != "cancelled" and units:
            self._deal_index.append((oid, inv_id, cust["id"], odate, [u["id"] for u in units]))
        # returns: rare on machines, normal on parts
        if status == "completed" and idx:
            rate_ret = 0.004 if units else self.p.return_rate
            if r.chance(rate_ret):
                self._make_return_mc(r, oid, cust, odate, ccy, rate, idx)
        return oid, status

    @staticmethod
    def _acc_qty(r, price_base, bulk=1.0):
        """Order quantity for an accessory line. A box of inserts moves in tens;
        a coordinate measuring machine moves in ones."""
        if price_base < 60:
            return max(1, r.poisson(9.0 * bulk))
        if price_base < 250:
            return max(1, r.poisson(5.0 * bulk))
        if price_base < 1200:
            return max(1, r.poisson(2.4 * bulk))
        if price_base < 6000:
            return max(1, r.poisson(1.1 * bulk))
        if price_base < 25000:
            return 1 if r.chance(0.86) else 2
        return 1

    def _channel(self, r, order_type):
        if order_type == "Machine Deal":
            return r.weighted(["Direct Sales", "Online Marketplace", "Agent / Broker", "Auction Resale"],
                              [58, 22, 14, 6])
        return r.weighted(["Direct Sales", "Webshop", "Aftermarket Service"], [55, 30, 15])

    def _wh_for(self, r, cust):
        if cust["country_code"] == "TR" and self._wh_tr:
            return r.choice(self._wh_tr) if r.chance(0.75) else r.choice(self._wh_de)
        return r.choice(self._wh_de) if self._wh_de else None

    def _tax_for(self, cust):
        if cust["country_code"] == "DE":
            return "DE-VAT-19", 0.19
        if cust["is_intra_eu"]:
            return "EU-RC-0", 0.0
        return "EXP-0", 0.0

    # --------------------------------------------------------- machine units
    def _acquire_unit(self, r, sale_date):
        """Create the serialized unit behind a machine sale, backdated by the
        time it actually sat in stock."""
        # a model can only appear on the used market once it has been built,
        # so skip picks that are still too new for this sale date
        latest = sale_date.year - 1
        p = None
        for _ in range(20):
            cand = self._product_by_id[self._machine_picker.pick()]
            if cand["_year_min"] <= latest:
                p = cand
                break
        if p is None:
            pool = [q for q in self.machine_products if q["_year_min"] <= latest]
            p = r.choice(pool) if pool else self.machine_products[0]
        uid = self.nid("machine_units")
        year_built = r.randint(p["_year_min"], max(p["_year_min"],
                                                   min(p["_year_max"], latest)))
        age = sale_date.year - year_built
        grade = r.weighted(CONDITION_GRADES, [22, 46, 26, 6])
        # older + rougher machines cost less
        age_factor = max(0.32, 1.0 - age * 0.031)
        grade_factor = {"A - Excellent": 1.18, "B - Good": 1.0,
                        "C - Fair": 0.82, "D - As-is / Project": 0.58}[grade]
        base_cost = p["_cost_min"] + r.rand() * (p["_cost_max"] - p["_cost_min"])
        acq_base = money(base_cost * age_factor * grade_factor * r.jitter(1.0, 0.10))

        days_stock = int(min(720, max(12, r.lognormal(105, 0.75))))
        acq_date = add_days(sale_date, -days_stock)
        if acq_date < self.start_date:
            acq_date = add_days(self.start_date, r.randint(0, 20))
            days_stock = max(5, (sale_date - acq_date).days)

        vendor_pool = (self._vend_by_type.get("Auction House", []) +
                       self._vend_by_type.get("Insolvency Liquidator", []) +
                       self._vend_by_type.get("Machine Dealer", []) +
                       self._vend_by_type.get("End User Trade-In", []))
        vid = r.choice(vendor_pool) if vendor_pool else r.choice(list(self._vend))
        vend = self._vend[vid]
        ccy = vend["currency"]
        rate = self.fx(ccy, acq_date)

        weight = float(p["weight_kg"])
        transport_in = money(420 + weight * r.jitter(0.075, 0.35) +
                             (900 if vend["country_code"] not in ("DE",) else 0))
        refurb = 0.0 if r.chance(0.28) else money(acq_base * r.jitter(0.062, 0.55))
        other = money(acq_base * r.jitter(0.011, 0.5) + 180)
        landed = money(acq_base + transport_in + refurb + other)

        margin = min(0.44, max(0.02, r.jitter(float(p["target_margin_pct"]) / 100.0, 0.42)))
        sale_price = money(landed / (1 - margin))

        unit = {
            "id": uid, "unit_no": f"MU-{uid:06d}", "product_id": p["id"],
            "manufacturer": p["_manufacturer"], "model": p["_model"],
            "serial_no": self._serial(r, p["_manufacturer"], year_built),
            "year_built": year_built, "control_system": r.choice(p["_controls"]),
            "spindle_hours": r.randint(1200, 48000), "operating_hours": r.randint(3000, 92000),
            "condition_grade": grade, "weight_kg": weight, "power_kw": p["_power_kw"],
            "dimensions": f"{r.randint(20,72)/10:.1f} x {r.randint(15,40)/10:.1f} x {r.randint(18,35)/10:.1f} m",
            "source_type": vend["vendor_type"], "vendor_id": vid, "acquisition_po_id": None,
            "acquisition_date": acq_date, "currency": ccy, "fx_rate": rate,
            "acquisition_cost": money(acq_base * rate), "acquisition_cost_base": acq_base,
            "transport_in_cost": transport_in, "refurb_cost": refurb, "other_cost": other,
            "landed_cost": landed, "asking_price": money(sale_price * r.jitter(1.06, 0.04)),
            "status": "sold", "warehouse_id": r.choice(self._wh_de) if self._wh_de else None,
            "listed_date": add_days(acq_date, r.randint(3, 45)),
            "sale_order_id": None, "sale_order_line_id": None, "sale_invoice_id": None,
            "sale_date": sale_date, "sale_price_base": sale_price,
            "days_in_stock": days_stock,
            "gross_profit": money(sale_price - landed),
            "gross_margin_pct": round(100.0 * (sale_price - landed) / sale_price, 3),
        }
        self.add("machine_units", unit)
        self.machine_units_sold.append(unit)
        return unit

    @staticmethod
    def _serial(r, manufacturer, year):
        pre = "".join(ch for ch in manufacturer.upper() if ch.isalpha())[:3] or "MCH"
        return f"{pre}-{year}{r.randint(1000, 9999)}"

    def gen_stock_units(self):
        """Unsold machines still on the yard at the end of the period — this is
        what makes inventory valuation and stock-aging analysis meaningful."""
        r = self.rng.stream("stock_units")
        n = int(self.t.get("machines_in_stock", 140))
        today = self._today()
        for _ in range(n):
            # place the acquisition somewhere in the last ~2 years
            fake_sale = add_days(today, r.randint(1, 30))
            unit = self._acquire_unit(r, fake_sale)
            self.machine_units_sold.pop()
            unit["status"] = r.weighted(["in_stock", "reserved", "under_refurbishment"],
                                        [74, 16, 10])
            unit["sale_order_id"] = None
            unit["sale_order_line_id"] = None
            unit["sale_invoice_id"] = None
            unit["sale_date"] = None
            unit["sale_price_base"] = None
            unit["gross_profit"] = None
            unit["gross_margin_pct"] = None
            unit["days_in_stock"] = (today - unit["acquisition_date"]).days

    # ------------------------------------------------- invoicing & collection
    def _make_invoice_mc(self, r, oid, cust, odate, ccy, rate, sub_b, disc_b, tax_b, tot_b,
                         idx, terms, recent):
        iid = self.nid("invoices")
        idate = add_days(odate, r.choice([0, 1, 2, 3, 5, 8]))
        if idate > self._today():
            idate = self._today()
        due = add_days(idate, terms)
        subtotal = money(sub_b * rate)
        tax = money(tax_b * rate)
        total = money(subtotal + tax)
        today = self._today()
        dpd = (today - due).days

        if dpd <= 0:
            status, paid = ("open", 0.0) if r.chance(0.62) else ("paid", total)
        elif dpd <= 120:
            if r.chance(self.p.overdue_rate):
                status, paid = "overdue", (0.0 if r.chance(0.55) else money(total * r.rand() * 0.6))
            else:
                status, paid = "paid", total
        elif dpd <= 420:
            if r.chance(0.02):
                status, paid = "overdue", 0.0
            else:
                status, paid = "paid", total
        else:
            # anything older has been collected or written off, so it leaves AR
            status, paid = "paid", total
        balance = money(total - paid)
        if balance <= 0:
            status, balance, paid = "paid", 0.0, total

        self.add("invoices", {
            "id": iid, "invoice_no": f"INV-{idate.year}-{iid:06d}", "order_id": oid,
            "customer_id": cust["id"], "invoice_date": idate, "due_date": due,
            "status": status, "currency": ccy, "subtotal": subtotal, "tax": tax,
            "total": total, "amount_paid": paid, "balance": balance,
            "fx_rate": rate, "subtotal_base": money(sub_b), "tax_base": money(tax_b),
            "total_base": money(sub_b + tax_b), "amount_paid_base": money(paid / rate),
            "balance_base": money(balance / rate), "tax_code": self._tax_for(cust)[0],
            "payment_terms_days": terms, "dest_country": cust["country_code"],
            "days_overdue": max(0, dpd) if balance > 0 else 0,
        })
        ln = 0
        for (lid, pid, qty, up, lt, muid, ltype) in idx:
            ln += 1
            self.add("invoice_lines", {
                "id": self.nid("invoice_lines"), "invoice_id": iid, "line_no": ln,
                "product_id": pid, "qty": qty, "unit_price": up, "line_total": lt,
                "machine_unit_id": muid, "line_type": ltype,
                "description": self._product_by_id[pid]["name"],
                "line_total_base": money(lt / rate),
            })
        if paid > 0:
            pay_date = add_days(due, r.choice([-25, -12, -5, 0, 2, 6, 14, 21])
                                if status != "overdue" else r.choice([8, 20, 40, 65]))
            pay_date = max(idate, min(pay_date, today))
            prate = self.fx(ccy, pay_date)
            amount_base = money(paid / prate)
            self.add("payments", {
                "id": self.nid("payments"), "payment_no": f"PAY-{self._ids['payments']:07d}",
                "invoice_id": iid, "customer_id": cust["id"], "payment_date": pay_date,
                "method": r.weighted(["SEPA Transfer", "Wire Transfer", "Letter of Credit",
                                      "Advance Payment", "Cash"], [46, 34, 9, 9, 2]),
                "amount": paid, "currency": ccy, "fx_rate": prate,
                "amount_base": amount_base,
                "fx_gain_loss": money(amount_base - (paid / rate)),
                "days_to_pay": (pay_date - idate).days,
                "bank_account": "DE89-HASPA-MAIN" if ccy != "TRY" else "TR33-ISBANK-TRY",
            })
        return iid

    def _make_return_mc(self, r, oid, cust, odate, ccy, rate, idx):
        lid, pid, qty, up, lt, muid, ltype = r.choice(idx)
        if ltype == "machine":
            rqty = 1
        else:
            rqty = max(1, int(qty * r.choice([0.25, 0.5, 1.0])))
        refund = money(rqty * up)
        self.add("returns", {
            "id": self.nid("returns"), "return_no": f"RMA-{self._ids['returns']:06d}",
            "order_id": oid, "order_line_id": lid, "product_id": pid,
            "customer_id": cust["id"], "return_date": add_days(odate, r.randint(5, 90)),
            "qty": rqty,
            "reason": r.choice(["Damaged in transit", "Not as described", "Wrong item shipped",
                                "Incompatible with machine", "Defective on arrival",
                                "Customer cancelled project", "Late delivery"]),
            "refund_amount": refund, "machine_unit_id": muid, "currency": ccy,
            "refund_amount_base": money(refund / rate),
            "restocking_fee": money(refund * r.choice([0.0, 0.0, 0.05, 0.10])),
            "status": r.weighted(["Refunded", "Credited", "Rejected"], [70, 24, 6]),
        })

    # ------------------------------------------------------------ purchasing
    def gen_purchasing(self):
        r = self.rng.stream("purch")
        self._machine_acquisition_pos(r)
        self._accessory_pos(r)
        self._vendor_billing(r)

    def _machine_acquisition_pos(self, r):
        """Group units bought from the same source in the same month into one PO
        — dealers buy whole auction lots, not single machines."""
        buckets = {}
        for u in self.rows("machine_units"):
            key = (u["vendor_id"], u["acquisition_date"].year, u["acquisition_date"].month)
            buckets.setdefault(key, []).append(u)
        buyers = self._emp_by_dept.get("Procurement & Sourcing", []) or self.salespeople
        for (vid, y, m), units in sorted(buckets.items(), key=lambda kv: (kv[0][1], kv[0][2], kv[0][0])):
            i = 0
            while i < len(units):
                chunk = units[i:i + r.randint(1, 6)]
                i += len(chunk)
                poid = self.nid("purchase_orders")
                odate = min(u["acquisition_date"] for u in chunk)
                vend = self._vend[vid]
                ccy = vend["currency"]
                rate = self.fx(ccy, odate)
                subtotal = sub_b = 0.0
                ln = 0
                for u in chunk:
                    ln += 1
                    u["acquisition_po_id"] = poid
                    line_total = money(u["acquisition_cost_base"] * rate)
                    self.add("purchase_order_lines", {
                        "id": self.nid("purchase_order_lines"), "po_id": poid, "line_no": ln,
                        "item_type": "machine_unit", "item_id": u["product_id"], "qty": 1,
                        "unit_cost": line_total, "line_total": line_total, "received_qty": 1,
                        "machine_unit_id": u["id"],
                        "description": f"{u['manufacturer']} {u['model']} S/N {u['serial_no']}",
                        "line_total_base": u["acquisition_cost_base"],
                    })
                    subtotal += line_total
                    sub_b += u["acquisition_cost_base"]
                # intra-EU acquisitions are reverse-charged, so no input VAT
                trate = 0.19 if vend["country_code"] == "DE" else 0.0
                tax = money(subtotal * trate)
                self.add("purchase_orders", {
                    "id": poid, "po_no": f"PO-M-{odate.year}-{poid:06d}", "vendor_id": vid,
                    "warehouse_id": r.choice(self._wh_de) if self._wh_de else None,
                    "order_date": odate, "status": "received", "currency": ccy,
                    "subtotal": money(subtotal), "tax": tax, "total": money(subtotal + tax),
                    "po_type": "Machine Acquisition", "fx_rate": rate,
                    "subtotal_base": money(sub_b), "tax_base": money(tax / rate),
                    "total_base": money(sub_b + tax / rate),
                    "buyer_id": r.choice(buyers), "incoterm": r.choice(["EXW", "FCA", "DAP"]),
                    "expected_date": add_days(odate, vend["lead_time_days"]),
                    "received_date": add_days(odate, vend["lead_time_days"] + r.randint(0, 12)),
                    "origin_country": vend["country_code"],
                })

    def _accessory_pos(self, r):
        """Replenishment buying for tooling and parts. Buying is driven by the
        items actually consumed each month, not by a spend target — matching
        value but not units is how stock-on-hand ends up negative."""
        need = {}
        order_month = {o["id"]: (o["order_date"].year, o["order_date"].month)
                       for o in self.rows("sales_orders")}
        for l in self.rows("sales_order_lines"):
            if l["line_type"] != "accessory":
                continue
            ym = order_month[l["order_id"]]
            need.setdefault(ym, {})
            need[ym][l["product_id"]] = need[ym].get(l["product_id"], 0.0) + float(l["qty"])

        supplier_pool = (self._vend_by_type.get("Tooling Supplier", []) +
                         self._vend_by_type.get("Parts Distributor", []) +
                         self._vend_by_type.get("Component Manufacturer", []))
        if not supplier_pool:
            supplier_pool = list(self._vend)
        buyers = self._emp_by_dept.get("Procurement & Sourcing", []) or self.salespeople
        cover = float(self.t.get("replenishment_cover", 1.12))

        for (y, m), items in sorted(need.items()):
            pids = list(items)
            r.shuffle(pids)
            i = 0
            while i < len(pids):
                chunk = pids[i:i + r.randint(4, 9)]
                i += len(chunk)
                poid = self.nid("purchase_orders")
                odate = random_date_in_month(r, y, m)
                if odate > self._today():
                    odate = self._today()
                vid = r.choice(supplier_pool)
                vend = self._vend[vid]
                ccy = vend["currency"]
                rate = self.fx(ccy, odate)
                status = r.weighted(["received", "open", "cancelled"], [93, 5, 2])
                subtotal = sub_b = 0.0
                ln = 0
                for pid in chunk:
                    p = self._product_by_id[pid]
                    qty = max(1, int(round(items[pid] * r.jitter(cover, 0.18))))
                    unit_cost_b = round(p["unit_cost"] * r.jitter(1.0, 0.06), 4)
                    lt_b = money(qty * unit_cost_b)
                    ln += 1
                    self.add("purchase_order_lines", {
                        "id": self.nid("purchase_order_lines"), "po_id": poid, "line_no": ln,
                        "item_type": "product", "item_id": pid, "qty": qty,
                        "unit_cost": round(unit_cost_b * rate, 4),
                        "line_total": money(lt_b * rate),
                        "received_qty": qty if r.chance(0.96) else int(qty * (0.5 + r.rand() * 0.5)),
                        "machine_unit_id": None, "description": p["name"],
                        "line_total_base": lt_b,
                    })
                    subtotal += money(lt_b * rate)
                    sub_b += lt_b
                trate = 0.19 if vend["country_code"] == "DE" else 0.0
                tax = money(subtotal * trate)
                self.add("purchase_orders", {
                    "id": poid, "po_no": f"PO-A-{y}-{poid:06d}", "vendor_id": vid,
                    "warehouse_id": r.choice(self._wh_de) if self._wh_de else None,
                    "order_date": odate, "status": status, "currency": ccy,
                    "subtotal": money(subtotal), "tax": tax,
                    "total": money(subtotal + tax), "po_type": "Stock Replenishment",
                    "fx_rate": rate, "subtotal_base": money(sub_b),
                    "tax_base": money(tax / rate), "total_base": money(sub_b + tax / rate),
                    "buyer_id": r.choice(buyers),
                    "incoterm": r.choice(["EXW", "FCA", "CPT", "DAP"]),
                    "expected_date": add_days(odate, vend["lead_time_days"]),
                    "received_date": add_days(odate, vend["lead_time_days"] + r.randint(0, 9)),
                    "origin_country": vend["country_code"],
                })

    def _vendor_billing(self, r):
        """AP documents for every received PO, plus their settlement."""
        for po in self.rows("purchase_orders"):
            if po["status"] == "cancelled":
                continue
            vend = self._vend[po["vendor_id"]]
            bdate = add_days(po["order_date"], r.randint(0, 10))
            if bdate > self._today():
                bdate = self._today()
            terms = vend["payment_terms_days"]
            due = add_days(bdate, terms)
            vid_ = self.nid("vendor_invoices")
            total = po["total"]
            today = self._today()
            if due <= today:
                paid = total if r.chance(0.97) else money(total * r.rand() * 0.7)
            else:
                paid = total if r.chance(0.35) else 0.0
            balance = money(total - paid)
            status = "paid" if balance <= 0 else ("overdue" if due < today else "open")
            self.add("vendor_invoices", {
                "id": vid_, "bill_no": f"VB-{bdate.year}-{vid_:06d}", "vendor_id": po["vendor_id"],
                "po_id": po["id"], "bill_date": bdate, "due_date": due,
                "spend_category": ("Machine Acquisition" if po["po_type"] == "Machine Acquisition"
                                   else "Goods for Resale"),
                "currency": po["currency"], "fx_rate": po["fx_rate"],
                "subtotal": po["subtotal"], "tax": po["tax"], "total": total,
                "total_base": po["total_base"], "amount_paid": paid, "balance": balance,
                "status": status,
            })
            if paid > 0:
                pdate = add_days(due, r.choice([-8, -3, 0, 4, 11, 25]))
                pdate = max(bdate, min(pdate, today))
                prate = self.fx(po["currency"], pdate)
                self.add("vendor_payments", {
                    "id": self.nid("vendor_payments"),
                    "payment_no": f"VP-{self._ids['vendor_payments']:07d}",
                    "vendor_invoice_id": vid_, "vendor_id": po["vendor_id"],
                    "payment_date": pdate,
                    "method": r.weighted(["SEPA Transfer", "Wire Transfer", "Letter of Credit"],
                                         [58, 34, 8]),
                    "currency": po["currency"], "fx_rate": prate, "amount": paid,
                    "amount_base": money(paid / prate),
                })

    # -------------------------------------------------------- refurbishment
    def gen_refurbishment(self):
        r = self.rng.stream("refurb")
        work_types = ["Full Mechanical Overhaul", "Spindle Rebuild", "Control Retrofit",
                      "Way Cover & Guideway Repair", "Ballscrew Replacement",
                      "Coolant System Overhaul", "Electrical Cabinet Rework",
                      "Paint & Cosmetic Refurbishment", "Geometric Realignment",
                      "Tool Changer Repair", "Hydraulic System Service",
                      "Safety Guarding Upgrade"]
        techs = self.technicians or [self.rows("employees")[0]["id"]]
        for u in self.rows("machine_units"):
            if u["refurb_cost"] <= 0:
                continue
            n_jobs = r.weighted([1, 2, 3], [62, 30, 8])
            remaining = u["refurb_cost"]
            for j in range(n_jobs):
                cost = money(remaining if j == n_jobs - 1 else remaining * r.jitter(0.55, 0.3))
                remaining = money(max(0.0, remaining - cost))
                if cost <= 0:
                    continue
                labor_share = r.jitter(0.42, 0.3)
                ext_share = r.jitter(0.18, 0.6) if r.chance(0.35) else 0.0
                labor_cost = money(cost * labor_share)
                external = money(cost * min(ext_share, 0.5))
                parts = money(max(0.0, cost - labor_cost - external))
                rate_h = float(self.t.get("workshop_labor_rate", 62))
                start = add_days(u["acquisition_date"], r.randint(4, 60))
                if start > self._today():
                    start = self._today()
                self.add("refurbishment_jobs", {
                    "id": self.nid("refurbishment_jobs"),
                    "job_no": f"RF-{start.year}-{self._ids['refurbishment_jobs']:06d}",
                    "machine_unit_id": u["id"], "work_type": r.choice(work_types),
                    "start_date": start, "end_date": add_days(start, r.randint(2, 35)),
                    "technician_id": r.choice(techs),
                    "warehouse_id": u["warehouse_id"],
                    "labor_hours": round(labor_cost / rate_h, 2), "labor_rate": rate_h,
                    "labor_cost": labor_cost, "parts_cost": parts, "external_cost": external,
                    "total_cost": cost,
                    "status": r.weighted(["completed", "in_progress"], [97, 3]),
                    "notes": "",
                })
