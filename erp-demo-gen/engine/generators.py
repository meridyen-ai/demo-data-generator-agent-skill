"""Domain generators.

A single Gen object owns the run: it holds the profile, completed seeds, tuning,
the master Rng, and the growing dataset (table name -> list of row dicts). Each
generate_* method appends rows. Dimensions are generated first and kept as
in-memory lists so fact rows can reference real ids and prices, guaranteeing
foreign-key integrity and reconciling totals without touching the database.
"""
from __future__ import annotations

import bisect
from datetime import date

from . import names
from .util import Rng, money, add_days, add_months, random_date_in_month, days_in_month


class WeightedPicker:
    """O(log n) weighted sampling over a fixed population of ids."""

    def __init__(self, ids, weights, rng: Rng):
        self.ids = ids
        self.rng = rng
        self.cum = []
        acc = 0.0
        for w in weights:
            acc += w
            self.cum.append(acc)
        self.total = acc

    def pick(self):
        x = self.rng.rand() * self.total
        i = bisect.bisect_left(self.cum, x)
        if i >= len(self.ids):
            i = len(self.ids) - 1
        return self.ids[i]


class Gen:
    def __init__(self, profile, seeds, tuning, rng: Rng):
        self.p = profile
        self.s = seeds
        self.t = tuning
        self.rng = rng
        self.data = {}                  # table -> [row dicts]
        self._ids = {}                  # table -> next id
        self.selected = set(profile.tables)
        self.tax_rate = float(tuning.get("tax_rate", 0.08))
        self.domain = seeds["company"]["domain"]

    # --- low level ---
    def has(self, table) -> bool:
        return table in self.selected

    def add(self, table, row):
        self.data.setdefault(table, []).append(row)
        return row

    def nid(self, table) -> int:
        n = self._ids.get(table, 0) + 1
        self._ids[table] = n
        return n

    def rows(self, table):
        return self.data.get(table, [])

    # ================= DIMENSIONS =================
    def gen_departments(self):
        for name in self.s["departments"]:
            self.add("departments", {
                "id": self.nid("departments"), "name": name,
                "cost_center": f"CC-{1000 + self._ids['departments']}",
            })

    def gen_employees(self):
        r = self.rng.stream("emp")
        depts = self.rows("departments")
        roles = ["Specialist", "Senior Specialist", "Lead", "Manager", "Director"]
        sales_dept = next((d["id"] for d in depts if d["name"].lower().startswith("sales")), depts[0]["id"])
        self.salespeople = []
        for _ in range(self.p.employees):
            eid = self.nid("employees")
            fn, ln = names.person(r)
            dept = r.choice(depts)
            role = r.weighted(roles, [50, 25, 12, 9, 4])
            base = {"Specialist": 55000, "Senior Specialist": 72000, "Lead": 95000,
                    "Manager": 120000, "Director": 175000}[role]
            hire = self._spread_date(r, before_start_ok=True)
            active = r.chance(0.92)
            self.add("employees", {
                "id": eid, "first_name": fn, "last_name": ln, "full_name": f"{fn} {ln}",
                "email": names.email_for(fn, ln, self.domain, eid if r.chance(0.1) else 0),
                "department_id": dept["id"], "role": role, "hire_date": hire,
                "salary": money(r.jitter(base, 0.12)), "is_active": active,
            })
            if dept["id"] == sales_dept and active:
                self.salespeople.append(eid)
        if not self.salespeople:  # guarantee at least one
            self.salespeople = [self.rows("employees")[0]["id"]]

    def gen_customers(self):
        r = self.rng.stream("cust")
        segs = ["SMB", "Mid-Market", "Enterprise"]
        for nm in self.s["customer_names"]:
            cid = self.nid("customers")
            seg = r.weighted(segs, [60, 30, 10])
            street, city, state, country = names.address(r)
            climit = {"SMB": 25000, "Mid-Market": 150000, "Enterprise": 750000}[seg]
            self.add("customers", {
                "id": cid, "name": nm, "segment": seg, "address": street, "city": city,
                "state": state, "country": country,
                "email": f"ap@{names.slug_domain(nm)}", "phone": self._phone(r),
                "credit_limit": money(r.jitter(climit, 0.3)),
                "created_at": self._spread_date(r, before_start_ok=True),
            })
        # weight customers by segment so a few big accounts dominate revenue
        self._customer_picker = WeightedPicker(
            [c["id"] for c in self.rows("customers")],
            [{"SMB": 1.0, "Mid-Market": 4.0, "Enterprise": 16.0}[c["segment"]]
             * r.lognormal(1.0, 0.5) for c in self.rows("customers")],
            self.rng.stream("cust_pick"),
        )

    def gen_vendors(self):
        r = self.rng.stream("vend")
        cats = self.t.get("vendor_categories", ["Materials", "Packaging", "Logistics", "Services", "Equipment"])
        for nm in self.s["vendor_names"]:
            vid = self.nid("vendors")
            street, city, state, country = names.address(r)
            self.add("vendors", {
                "id": vid, "name": nm, "category": r.choice(cats), "address": street,
                "city": city, "state": state, "country": country,
                "email": f"sales@{names.slug_domain(nm)}", "phone": self._phone(r),
                "lead_time_days": r.choice([7, 10, 14, 21, 30, 45]),
                "created_at": self._spread_date(r, before_start_ok=True),
            })

    def gen_warehouses(self):
        r = self.rng.stream("wh")
        wtype = self.t.get("warehouse_type", "DC")
        for i in range(self.p.n_warehouses):
            city, state = names.CITIES[i % len(names.CITIES)]
            self.add("warehouses", {
                "id": self.nid("warehouses"), "code": f"WH{i+1:02d}",
                "name": f"{city} {wtype}", "type": wtype, "city": city, "state": state,
                "country": "USA", "capacity_sqft": r.choice([20000, 50000, 80000, 120000]),
            })

    def gen_work_centers(self):
        r = self.rng.stream("wc")
        wcs = self.s.get("work_centers", [])
        for i in range(max(self.p.n_work_centers, len(wcs))):
            base = wcs[i] if i < len(wcs) else {"name": f"Line {i+1}",
                                                "capacity_per_hour": 100, "cost_per_hour": 80}
            self.add("work_centers", {
                "id": self.nid("work_centers"), "code": f"WC{i+1:02d}",
                "name": base["name"],
                "capacity_per_hour": float(base.get("capacity_per_hour", 100)),
                "cost_per_hour": money(float(base.get("cost_per_hour", 80))),
                "is_active": r.chance(0.95),
            })

    def gen_products(self):
        r = self.rng.stream("prod")
        seeded = self.s["products"]
        variants = ["", " - Std", " - Pro", " - Lite", " - XL", " - Eco", " - 2-Pack",
                    " - 250ml", " - 500ml", " - 1L", " - 5kg", " - Bulk"]
        margin_default = self.p.avg_margin
        for i in range(self.p.n_products):
            base = seeded[i % len(seeded)]
            suffix = "" if i < len(seeded) else r.choice(variants[1:])
            pid = self.nid("products")
            lo = float(base.get("unit_cost_min", 1.0))
            hi = float(base.get("unit_cost_max", max(lo * 3, lo + 1)))
            unit_cost = round(lo + r.rand() * max(hi - lo, 0.01), 4)
            margin = float(base.get("margin_pct", margin_default * 100)) / 100.0
            margin = min(max(margin, 0.05), 0.85)
            list_price = round(unit_cost / (1 - margin), 4)
            self.add("products", {
                "id": pid, "sku": f"SKU-{pid:05d}",
                "name": (base["name"] + suffix)[:120], "category": base.get("category", "General"),
                "uom": base.get("uom", "ea"), "unit_cost": unit_cost, "list_price": list_price,
                "is_active": r.chance(0.96), "created_at": self._spread_date(r, before_start_ok=True),
            })
        # product popularity (Pareto-ish)
        self._product_picker = WeightedPicker(
            [p["id"] for p in self.rows("products")],
            [r.lognormal(1.0, 0.9) for _ in self.rows("products")],
            self.rng.stream("prod_pick"),
        )

    def gen_raw_materials(self):
        r = self.rng.stream("raw")
        vendors = [v["id"] for v in self.rows("vendors")]
        for base in self.s.get("raw_materials", []):
            self.add("raw_materials", {
                "id": self.nid("raw_materials"), "code": f"RM-{self._ids['raw_materials']:05d}",
                "name": base["name"], "category": base.get("category", "Material"),
                "uom": base.get("uom", "kg"),
                "unit_cost": round(float(base.get("unit_cost", r.lognormal(2.5, 0.4))), 4),
                "vendor_id": r.choice(vendors) if vendors else None,
            })

    def gen_price_list(self):
        # one price row per product per year, drifting up with inflation
        infl = float(self.t.get("inflation", 0.03))
        for p in self.rows("products"):
            for yi in range(self.p.years):
                year = self.p.start_year + yi
                factor = (1 + infl) ** (yi - (self.p.years - 1))
                self.add("price_list", {
                    "id": self.nid("price_list"), "product_id": p["id"],
                    "valid_from": date(year, 1, 1), "valid_to": date(year, 12, 31),
                    "price": round(p["list_price"] * factor, 4),
                })

    def gen_promotions(self):
        r = self.rng.stream("promo")
        cats = list({p["category"] for p in self.rows("products")})
        for yi in range(self.p.years):
            year = self.p.start_year + yi
            for _ in range(r.randint(2, 5)):
                m = r.randint(1, 12)
                start = random_date_in_month(r, year, m)
                self.add("promotions", {
                    "id": self.nid("promotions"), "code": f"PROMO{self._ids['promotions']:04d}",
                    "name": r.choice(["Spring Sale", "Summer Clearance", "Black Friday",
                                      "Holiday Deal", "Flash Sale", "Loyalty Bonus"]),
                    "category": r.choice(cats) if cats else "General",
                    "discount_pct": r.choice([5, 10, 15, 20, 25]),
                    "start_date": start, "end_date": add_days(start, r.choice([7, 14, 30])),
                })

    def gen_bom(self):
        r = self.rng.stream("bom")
        raws = [m["id"] for m in self.rows("raw_materials")]
        if not raws:
            return
        for p in self.rows("products"):
            bid = self.nid("bom")
            self.add("bom", {
                "id": bid, "product_id": p["id"], "name": f"BOM {p['sku']}",
                "version": "v1", "output_qty": 1, "is_active": True,
            })
            for rm in r.sample(raws, min(len(raws), r.randint(2, 5))):
                self.add("bom_lines", {
                    "id": self.nid("bom_lines"), "bom_id": bid, "raw_material_id": rm,
                    "qty_per": round(r.lognormal(1.5, 0.5), 4),
                    "scrap_pct": r.choice([0, 0, 1, 2, 3, 5]),
                })
        self._bom_by_product = {b["product_id"]: b["id"] for b in self.rows("bom")}

    # ================= FACTS =================
    def gen_sales(self):
        r = self.rng.stream("sales")
        products = {p["id"]: p for p in self.rows("products")}
        warehouses = [w["id"] for w in self.rows("warehouses")] or [None]
        channels = self.t.get("channels", ["Direct"])
        terms = self.t.get("payment_terms_days", [30, 45, 60])
        sigma = float(self.t.get("order_value_sigma", 0.6))

        for yi in range(self.p.years):
            year = self.p.start_year + yi
            year_orders = self.p.year_invoices(yi)
            aov = self.p.avg_order_value
            for m in range(1, 13):
                share = self.p.seasonality[m - 1] / 12.0
                n_orders = int(round(year_orders * share))
                for _ in range(n_orders):
                    self._one_sales_order(r, year, m, products, warehouses, channels, terms, aov, sigma)

    def _one_sales_order(self, r, year, month, products, warehouses, channels, terms, aov, sigma):
        oid = self.nid("sales_orders")
        odate = random_date_in_month(r, year, month)
        cust = self._customer_picker.pick()
        target = r.lognormal_mean(aov, sigma)
        n_lines = max(1, r.poisson(self.p.lines_per_order_mean))
        line_targets = self._split(r, target, n_lines)

        subtotal = discount_amt = tax_amt = total = cogs = 0.0
        line_no = 0
        order_lines_idx = []
        for lt in line_targets:
            pid = self._product_picker.pick()
            prod = products[pid]
            unit_price = round(prod["list_price"] * r.jitter(1.0, 0.06), 4)
            disc = self._discount(r)
            eff_price = unit_price * (1 - disc)
            qty = max(1, int(round(lt / max(eff_price, 0.01))))
            line_sub = money(qty * unit_price)
            line_disc = money(qty * unit_price * disc)
            taxable = line_sub - line_disc
            line_tax = money(taxable * self.tax_rate)
            line_total = money(taxable + line_tax)
            unit_cost = prod["unit_cost"]
            line_cogs = money(qty * unit_cost)
            line_margin = money(taxable - line_cogs)
            line_no += 1
            lid = self.nid("sales_order_lines")
            order_lines_idx.append((lid, pid, qty, unit_price, line_total))
            self.add("sales_order_lines", {
                "id": lid, "order_id": oid, "line_no": line_no, "product_id": pid,
                "qty": qty, "unit_price": unit_price, "discount_pct": round(disc * 100, 2),
                "line_subtotal": line_sub, "tax": line_tax, "line_total": line_total,
                "unit_cost": unit_cost, "line_cogs": line_cogs, "line_margin": line_margin,
            })
            subtotal += line_sub
            discount_amt += line_disc
            tax_amt += line_tax
            total += line_total
            cogs += line_cogs

        # order status: most fulfilled; a slice near the most recent month still open
        recent = (year == self.p.end_year() and month >= 11)
        status = r.weighted(["completed", "open", "cancelled"],
                            [10, 70, 6] if recent else [94, 3, 3])
        self.add("sales_orders", {
            "id": oid, "order_no": f"SO-{year}-{oid:06d}", "customer_id": cust,
            "salesperson_id": r.choice(self.salespeople),
            "warehouse_id": r.choice(warehouses), "channel": r.choice(channels),
            "order_date": odate, "status": status, "currency": self.p.currency,
            "subtotal": money(subtotal), "discount": money(discount_amt), "tax": money(tax_amt),
            "total": money(total), "cogs": money(cogs), "margin": money(subtotal - discount_amt - cogs),
        })
        if status != "cancelled":
            self._make_invoice(r, oid, cust, odate, subtotal, discount_amt, tax_amt, total, order_lines_idx, terms, recent)
        # returns
        if status == "completed" and r.chance(self.p.return_rate) and order_lines_idx:
            self._make_return(r, oid, cust, odate, order_lines_idx, products)

    def _make_invoice(self, r, oid, cust, odate, subtotal, discount_amt, tax_amt, total, lines_idx, terms, recent):
        iid = self.nid("invoices")
        idate = add_days(odate, r.choice([0, 1, 2, 3, 5]))
        term = r.choice(terms)
        due = add_days(idate, term)
        net = money(subtotal - discount_amt)
        gross = money(net + tax_amt)
        # Collection probability depends on age: older invoices are almost always
        # collected (or written off as a small bad-debt residue), so open/overdue
        # balances concentrate in recent periods — realistic AR aging.
        today = self._today()
        days_past_due = (today - due).days
        if days_past_due <= 0:
            # not yet due: a chunk still awaiting payment, the rest paid early
            status, paid = ("open", 0.0) if r.chance(0.5) else ("paid", gross)
        elif days_past_due <= 90:
            # recently due: overdue_rate still unpaid (some partially)
            if r.chance(self.p.overdue_rate):
                status, paid = "overdue", 0.0 if r.chance(0.5) else money(gross * r.rand() * 0.6)
            else:
                status, paid = "paid", gross
        else:
            # old: collected ~98%, small bad-debt residue stays overdue
            if r.chance(0.02):
                status, paid = "overdue", 0.0
            else:
                status, paid = "paid", gross
        balance = money(gross - paid)
        if balance <= 0:
            status = "paid"
        self.add("invoices", {
            "id": iid, "invoice_no": f"INV-{idate.year}-{iid:06d}", "order_id": oid,
            "customer_id": cust, "invoice_date": idate, "due_date": due, "status": status,
            "currency": self.p.currency, "subtotal": net, "tax": tax_amt, "total": gross,
            "amount_paid": paid, "balance": balance,
        })
        if self.has("invoice_lines"):
            ln = 0
            for (lid, pid, qty, unit_price, line_total) in lines_idx:
                ln += 1
                self.add("invoice_lines", {
                    "id": self.nid("invoice_lines"), "invoice_id": iid, "line_no": ln,
                    "product_id": pid, "qty": qty, "unit_price": unit_price, "line_total": line_total,
                })
        if paid > 0 and self.has("payments"):
            pay_date = add_days(due, r.choice([-20, -10, -5, 0, 3, 8, 15]) if status != "overdue" else r.choice([5, 15, 30]))
            if pay_date < idate:
                pay_date = idate
            if pay_date > self._today():
                pay_date = self._today()
            self.add("payments", {
                "id": self.nid("payments"), "payment_no": f"PAY-{self._ids['payments']:07d}",
                "invoice_id": iid, "customer_id": cust, "payment_date": pay_date,
                "method": r.weighted(["ACH", "Wire", "Credit Card", "Check"], [45, 25, 20, 10]),
                "amount": paid,
            })

    def _make_return(self, r, oid, cust, odate, lines_idx, products):
        lid, pid, qty, unit_price, line_total = r.choice(lines_idx)
        rqty = max(1, int(qty * r.choice([0.2, 0.3, 0.5, 1.0])))
        self.add("returns", {
            "id": self.nid("returns"), "return_no": f"RMA-{self._ids['returns']:06d}",
            "order_id": oid, "order_line_id": lid, "product_id": pid, "customer_id": cust,
            "return_date": add_days(odate, r.randint(3, 45)), "qty": rqty,
            "reason": r.choice(["Damaged", "Wrong item", "Defective", "Not as described",
                                "Late delivery", "Customer changed mind"]),
            "refund_amount": money(rqty * unit_price),
        })

    def gen_purchasing(self):
        if not self.has("purchase_orders"):
            return
        r = self.rng.stream("purch")
        vendors = [v["id"] for v in self.rows("vendors")]
        warehouses = [w["id"] for w in self.rows("warehouses")] or [None]
        buy_raw = self.has("raw_materials") and self.rows("raw_materials")
        if buy_raw:
            items = [(m["id"], m["unit_cost"], "raw_material") for m in self.rows("raw_materials")]
        else:
            items = [(p["id"], p["unit_cost"], "product") for p in self.rows("products")]
        # target spend ~ total COGS * 1.05 spread across POs
        total_cogs = sum(o["cogs"] for o in self.rows("sales_orders"))
        target_spend = total_cogs * 1.05
        avg_po = max(2000.0, self.p.avg_order_value * 1.5)
        n_pos = max(self.p.years * 12, int(target_spend / avg_po))
        for _ in range(n_pos):
            yi = r.randint(0, self.p.years - 1)
            year = self.p.start_year + yi
            month = r.randint(1, 12)
            self._one_po(r, year, month, vendors, warehouses, items, avg_po)

    def _one_po(self, r, year, month, vendors, warehouses, items, avg_po):
        if not vendors or not items:
            return
        poid = self.nid("purchase_orders")
        odate = random_date_in_month(r, year, month)
        n_lines = max(1, r.poisson(2.5))
        line_targets = self._split(r, r.lognormal_mean(avg_po, 0.5), n_lines)
        subtotal = 0.0
        ln = 0
        for lt in line_targets:
            iid_, cost, itype = r.choice(items)
            unit_cost = round(cost * r.jitter(1.0, 0.05), 4)
            qty = max(1, int(round(lt / max(unit_cost, 0.01))))
            line_total = money(qty * unit_cost)
            received = qty if r.chance(0.9) else int(qty * r.rand())
            ln += 1
            self.add("purchase_order_lines", {
                "id": self.nid("purchase_order_lines"), "po_id": poid, "line_no": ln,
                "item_type": itype, "item_id": iid_, "qty": qty, "unit_cost": unit_cost,
                "line_total": line_total, "received_qty": received,
            })
            subtotal += line_total
        tax = money(subtotal * self.tax_rate)
        self.add("purchase_orders", {
            "id": poid, "po_no": f"PO-{year}-{poid:06d}", "vendor_id": r.choice(vendors),
            "warehouse_id": r.choice(warehouses), "order_date": odate,
            "status": r.weighted(["received", "open", "cancelled"], [88, 9, 3]),
            "currency": self.p.currency, "subtotal": money(subtotal), "tax": tax,
            "total": money(subtotal + tax),
        })

    def gen_production(self):
        if not self.has("production_orders"):
            return
        r = self.rng.stream("prod_ord")
        wcs = [w["id"] for w in self.rows("work_centers")] or [None]
        bom_by_product = getattr(self, "_bom_by_product", {})
        bom_lines_by_bom = {}
        for bl in self.rows("bom_lines"):
            bom_lines_by_bom.setdefault(bl["bom_id"], []).append(bl)
        raw_cost = {m["id"]: m["unit_cost"] for m in self.rows("raw_materials")}
        # total finished units sold drives how much we produce
        sold_qty = {}
        for l in self.rows("sales_order_lines"):
            sold_qty[l["product_id"]] = sold_qty.get(l["product_id"], 0) + l["qty"]
        for p in self.rows("products"):
            need = sold_qty.get(p["id"], 0) * 1.05
            if need <= 0:
                continue
            bid = bom_by_product.get(p["id"])
            # batch into MOs
            batch = max(10, int(need / max(self.p.years * 4, 1)))
            made = 0
            while made < need:
                qty = min(batch, need - made)
                made += qty
                moid = self.nid("production_orders")
                yi = r.randint(0, self.p.years - 1)
                start = random_date_in_month(r, self.p.start_year + yi, r.randint(1, 12))
                scrap = round(qty * r.choice([0, 0, 0.01, 0.02, 0.03]), 2)
                produced = round(qty - scrap, 2)
                self.add("production_orders", {
                    "id": moid, "mo_no": f"MO-{start.year}-{moid:06d}", "product_id": p["id"],
                    "bom_id": bid, "work_center_id": r.choice(wcs),
                    "planned_qty": round(qty, 2), "produced_qty": produced, "scrap_qty": scrap,
                    "start_date": start, "end_date": add_days(start, r.randint(1, 7)),
                    "status": r.weighted(["done", "in_progress"], [95, 5]),
                    "unit_cost": p["unit_cost"],
                })
                for bl in bom_lines_by_bom.get(bid, []):
                    planned = round(qty * bl["qty_per"], 4)
                    consumed = round(planned * (1 + bl["scrap_pct"] / 100.0), 4)
                    self.add("production_consumption", {
                        "id": self.nid("production_consumption"), "production_order_id": moid,
                        "raw_material_id": bl["raw_material_id"], "planned_qty": planned,
                        "consumed_qty": consumed, "unit_cost": raw_cost.get(bl["raw_material_id"], 0),
                    })
                if self.has("lots"):
                    shelf = int(self.t.get("shelf_life_days", 365))
                    self.add("lots", {
                        "id": self.nid("lots"), "lot_no": f"LOT-{moid:06d}", "product_id": p["id"],
                        "production_order_id": moid, "production_date": start,
                        "expiry_date": add_days(start, shelf), "qty": produced,
                    })

    def gen_stock_moves(self):
        if not self.has("stock_moves"):
            return
        whs = [w["id"] for w in self.rows("warehouses")] or [None]
        wh0 = whs[0]
        # outbound from sales
        for l in self.rows("sales_order_lines"):
            self.add("stock_moves", {
                "id": self.nid("stock_moves"), "move_date": self._order_date(l["order_id"]),
                "item_type": "product", "item_id": l["product_id"], "warehouse_id": wh0,
                "move_type": "out", "qty": l["qty"], "unit_cost": l["unit_cost"],
                "reference_type": "sales_order", "reference_id": l["order_id"],
            })
        # inbound from purchases
        for l in self.rows("purchase_order_lines"):
            self.add("stock_moves", {
                "id": self.nid("stock_moves"), "move_date": self._po_date(l["po_id"]),
                "item_type": l["item_type"], "item_id": l["item_id"], "warehouse_id": wh0,
                "move_type": "in", "qty": l["received_qty"], "unit_cost": l["unit_cost"],
                "reference_type": "purchase_order", "reference_id": l["po_id"],
            })
        # inbound from production
        for mo in self.rows("production_orders"):
            self.add("stock_moves", {
                "id": self.nid("stock_moves"), "move_date": mo["start_date"],
                "item_type": "product", "item_id": mo["product_id"], "warehouse_id": wh0,
                "move_type": "production", "qty": mo["produced_qty"], "unit_cost": mo["unit_cost"],
                "reference_type": "production_order", "reference_id": mo["id"],
            })

    def gen_bank(self):
        if not self.has("bank_transactions"):
            return
        r = self.rng.stream("bank")
        events = []
        for pay in self.rows("payments"):
            events.append((pay["payment_date"], "in", pay["amount"], "Customer Receipt",
                           "payment", pay["id"], self._cust_name(pay["customer_id"])))
        for po in self.rows("purchase_orders"):
            if po["status"] != "cancelled":
                events.append((add_days(po["order_date"], r.randint(15, 45)), "out", po["total"],
                               "Vendor Payment", "purchase_order", po["id"], self._vend_name(po["vendor_id"])))
        # monthly payroll
        monthly_payroll = sum(e["salary"] for e in self.rows("employees") if e["is_active"]) / 12.0
        for yi in range(self.p.years):
            for m in range(1, 13):
                d = date(self.p.start_year + yi, m, min(28, days_in_month(self.p.start_year + yi, m)))
                events.append((d, "out", money(r.jitter(monthly_payroll, 0.05)), "Payroll",
                               "payroll", 0, "Payroll Run"))
        events.sort(key=lambda e: e[0])
        balance = float(self.t.get("opening_cash", 250000))
        for (d, direction, amount, account, rtype, rid, cp) in events:
            balance += amount if direction == "in" else -amount
            self.add("bank_transactions", {
                "id": self.nid("bank_transactions"), "txn_date": d, "account": account,
                "direction": direction, "counterparty": cp, "reference_type": rtype,
                "reference_id": rid, "amount": money(amount), "balance_after": money(balance),
            })

    def gen_gl(self):
        if not self.has("gl_entries"):
            return
        for inv in self.rows("invoices"):
            self.add("gl_entries", {
                "id": self.nid("gl_entries"), "entry_date": inv["invoice_date"],
                "account_code": "1200", "account_name": "Accounts Receivable",
                "debit": inv["total"], "credit": 0, "reference_type": "invoice",
                "reference_id": inv["id"],
            })
            self.add("gl_entries", {
                "id": self.nid("gl_entries"), "entry_date": inv["invoice_date"],
                "account_code": "4000", "account_name": "Sales Revenue",
                "debit": 0, "credit": inv["subtotal"], "reference_type": "invoice",
                "reference_id": inv["id"],
            })
            if inv["tax"]:
                self.add("gl_entries", {
                    "id": self.nid("gl_entries"), "entry_date": inv["invoice_date"],
                    "account_code": "2200", "account_name": "Sales Tax Payable",
                    "debit": 0, "credit": inv["tax"], "reference_type": "invoice",
                    "reference_id": inv["id"],
                })
        for pay in self.rows("payments"):
            self.add("gl_entries", {
                "id": self.nid("gl_entries"), "entry_date": pay["payment_date"],
                "account_code": "1000", "account_name": "Cash", "debit": pay["amount"],
                "credit": 0, "reference_type": "payment", "reference_id": pay["id"],
            })
            self.add("gl_entries", {
                "id": self.nid("gl_entries"), "entry_date": pay["payment_date"],
                "account_code": "1200", "account_name": "Accounts Receivable", "debit": 0,
                "credit": pay["amount"], "reference_type": "payment", "reference_id": pay["id"],
            })

    def gen_iot(self):
        if not self.has("iot_readings"):
            return
        r = self.rng.stream("iot")
        days = int(self.t.get("iot_days", 180))
        end = self._today()
        sources = self.rows("work_centers") or self.rows("warehouses")
        stype = "work_center" if self.rows("work_centers") else "warehouse"
        metrics = self.t.get("iot_metrics", [
            {"metric": "uptime_pct", "unit": "%", "base": 92, "sigma": 0.04},
            {"metric": "units_produced", "unit": "ea", "base": 850, "sigma": 0.25},
            {"metric": "temperature", "unit": "C", "base": 4, "sigma": 0.3},
        ])
        for day in range(days):
            d = add_days(end, -day)
            for src in sources:
                for mt in metrics:
                    val = r.jitter(mt["base"], mt["sigma"])
                    if mt["metric"] == "uptime_pct":
                        val = min(100.0, val)
                    self.add("iot_readings", {
                        "id": self.nid("iot_readings"), "source_type": stype, "source_id": src["id"],
                        "reading_ts": f"{d.isoformat()} {r.randint(0,23):02d}:00:00",
                        "metric": mt["metric"], "value": round(val, 4), "unit": mt["unit"],
                    })

    # ================= helpers =================
    def _split(self, r, total, n):
        if n <= 1:
            return [total]
        cuts = sorted(r.rand() for _ in range(n - 1))
        parts = []
        prev = 0.0
        for c in cuts + [1.0]:
            parts.append(total * (c - prev))
            prev = c
        return parts

    def _discount(self, r):
        return r.weighted([0.0, 0.05, 0.10, 0.15, 0.20], [55, 20, 13, 8, 4])

    def _phone(self, r):
        return f"({r.randint(200,989)}) {r.randint(200,999)}-{r.randint(1000,9999)}"

    def _spread_date(self, r, before_start_ok=False):
        lo = self.p.start_year - (3 if before_start_ok else 0)
        y = r.randint(lo, self.p.end_year())
        m = r.randint(1, 12)
        return random_date_in_month(r, y, m)

    def _today(self):
        # deterministic "now" = end of the last simulated year
        return date(self.p.end_year(), 12, 31)

    # order/po/customer/vendor lookups (built lazily)
    def _order_date(self, oid):
        return self._order_date_map[oid]

    def _po_date(self, poid):
        return self._po_date_map[poid]

    def _cust_name(self, cid):
        return self._cust_name_map.get(cid, "Customer")

    def _vend_name(self, vid):
        return self._vend_name_map.get(vid, "Vendor")

    def build_lookups(self):
        self._order_date_map = {o["id"]: o["order_date"] for o in self.rows("sales_orders")}
        self._po_date_map = {o["id"]: o["order_date"] for o in self.rows("purchase_orders")}
        self._cust_name_map = {c["id"]: c["name"] for c in self.rows("customers")}
        self._vend_name_map = {v["id"]: v["name"] for v in self.rows("vendors")}
