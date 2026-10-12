"""Back-office ERP modules for the machinery dealer.

CRM, export logistics + customs, field service and warranty, HR payroll,
fixed assets and depreciation, operating expenses and budgets, plus the cash
and double-entry ledger that ties all of it together.

The point of these modules is that a complete P&L can be built from the data:
revenue and COGS come from sales, everything between gross profit and net
profit comes from here.
"""
from __future__ import annotations

from datetime import date

from . import locales
from .util import money, add_days, add_months, random_date_in_month, days_in_month

WIN_REASONS = ["Best price", "Machine availability / short lead time", "Existing relationship",
               "Condition and inspection report", "Financing terms offered",
               "Included tooling package", "Local service coverage"]
LOSS_REASONS = ["Lost on price", "Competitor had better machine", "Customer postponed capex",
                "Customer bought new instead of used", "Lead time too long",
                "Financing not approved", "No response / went quiet",
                "Machine sold to another buyer first"]
COMPETITORS = ["Surplex", "Maschinensucher Trader", "RDMO", "Machines4u EU", "Kitmondo Partner",
               "Werktuigen Dealer", "Prestige Equipment EU", "Local dealer", "OEM direct",
               "TIAB Makina", "Anadolu Tezgah"]
LEAD_SOURCES = ["Machineseeker listing", "Exapro enquiry", "Mascus listing", "Website form",
                "EMO Hannover trade fair", "AMB Stuttgart trade fair",
                "TIMTOS / Turkish trade delegation", "Referral", "Cold call campaign",
                "LinkedIn outreach", "Email campaign", "Existing customer repeat",
                "Auction watch-list", "Trade press advert"]
ACTIVITY_TYPES = ["Call", "Email", "On-site visit", "Machine inspection", "Video walkaround",
                  "Quotation sent", "Follow-up", "Negotiation meeting", "Trade fair meeting",
                  "Technical clarification"]


class BackOfficeMixin:
    # ------------------------------------------------------------------- CRM
    def gen_crm(self):
        r = self.rng.stream("crm")
        owners = self.salespeople
        self._leads_by_customer = {}
        self._gen_leads(r, owners)

        machine_orders = [o for o in self.rows("sales_orders")
                          if o["order_type"] == "Machine Deal" and o["status"] != "cancelled"]
        lines_by_order = {}
        for l in self.rows("sales_order_lines"):
            lines_by_order.setdefault(l["order_id"], []).append(l)

        for o in machine_orders:
            self._won_opportunity(r, o, lines_by_order.get(o["id"], []))

        # deals that never closed — without them win-rate analysis is meaningless
        n_lost = int(len(machine_orders) * float(self.t.get("lost_opportunity_ratio", 1.15)))
        for _ in range(n_lost):
            self._lost_opportunity(r, owners)

    def _gen_leads(self, r, owners):
        n = int(self.t.get("leads_count", 3200))
        cust_ids = [c["id"] for c in self.rows("customers")]
        pool = locales.EU_LOCATIONS + locales.TR_LOCATIONS
        cats = self.t.get("machine_categories", ["CNC Lathe"])
        for i in range(n):
            lid = self.nid("leads")
            city, region, country, iso2, phone_cc, cur, in_eu = locales.location(r, pool)
            created = self._spread_date(r, before_start_ok=False)
            if created > self._today():
                created = self._today()
            status = r.weighted(["Converted", "Qualified", "Nurturing", "Disqualified", "New"],
                                [26, 18, 22, 26, 8])
            conv_cid = conv_date = None
            lost = None
            if status == "Converted":
                conv_cid = r.choice(cust_ids)
                conv_date = add_days(created, r.randint(5, 240))
                if conv_date > self._today():
                    conv_date = self._today()
                self._leads_by_customer.setdefault(conv_cid, []).append(lid)
            elif status == "Disqualified":
                lost = r.choice(["No budget", "Not a fit", "Wrong region", "Duplicate",
                                 "Bought elsewhere", "No decision authority"])
            fn, ln = locales.person(r, "tr" if iso2 == "TR" else "de")
            self.add("leads", {
                "id": lid, "lead_no": f"LD-{created.year}-{lid:06d}",
                "company_name": self._lead_company(r, iso2), "contact_name": f"{fn} {ln}",
                "email": f"{self._ascii(fn)}.{self._ascii(ln)}@example.com".lower(),
                "phone": locales.phone_for(r, phone_cc), "country": country, "city": city,
                "source": r.choice(LEAD_SOURCES), "interest_category": r.choice(cats),
                "created_date": created, "status": status, "score": r.randint(10, 99),
                "owner_id": r.choice(owners), "converted_customer_id": conv_cid,
                "converted_date": conv_date, "lost_reason": lost,
            })

    @staticmethod
    def _lead_company(r, iso2):
        heads = ["Precision", "Nord", "Anadolu", "Metall", "Steel", "Tek", "Mikro", "Öz",
                 "Alpha", "Meta", "Ferro", "Titan", "Kappa", "Delta", "Mekanik", "Vulkan"]
        tails = ["Zerspanung", "Makina", "Metallbau", "Engineering", "Machining", "Werke",
                 "Endüstri", "Fabrikasyon", "Toolworks", "Mechanics", "Metaal", "Meccanica"]
        sufs = {"DE": "GmbH", "TR": "A.Ş.", "PL": "Sp. z o.o.", "IT": "S.r.l.", "ES": "S.L.",
                "NL": "B.V.", "FR": "SAS", "CZ": "s.r.o.", "AT": "GmbH", "GB": "Ltd"}
        return f"{r.choice(heads)} {r.choice(tails)} {sufs.get(iso2, 'Ltd')}"

    def _won_opportunity(self, r, order, lines):
        cust = self._cust[order["customer_id"]]
        oid = self.nid("opportunities")
        created = add_days(order["order_date"], -r.randint(14, 210))
        if created < self.start_date:
            created = self.start_date
        mach = [l for l in lines if l["line_type"] == "machine"]
        cat = (self._product_by_id[mach[0]["product_id"]]["category"] if mach else "Tooling")
        leads = self._leads_by_customer.get(cust["id"])
        self.add("opportunities", {
            "id": oid, "opp_no": f"OPP-{created.year}-{oid:06d}", "customer_id": cust["id"],
            "lead_id": (r.choice(leads) if leads and r.chance(0.35) else None),
            "owner_id": order["salesperson_id"],
            "title": f"{cat} for {cust['name']}", "product_category": "Machine",
            "machine_category": cat, "created_date": created,
            "expected_close_date": add_days(created, r.randint(30, 180)),
            "close_date": order["order_date"], "stage": "Closed Won", "probability_pct": 100,
            "currency": order["currency"], "amount": order["total"],
            "fx_rate": order["fx_rate"], "amount_base": order["total_base"], "status": "won",
            "win_loss_reason": r.choice(WIN_REASONS),
            "competitor": r.choice(COMPETITORS) if r.chance(0.55) else None,
            "source": r.choice(LEAD_SOURCES),
        })
        q = self._quotation(r, oid, cust, order, lines, created, "accepted")
        order["opportunity_id"] = oid
        order["quote_id"] = q
        self._crm_activities(r, oid, None, cust["id"], order["salesperson_id"],
                             created, order["order_date"], won=True)

    def _lost_opportunity(self, r, owners):
        cust = self._cust[self._customer_picker.pick()]
        oid = self.nid("opportunities")
        created = self._spread_date(r, before_start_ok=False)
        if created > self._today():
            created = self._today()
        p = self._product_by_id[self._machine_picker.pick()]
        ccy = cust["currency"]
        rate = self.fx(ccy, created)
        amount_base = money(p["list_price"] * r.jitter(1.0, 0.35))
        stage = r.weighted(["Closed Lost", "Qualification", "Proposal", "Negotiation"],
                           [68, 9, 13, 10])
        is_open = stage != "Closed Lost"
        close = None if is_open else add_days(created, r.randint(20, 260))
        if close and close > self._today():
            close = self._today()
        owner = r.choice(owners)
        self.add("opportunities", {
            "id": oid, "opp_no": f"OPP-{created.year}-{oid:06d}", "customer_id": cust["id"],
            "lead_id": None, "owner_id": owner,
            "title": f"{p['category']} for {cust['name']}", "product_category": "Machine",
            "machine_category": p["category"], "created_date": created,
            "expected_close_date": add_days(created, r.randint(30, 210)),
            "close_date": close, "stage": stage,
            "probability_pct": {"Qualification": 20, "Proposal": 45, "Negotiation": 70,
                                "Closed Lost": 0}[stage],
            "currency": ccy, "amount": money(amount_base * rate), "fx_rate": rate,
            "amount_base": amount_base, "status": "open" if is_open else "lost",
            "win_loss_reason": None if is_open else r.choice(LOSS_REASONS),
            "competitor": r.choice(COMPETITORS) if r.chance(0.6) else None,
            "source": r.choice(LEAD_SOURCES),
        })
        if r.chance(0.75):
            self._quotation(r, oid, cust, None, None, created,
                            "expired" if is_open else "lost", p, amount_base, ccy, rate, owner)
        self._crm_activities(r, oid, None, cust["id"], owner, created,
                             close or self._today(), won=False)

    def _quotation(self, r, opp_id, cust, order, lines, created, status,
                   fallback_product=None, amount_base=None, ccy=None, rate=None, owner=None):
        qid = self.nid("quotations")
        qdate = add_days(created, r.randint(1, 25))
        if qdate > self._today():
            qdate = self._today()
        if order is not None:
            ccy, rate = order["currency"], order["fx_rate"]
            sub, disc, tax, tot = (order["subtotal"], order["discount"], order["tax"],
                                   order["total"])
            tot_b = order["total_base"]
            sp = order["salesperson_id"]
            incoterm = order["incoterm"]
            src_lines = [(l["product_id"], l["machine_unit_id"], l["description"], l["qty"],
                          l["unit_price"], l["discount_pct"], l["line_total"]) for l in lines]
            conv = order["id"]
        else:
            sub = money(amount_base * rate)
            disc = money(sub * r.choice([0.0, 0.03, 0.05, 0.08]))
            tax = money((sub - disc) * (0.19 if cust["country_code"] == "DE" else 0.0))
            tot = money(sub - disc + tax)
            tot_b = money(tot / rate)
            sp = owner
            incoterm = cust["incoterm"]
            src_lines = [(fallback_product["id"], None, fallback_product["name"], 1,
                          money(amount_base * rate), round(disc / sub * 100, 2) if sub else 0,
                          tot)]
            conv = None
        self.add("quotations", {
            "id": qid, "quote_no": f"QT-{qdate.year}-{qid:06d}", "opportunity_id": opp_id,
            "customer_id": cust["id"], "salesperson_id": sp, "quote_date": qdate,
            "valid_until": add_days(qdate, r.choice([14, 21, 30, 45, 60])),
            "currency": ccy, "fx_rate": rate, "subtotal": sub, "discount": disc, "tax": tax,
            "total": tot, "total_base": tot_b, "status": status, "converted_order_id": conv,
            "incoterm": incoterm, "lead_time_days": r.choice([7, 14, 21, 30, 45, 60, 90]),
        })
        ln = 0
        for (pid, muid, desc, qty, up, dpct, lt) in src_lines:
            ln += 1
            self.add("quotation_lines", {
                "id": self.nid("quotation_lines"), "quote_id": qid, "line_no": ln,
                "product_id": pid, "machine_unit_id": muid, "description": desc,
                "qty": qty, "unit_price": up, "discount_pct": dpct, "line_total": lt,
            })
        return qid

    def _crm_activities(self, r, opp_id, lead_id, cust_id, emp_id, start, end, won):
        n = r.randint(3, 11) if won else r.randint(1, 7)
        span = max(1, (end - start).days)
        for _ in range(n):
            d = add_days(start, r.randint(0, span))
            if d > self._today():
                d = self._today()
            self.add("crm_activities", {
                "id": self.nid("crm_activities"), "activity_date": d,
                "activity_type": r.choice(ACTIVITY_TYPES), "opportunity_id": opp_id,
                "lead_id": lead_id, "customer_id": cust_id, "employee_id": emp_id,
                "subject": r.choice([
                    "Discussed machine specification", "Sent condition report and photos",
                    "Arranged inspection visit", "Price negotiation", "Clarified tooling package",
                    "Discussed delivery and rigging", "Reviewed financing options",
                    "Chased decision", "Sent updated quotation", "Handled technical questions"]),
                "outcome": r.weighted(["Positive", "Neutral", "Needs follow-up", "Negative"],
                                      [38, 30, 25, 7]),
                "duration_min": r.choice([10, 15, 20, 30, 45, 60, 90, 120, 240]),
            })

    # ------------------------------------------------------- export logistics
    def gen_logistics(self):
        r = self.rng.stream("logi")
        inv_by_order = {i["order_id"]: i for i in self.rows("invoices")}
        lines_by_order = {}
        for l in self.rows("sales_order_lines"):
            lines_by_order.setdefault(l["order_id"], []).append(l)
        units_by_id = {u["id"]: u for u in self.rows("machine_units")}
        road = self._carriers_by_mode.get("Road", [])
        sea = self._carriers_by_mode.get("Sea", [])
        air = self._carriers_by_mode.get("Air", [])
        parcel = self._carriers_by_mode.get("Parcel", [])

        for o in self.rows("sales_orders"):
            if o["status"] == "cancelled":
                continue
            lines = [l for l in lines_by_order.get(o["id"], [])
                     if l["line_type"] in ("machine", "accessory")]
            if not lines:
                continue
            cust = self._cust[o["customer_id"]]
            heavy = any(l["line_type"] == "machine" for l in lines)
            weight = 0.0
            for l in lines:
                if l["machine_unit_id"]:
                    weight += float(units_by_id[l["machine_unit_id"]]["weight_kg"])
                else:
                    weight += float(self._product_by_id[l["product_id"]]["weight_kg"]) * float(l["qty"])
            weight = round(max(1.0, weight), 2)

            if heavy:
                mode = "Sea" if (cust["country_code"] in ("TR", "GB") and r.chance(0.42)) else "Road"
            elif weight > 120:
                mode = "Road"
            else:
                mode = r.weighted(["Parcel", "Road", "Air"], [66, 24, 10])
            pool = {"Road": road, "Sea": sea, "Air": air, "Parcel": parcel}.get(mode) or road
            carrier = r.choice(pool) if pool else None

            ship = add_days(o["order_date"], r.randint(3, 45) if heavy else r.randint(1, 8))
            if ship > self._today():
                ship = self._today()
            transit = self._transit_days(r, mode, cust["country_code"])
            delivered = add_days(ship, transit)
            is_export = cust["country_code"] != "DE"
            outside_eu = not cust["is_intra_eu"] and is_export

            freight = self._freight_cost(r, mode, weight, cust["country_code"])
            insurance = money(o["total_base"] * r.jitter(0.0022, 0.4))
            packing = money((320 + weight * 0.055) * r.jitter(1.0, 0.3)) if heavy else money(
                r.jitter(28, 0.6))
            handling = money(freight * r.jitter(0.09, 0.4))
            total_cost = money(freight + insurance + packing + handling)
            # EXW/FCA means the buyer pays; otherwise we recharge part of it
            billed = 0.0 if o["incoterm"] in ("EXW", "FCA") else money(
                total_cost * r.jitter(0.82, 0.22))

            sid = self.nid("shipments")
            inv = inv_by_order.get(o["id"])
            self.add("shipments", {
                "id": sid, "shipment_no": f"SHP-{ship.year}-{sid:06d}", "order_id": o["id"],
                "invoice_id": inv["id"] if inv else None, "customer_id": cust["id"],
                "carrier_id": carrier, "warehouse_id": o["warehouse_id"], "ship_date": ship,
                "eta_date": add_days(ship, transit), "delivery_date":
                    delivered if delivered <= self._today() else None,
                "incoterm": o["incoterm"], "mode": mode, "origin_country":
                    "TR" if o["warehouse_id"] in self._wh_tr else "DE",
                "dest_country": cust["country_code"], "dest_city": cust["city"],
                "is_export": is_export, "is_intra_eu": cust["is_intra_eu"],
                "gross_weight_kg": weight,
                "volume_m3": round(weight / r.jitter(320, 0.25), 2),
                "packages": 1 if heavy else max(1, int(len(lines) * r.jitter(1.2, 0.5))),
                "container_type": self._container(r, mode, weight, heavy),
                "freight_cost": freight, "insurance_cost": insurance, "packing_cost": packing,
                "handling_cost": handling, "total_logistics_cost": total_cost,
                "currency": self.base_ccy, "fx_rate": 1.0, "cost_base": total_cost,
                "billed_to_customer": billed,
                "status": ("delivered" if delivered <= self._today()
                           else r.weighted(["in_transit", "booked"], [70, 30])),
                "tracking_no": f"{r.choice(['DHL','KN','DBS','ARK','MSC'])}"
                               f"{r.randint(100000000, 999999999)}",
                "transit_days": transit,
            })
            for l in lines:
                p = self._product_by_id[l["product_id"]]
                u = units_by_id.get(l["machine_unit_id"]) if l["machine_unit_id"] else None
                self.add("shipment_lines", {
                    "id": self.nid("shipment_lines"), "shipment_id": sid,
                    "order_line_id": l["id"], "product_id": l["product_id"],
                    "machine_unit_id": l["machine_unit_id"], "description": l["description"],
                    "qty": l["qty"],
                    "weight_kg": float(u["weight_kg"]) if u else round(
                        float(p["weight_kg"]) * float(l["qty"]), 2),
                    "hs_code": p["hs_code"], "country_of_origin": p["origin_country"],
                })
            if outside_eu:
                self._customs(r, sid, ship, o, cust, lines)

    @staticmethod
    def _transit_days(r, mode, cc):
        base = {"Parcel": 2, "Road": 4, "Air": 3, "Sea": 16}[mode]
        far = {"TR": 6, "GB": 3, "NO": 4, "CH": 2, "GR": 5, "RO": 4, "BG": 4, "PT": 4, "ES": 3}
        return max(1, int(base + far.get(cc, 1) + r.randint(-1, 4)))

    @staticmethod
    def _freight_cost(r, mode, weight, cc):
        far = {"TR": 1.55, "GB": 1.3, "NO": 1.45, "SE": 1.25, "ES": 1.3, "PT": 1.4,
               "RO": 1.35, "BG": 1.4, "GR": 1.45, "IT": 1.15, "PL": 1.1, "CZ": 1.05,
               "FI": 1.5, "DE": 1.0}.get(cc, 1.2)
        if mode == "Parcel":
            return money((9 + weight * 1.35) * far * r.jitter(1.0, 0.25))
        if mode == "Air":
            return money((120 + weight * 4.1) * far * r.jitter(1.0, 0.3))
        if mode == "Sea":
            return money((1750 + weight * 0.061) * far * r.jitter(1.0, 0.28))
        return money((260 + weight * 0.115) * far * r.jitter(1.0, 0.26))

    @staticmethod
    def _container(r, mode, weight, heavy):
        if mode == "Sea":
            return r.weighted(["40ft Flat Rack", "40ft Open Top", "20ft Flat Rack",
                               "Breakbulk / RoRo", "40ft HC"], [30, 22, 16, 20, 12])
        if heavy:
            return r.weighted(["Low-loader trailer", "Mega trailer", "Step-deck trailer",
                               "Heavy haulage (permit)"], [38, 30, 20, 12])
        return r.weighted(["Euro pallet", "Crate", "Parcel", "Half-load trailer"],
                          [42, 28, 22, 8])

    def _customs(self, r, sid, ship, order, cust, lines):
        """Export paperwork. EU-Türkiye trade moves under the customs union, so
        A.TR certificates dominate that lane; other exports use EX-A/EUR.1."""
        cc = cust["country_code"]
        if cc == "TR":
            doc = r.weighted(["A.TR Movement Certificate", "EX-A Export Declaration",
                              "T1 Transit Document"], [66, 26, 8])
            duty_rate = 0.0 if doc == "A.TR Movement Certificate" else r.choice([0.0, 0.0, 1.7, 2.7])
        elif cc == "GB":
            doc = r.weighted(["EUR.1 Certificate", "EX-A Export Declaration"], [58, 42])
            duty_rate = 0.0 if doc == "EUR.1 Certificate" else r.choice([0.0, 2.0, 2.7])
        else:
            doc = r.weighted(["EX-A Export Declaration", "EUR.1 Certificate",
                              "ATA Carnet", "T1 Transit Document"], [56, 28, 6, 10])
            duty_rate = r.choice([0.0, 0.0, 1.7, 2.2, 2.7, 3.7])
        value_base = order["subtotal_base"]
        rate = order["fx_rate"]
        duty = money(value_base * duty_rate / 100.0)
        broker = r.choice(self._brokers) if self._brokers else None
        did = self.nid("customs_declarations")
        self.add("customs_declarations", {
            "id": did, "declaration_no": f"CD-{ship.year}-{did:06d}", "shipment_id": sid,
            "decl_date": add_days(ship, -r.randint(0, 4)), "direction": "export",
            "customs_office": r.choice(["DE004058 Hamburg-Waltershof", "DE003501 Hamburg-Hafen",
                                        "DE002802 Bremen", "DE004060 Hamburg-Freihafen"]),
            "document_type": doc,
            "hs_code": self._product_by_id[lines[0]["product_id"]]["hs_code"],
            "dest_country": cc, "currency": order["currency"], "fx_rate": rate,
            "customs_value": money(value_base * rate), "customs_value_base": value_base,
            "duty_rate_pct": duty_rate, "duty_amount": duty,
            "vat_amount": 0.0,  # exports are VAT-exempt at the German border
            "broker_id": broker,
            "broker_fee": money(r.jitter(165, 0.45) + (95 if doc == "T1 Transit Document" else 0)),
            "status": r.weighted(["cleared", "cleared", "pending", "amended"], [78, 14, 5, 3]),
        })

    # ------------------------------------------------- field service & warranty
    def gen_service(self):
        r = self.rng.stream("svc")
        techs = self.technicians
        sold = [u for u in self.rows("machine_units") if u["status"] == "sold" and u["sale_date"]]
        inv_by_order = {i["order_id"]: i["id"] for i in self.rows("invoices")}
        for u in sold:
            cust_id = self._sale_customer(u)
            if cust_id is None:
                continue
            cust = self._cust[cust_id]
            months = r.weighted([0, 3, 6, 12, 24], [30, 22, 24, 20, 4])
            if months:
                cid = self.nid("warranty_contracts")
                price_base = money(u["sale_price_base"] * r.jitter(0.014, 0.5) * (months / 6.0))
                self.add("warranty_contracts", {
                    "id": cid, "contract_no": f"WC-{u['sale_date'].year}-{cid:06d}",
                    "machine_unit_id": u["id"], "customer_id": cust_id,
                    "invoice_id": inv_by_order.get(u["sale_order_id"]),
                    "start_date": u["sale_date"],
                    "end_date": add_months(u["sale_date"], months), "months": months,
                    "coverage_type": r.weighted(
                        ["Parts only", "Parts & Labour", "Full incl. travel", "Spindle only"],
                        [34, 42, 16, 8]),
                    "price": money(price_base * self.fx(cust["currency"], u["sale_date"])),
                    "currency": cust["currency"], "price_base": price_base,
                    "status": "expired" if add_months(u["sale_date"], months) < self._today()
                              else "active",
                    "claims_count": 0, "claims_cost": 0.0,
                })
            # commissioning is almost always part of the deal
            if r.chance(0.86):
                self._service_job(r, u, cust, techs, "Installation & Commissioning",
                                  add_days(u["sale_date"], r.randint(5, 60)), billable=True)
            n_jobs = r.weighted([0, 1, 2, 3, 4], [40, 27, 17, 11, 5])
            for _ in range(n_jobs):
                d = add_days(u["sale_date"], r.randint(20, 1400))
                if d > self._today():
                    continue
                in_warranty = bool(months) and d <= add_months(u["sale_date"], months)
                jt = r.choice(["Breakdown Repair", "Preventive Maintenance", "Spindle Service",
                               "Control Fault Diagnosis", "Geometry Realignment",
                               "Operator Training", "Retrofit Support", "Remote Support"])
                self._service_job(r, u, cust, techs, jt, d, billable=not in_warranty,
                                  warranty=in_warranty)

    def _sale_customer(self, unit):
        o = self._order_by_id.get(unit["sale_order_id"])
        return o["customer_id"] if o else None

    def _service_job(self, r, unit, cust, techs, job_type, req_date, billable, warranty=False):
        if req_date > self._today():
            return
        jid = self.nid("service_jobs")
        sched = add_days(req_date, r.randint(1, 21))
        done = add_days(sched, r.randint(0, 6))
        hours = round(max(1.0, r.lognormal(7.0, 0.7)), 2)
        rate_h = float(self.t.get("service_labor_rate", 78))
        labor = money(hours * rate_h)
        parts = 0.0 if r.chance(0.35) else money(r.lognormal(680, 1.05))
        travel = money((240 if cust["country_code"] != "DE" else 90) * r.jitter(1.0, 0.5)
                       + (620 if cust["country_code"] in ("TR", "ES", "PT", "GR", "RO") else 0))
        total = money(labor + parts + travel)
        billable_amt = 0.0 if not billable else money(total * r.jitter(1.62, 0.18))
        ccy = cust["currency"]
        fxr = self.fx(ccy, done)
        self.add("service_jobs", {
            "id": jid, "job_no": f"SJ-{req_date.year}-{jid:06d}", "machine_unit_id": unit["id"],
            "customer_id": cust["id"], "job_type": job_type, "request_date": req_date,
            "scheduled_date": sched,
            "completion_date": done if done <= self._today() else None,
            "technician_id": r.choice(techs), "country": cust["country_code"],
            "labor_hours": hours, "labor_cost": labor, "parts_cost": parts,
            "travel_cost": travel, "total_cost": total,
            "billable_amount": money(billable_amt * fxr), "currency": ccy, "fx_rate": fxr,
            "billable_base": billable_amt, "is_warranty": warranty,
            "status": ("completed" if done <= self._today() else "scheduled"),
            "sla_days": r.choice([2, 3, 5, 10]), "response_days": (sched - req_date).days,
            "satisfaction_score": round(r.jitter(4.3, 0.14), 2),
        })
        if warranty:
            for wc in self.rows("warranty_contracts"):
                if wc["machine_unit_id"] == unit["id"]:
                    wc["claims_count"] += 1
                    wc["claims_cost"] = money(wc["claims_cost"] + total)
                    break

    # -------------------------------------------------------- HR and payroll
    def gen_payroll(self):
        """Monthly payroll per country. The Hamburg payroll is in EUR; the Tuzla
        payroll is in lira, so its nominal cost climbs steeply with the currency
        while its EUR cost stays roughly flat — which is the whole reason the
        company staffs its workshop there."""
        r = self.rng.stream("payroll")
        emps = self.rows("employees")
        de_wage_drift = float(self.t.get("de_wage_drift", 0.028))
        tr_real_drift = float(self.t.get("tr_wage_real_drift", 0.004))
        today_fx_try = self.fx("TRY", self._today())
        meal_de = float(self.t.get("meal_allowance_de", 108))
        meal_tr_eur = float(self.t.get("meal_allowance_tr_eur", 62))

        for yi, year, m in self.months():
            mstart = date(year, m, 1)
            mend = date(year, m, days_in_month(year, m))
            for cc in ("DE", "TR"):
                active = [e for e in emps
                          if e["country_code"] == cc and e["hire_date"] <= mend
                          and (e["termination_date"] is None or e["termination_date"] >= mstart)]
                if not active:
                    continue
                ccy = self.base_ccy if cc == "DE" else "TRY"
                fxr = self.fx(ccy, mend)
                rid = self.nid("payroll_runs")
                gross_t = ded_t = net_t = cost_t = 0.0
                for e in active:
                    if cc == "DE":
                        factor = (1 + de_wage_drift) ** (year - self.p.end_year())
                    else:
                        factor = (fxr / today_fx_try) * ((1 + tr_real_drift) ** (year - self.p.end_year()))
                    base = money(e["annual_gross"] * factor / 12.0)
                    ot = money(base * r.jitter(0.06, 0.9)) if r.chance(0.34) else 0.0
                    bonus = 0.0
                    if cc == "DE" and m == 12:
                        bonus = money(base * r.jitter(0.85, 0.25))       # 13th salary
                    elif cc == "DE" and m == 6 and r.chance(0.5):
                        bonus = money(base * r.jitter(0.35, 0.4))        # holiday pay
                    elif cc == "TR" and m in (4, 6):
                        bonus = money(base * r.jitter(0.5, 0.3))         # bayram bonus
                    allow = money((meal_de if cc == "DE" else meal_tr_eur * fxr) * r.jitter(1.0, 0.08))
                    gross = money(base + ot + bonus)
                    if cc == "DE":
                        emp_soc = money(gross * 0.2065)
                        tax = money(max(0.0, (gross - emp_soc)) * r.jitter(0.235, 0.16))
                        other_ded = money(gross * 0.0055)                # church/solidarity
                        er_soc = money(gross * 0.2050)
                        er_other = money(allow + gross * 0.012)          # meals + insurance
                    else:
                        emp_soc = money(gross * 0.15)                    # SGK + unemployment
                        tax = money(max(0.0, gross - emp_soc) * r.jitter(0.17, 0.2))
                        other_ded = money(gross * 0.00759)               # stamp duty
                        er_soc = money(gross * 0.2275)
                        er_other = money(allow + gross * 0.02)           # meals + shuttle
                    net = money(gross - emp_soc - tax - other_ded)
                    cost = money(gross + er_soc + er_other)
                    self.add("payroll_items", {
                        "id": self.nid("payroll_items"), "payroll_run_id": rid,
                        "employee_id": e["id"], "period_year": year, "period_month": m,
                        "period_date": mend, "country": cc, "base_salary": base,
                        "overtime_pay": ot, "bonus": bonus, "allowances": allow,
                        "gross_pay": gross, "employee_social": emp_soc, "income_tax": tax,
                        "other_deductions": other_ded, "net_pay": net, "employer_social": er_soc,
                        "employer_other": er_other, "employer_cost": cost, "currency": ccy,
                        "fx_rate": fxr, "employer_cost_base": money(cost / fxr),
                    })
                    gross_t += gross
                    ded_t += emp_soc + tax + other_ded
                    net_t += net
                    cost_t += cost
                self.add("payroll_runs", {
                    "id": rid, "run_no": f"PR-{cc}-{year}{m:02d}", "period_year": year,
                    "period_month": m, "period_date": mend, "country": cc,
                    "pay_date": add_days(mend, -3), "currency": ccy,
                    "employee_count": len(active), "gross_total": money(gross_t),
                    "employee_deductions_total": money(ded_t), "net_total": money(net_t),
                    "employer_cost_total": money(cost_t),
                    "employer_cost_base": money(cost_t / fxr), "status": "posted",
                })

    def gen_leave(self):
        r = self.rng.stream("leave")
        types = ["Annual Leave", "Sick Leave", "Public Holiday Bridge", "Parental Leave",
                 "Unpaid Leave", "Training Leave", "Compensatory Time Off"]
        weights = [56, 22, 8, 3, 3, 6, 2]
        for e in self.rows("employees"):
            start_y = max(self.p.start_year, e["hire_date"].year)
            end_y = e["termination_date"].year if e["termination_date"] else self.p.end_year()
            for y in range(start_y, min(end_y, self.p.end_year()) + 1):
                for _ in range(r.randint(3, 9)):
                    s = random_date_in_month(r, y, r.randint(1, 12))
                    if s > self._today() or s < e["hire_date"]:
                        continue
                    days = r.weighted([1, 2, 3, 5, 10, 14], [30, 18, 14, 20, 12, 6])
                    lt = r.weighted(types, weights)
                    self.add("leave_records", {
                        "id": self.nid("leave_records"), "employee_id": e["id"],
                        "leave_type": lt, "start_date": s, "end_date": add_days(s, days - 1),
                        "days": days, "status": r.weighted(
                            ["Approved", "Approved", "Taken", "Rejected"], [40, 40, 16, 4]),
                        "approved_by": e["manager_id"], "note": "",
                    })

    # --------------------------------------------------- assets & depreciation
    def gen_fixed_assets(self):
        r = self.rng.stream("assets")
        for spec in self.s.get("fixed_assets", []):
            for _ in range(int(spec.get("count", 1))):
                aid = self.nid("fixed_assets")
                cost = money(r.jitter((float(spec["cost_min"]) + float(spec["cost_max"])) / 2,
                                      0.28))
                acq_y = r.randint(max(self.p.start_year - 4, 2013), self.p.end_year())
                acq = random_date_in_month(r, acq_y, r.randint(1, 12))
                if acq > self._today():
                    acq = self._today()
                life = int(spec["useful_life_years"])
                salvage = money(cost * float(spec.get("salvage_pct", 0)) / 100.0)
                dept = self._dept_by_name.get(spec.get("department"))
                self.add("fixed_assets", {
                    "id": aid, "asset_no": f"FA-{aid:05d}", "name": spec["name"],
                    "category": spec["category"], "department_id": dept,
                    "warehouse_id": r.choice(self._wh_de) if self._wh_de else None,
                    "vendor_id": r.choice(list(self._vend)), "acquisition_date": acq,
                    "acquisition_cost": cost, "useful_life_years": life,
                    "salvage_value": salvage, "method": "Straight Line", "status": "in_service",
                    "disposal_date": None, "disposal_proceeds": None,
                    "accumulated_depreciation": 0.0, "net_book_value": cost,
                    "serial_no": f"{spec['category'][:2].upper()}{r.randint(100000, 999999)}",
                })
        self._depreciate()

    def _depreciate(self):
        today = self._today()
        for a in self.rows("fixed_assets"):
            monthly = money((a["acquisition_cost"] - a["salvage_value"]) /
                            (a["useful_life_years"] * 12))
            if monthly <= 0:
                continue
            acc = 0.0
            d = date(a["acquisition_date"].year, a["acquisition_date"].month, 1)
            for i in range(a["useful_life_years"] * 12):
                pd = add_months(d, i)
                pend = date(pd.year, pd.month, days_in_month(pd.year, pd.month))
                if pend > today:
                    break
                if acc + monthly > a["acquisition_cost"] - a["salvage_value"]:
                    monthly = money(a["acquisition_cost"] - a["salvage_value"] - acc)
                if monthly <= 0:
                    break
                acc = money(acc + monthly)
                if pd.year >= self.p.start_year:
                    self.add("depreciation_entries", {
                        "id": self.nid("depreciation_entries"), "asset_id": a["id"],
                        "period_year": pd.year, "period_month": pd.month, "period_date": pend,
                        "depreciation_amount": monthly, "accumulated_after": acc,
                        "book_value_after": money(a["acquisition_cost"] - acc),
                    })
            a["accumulated_depreciation"] = acc
            a["net_book_value"] = money(a["acquisition_cost"] - acc)
            if a["net_book_value"] <= a["salvage_value"] + 0.01:
                a["status"] = "fully_depreciated"

    # -------------------------------------------------------------- expenses
    def gen_expenses(self):
        """One table holding every cost below gross profit: bought-in operating
        costs, payroll, depreciation, logistics, financing and income tax.
        ``source`` distinguishes them so nothing is double counted."""
        r = self.rng.stream("expense")
        rev_final = self.p.revenue_for_year(self.p.years - 1)
        infl = float(self.t.get("inflation", 0.03))
        depts = {d["name"]: d["id"] for d in self.rows("departments")}
        vend_ids = list(self._vend)

        # 1) bought-in operating expenses, category by category
        for cat in self.rows("expense_categories"):
            spec = self._exp_cat[cat["code"]]
            if spec.get("source", "purchased") != "purchased":
                continue
            annual = float(spec["annual_amount"])
            var = float(spec.get("variability_pct", 0)) / 100.0
            freq = spec.get("frequency", "monthly")
            dept_id = depts.get(spec.get("department"), None)
            vtypes = spec.get("vendor_types") or []
            pool = [v for t in vtypes for v in self._vend_by_type.get(t, [])] or vend_ids
            ccy = spec.get("currency", self.base_ccy)
            for yi, year, m in self.months():
                if freq == "quarterly" and m not in (3, 6, 9, 12):
                    continue
                if freq == "annual" and m != int(spec.get("month", 12)):
                    continue
                rev_idx = self.p.revenue_for_year(yi) / rev_final
                infl_f = (1 + infl) ** (year - self.p.end_year())
                periods = {"monthly": 12, "quarterly": 4, "annual": 1}[freq]
                amt_base = (annual / periods) * ((1 - var) + var * rev_idx) * infl_f
                amt_base = money(amt_base * r.jitter(1.0, float(spec.get("noise", 0.14))))
                if amt_base <= 0:
                    continue
                d = random_date_in_month(r, year, m)
                if d > self._today():
                    d = self._today()
                self._add_expense(r, spec, cat, d, amt_base, dept_id,
                                  r.choice(pool) if pool else None, ccy, "purchased")

        # 2) payroll, summarised per department per month
        self._payroll_expenses(r)
        # 3) depreciation
        self._depreciation_expenses()
        # 4) outbound logistics actually incurred (net of what customers paid)
        self._logistics_expenses(r)
        # 5) financing cost on the machine stock, then income tax
        self._finance_expenses(r)
        self._tax_expenses(r)

    def _add_expense(self, r, spec, cat, d, amt_base, dept_id, vendor_id, ccy, source,
                     ref_type=None, ref_id=None, emp_id=None, desc=None, is_cash=True):
        eid = self.nid("expenses")
        fxr = self.fx(ccy, d)
        amount = money(amt_base * fxr)
        vat = money(amt_base * 0.19) if spec.get("vat", True) and is_cash else 0.0
        paid = is_cash and (d < add_days(self._today(), -35) or r.chance(0.72))
        self.add("expenses", {
            "id": eid, "expense_no": f"EXP-{d.year}-{eid:07d}", "expense_date": d,
            "period_year": d.year, "period_month": d.month, "category_id": cat["id"],
            "department_id": dept_id, "vendor_id": vendor_id, "employee_id": emp_id,
            "warehouse_id": None,
            "cost_center": next((x["cost_center"] for x in self.rows("departments")
                                 if x["id"] == dept_id), None),
            "description": desc or cat["name"], "currency": ccy, "amount": amount,
            "fx_rate": fxr, "amount_base": amt_base, "tax_amount": vat,
            "total_base": money(amt_base + vat), "payment_method": (
                "Direct Debit" if source == "purchased" else
                "SEPA Transfer" if source == "payroll" else "Non-cash"),
            "status": "paid" if paid else "open", "source": source,
            "reference_type": ref_type, "reference_id": ref_id,
        })
        return eid

    def _payroll_expenses(self, r):
        wages = self._exp_cat.get("PAY-WAGE")
        social = self._exp_cat.get("PAY-SOC")
        if not wages or not social:
            return
        wcat = next(c for c in self.rows("expense_categories") if c["code"] == "PAY-WAGE")
        scat = next(c for c in self.rows("expense_categories") if c["code"] == "PAY-SOC")
        emp_dept = {e["id"]: e["department_id"] for e in self.rows("employees")}
        buckets = {}
        for it in self.rows("payroll_items"):
            key = (it["period_year"], it["period_month"], emp_dept[it["employee_id"]])
            b = buckets.setdefault(key, [0.0, 0.0, it["period_date"]])
            b[0] += it["gross_pay"] / it["fx_rate"]
            b[1] += (it["employer_social"] + it["employer_other"]) / it["fx_rate"]
        for (y, m, dept), (gross_b, soc_b, pdate) in sorted(buckets.items()):
            self._add_expense(r, wages, wcat, pdate, money(gross_b), dept, None,
                              self.base_ccy, "payroll", "payroll_run", None,
                              desc=f"Gross salaries {y}-{m:02d}")
            self._add_expense(r, social, scat, pdate, money(soc_b), dept, None,
                              self.base_ccy, "payroll", "payroll_run", None,
                              desc=f"Employer contributions & allowances {y}-{m:02d}")

    def _depreciation_expenses(self):
        spec = self._exp_cat.get("DEP-001")
        if not spec:
            return
        cat = next(c for c in self.rows("expense_categories") if c["code"] == "DEP-001")
        by_period = {}
        for de in self.rows("depreciation_entries"):
            key = (de["period_year"], de["period_month"], de["period_date"])
            by_period[key] = by_period.get(key, 0.0) + de["depreciation_amount"]
        r = self.rng.stream("dep_exp")
        for (y, m, pd), amt in sorted(by_period.items()):
            self._add_expense(r, spec, cat, pd, money(amt), None, None, self.base_ccy,
                              "depreciation", "depreciation", None,
                              desc=f"Depreciation {y}-{m:02d}", is_cash=False)

    def _logistics_expenses(self, r):
        spec = self._exp_cat.get("LOG-FRT")
        if not spec:
            return
        cat = next(c for c in self.rows("expense_categories") if c["code"] == "LOG-FRT")
        duty_spec = self._exp_cat.get("LOG-DUT")
        duty_cat = (next(c for c in self.rows("expense_categories") if c["code"] == "LOG-DUT")
                    if duty_spec else None)
        dept = self._dept_by_name.get("Logistics & Shipping")
        by_month = {}
        for s in self.rows("shipments"):
            key = (s["ship_date"].year, s["ship_date"].month)
            by_month[key] = by_month.get(key, 0.0) + max(
                0.0, s["cost_base"] - s["billed_to_customer"])
        for (y, m), amt in sorted(by_month.items()):
            if amt <= 0:
                continue
            d = date(y, m, min(28, days_in_month(y, m)))
            self._add_expense(r, spec, cat, d, money(amt), dept, None, self.base_ccy,
                              "logistics", "shipments", None,
                              desc=f"Outbound freight, packing & rigging {y}-{m:02d}")
        if duty_cat:
            duty_by_month = {}
            for cd in self.rows("customs_declarations"):
                key = (cd["decl_date"].year, cd["decl_date"].month)
                duty_by_month[key] = duty_by_month.get(key, 0.0) + cd["duty_amount"] + cd["broker_fee"]
            for (y, m), amt in sorted(duty_by_month.items()):
                if amt <= 0:
                    continue
                d = date(y, m, min(28, days_in_month(y, m)))
                self._add_expense(r, duty_spec, duty_cat, d, money(amt), dept, None,
                                  self.base_ccy, "logistics", "customs", None,
                                  desc=f"Customs duty & broker fees {y}-{m:02d}")

    def _finance_expenses(self, r):
        spec = self._exp_cat.get("FIN-INT")
        if not spec:
            return
        cat = next(c for c in self.rows("expense_categories") if c["code"] == "FIN-INT")
        dept = self._dept_by_name.get("Finance & Accounting")
        rate = float(self.t.get("floorplan_rate", 0.062))
        # interest accrues on the machine stock actually financed each month
        stock_by_month = {}
        for u in self.rows("machine_units"):
            start = u["acquisition_date"]
            end = u["sale_date"] or self._today()
            d = date(start.year, start.month, 1)
            while d <= end:
                stock_by_month[(d.year, d.month)] = stock_by_month.get((d.year, d.month), 0.0) \
                    + u["landed_cost"]
                d = add_months(d, 1)
        share = float(self.t.get("floorplan_financed_share", 0.55))
        for (y, m), stock in sorted(stock_by_month.items()):
            if y < self.p.start_year:
                continue
            d = date(y, m, min(28, days_in_month(y, m)))
            if d > self._today():
                continue
            amt = money(stock * share * rate / 12.0)
            if amt <= 0:
                continue
            self._add_expense(r, spec, cat, d, amt, dept, None, self.base_ccy, "financing",
                              "floorplan", None,
                              desc=f"Floor-plan interest on machine stock {y}-{m:02d}")

    def _tax_expenses(self, r):
        spec = self._exp_cat.get("TAX-CIT")
        if not spec:
            return
        cat = next(c for c in self.rows("expense_categories") if c["code"] == "TAX-CIT")
        dept = self._dept_by_name.get("Finance & Accounting")
        rate = float(self.t.get("income_tax_rate", 0.30))
        gp = {}
        order_year = {o["id"]: o["order_date"].year for o in self.rows("sales_orders")
                      if o["status"] != "cancelled"}
        for l in self.rows("sales_order_lines"):
            y = order_year.get(l["order_id"])
            if y:
                gp[y] = gp.get(y, 0.0) + l["line_margin_base"]
        opex = {}
        for e in self.rows("expenses"):
            opex[e["period_year"]] = opex.get(e["period_year"], 0.0) + e["amount_base"]
        # realised FX differences are part of the taxable result too — without
        # them a year wrecked by a currency move still pays tax on a loss
        for pay in self.rows("payments"):
            y = pay["payment_date"].year
            opex[y] = opex.get(y, 0.0) - pay["fx_gain_loss"]
        # monthly gross profit, used to spread the annual charge realistically
        gp_month = {}
        order_ym = {o["id"]: (o["order_date"].year, o["order_date"].month)
                    for o in self.rows("sales_orders") if o["status"] != "cancelled"}
        for l in self.rows("sales_order_lines"):
            ym = order_ym.get(l["order_id"])
            if ym:
                gp_month[ym] = gp_month.get(ym, 0.0) + l["line_margin_base"]
        for y in sorted(gp):
            ebt = gp[y] - opex.get(y, 0.0)
            if ebt <= 0:
                continue
            charge = ebt * rate
            months = [(m, v) for (yy, m), v in gp_month.items() if yy == y and v > 0]
            total_gp = sum(v for _, v in months) or 1.0
            for m, v in sorted(months):
                amt = money(charge * v / total_gp)
                if amt <= 0:
                    continue
                d = min(date(y, m, min(28, days_in_month(y, m))), self._today())
                self._add_expense(r, spec, cat, d, amt, dept, None, self.base_ccy,
                                  "tax", "income_tax", None,
                                  desc=f"Corporate income tax accrual {y}-{m:02d}")

    def gen_budgets(self):
        """Budget set before each year, so variance vs actual is realistic."""
        r = self.rng.stream("budget")
        actual = {}
        for e in self.rows("expenses"):
            key = (e["period_year"], e["period_month"], e["department_id"], e["category_id"])
            actual[key] = actual.get(key, 0.0) + e["amount_base"]
        for (y, m, dept, cat), amt in sorted(actual.items(), key=lambda kv: (kv[0][0], kv[0][1])):
            self.add("budgets", {
                "id": self.nid("budgets"), "fiscal_year": y, "period_month": m,
                "department_id": dept, "expense_category_id": cat,
                "budget_amount": money(amt * r.jitter(1.02, 0.16)),
                "budget_type": "Operating", "approved_by": "CFO",
            })

    # ------------------------------------------------------- stock, cash, GL
    def build_lookups(self):
        self._order_date_map = {o["id"]: o["order_date"] for o in self.rows("sales_orders")}
        self._po_date_map = {o["id"]: o["order_date"] for o in self.rows("purchase_orders")}
        self._cust_name_map = {c["id"]: c["name"] for c in self.rows("customers")}
        self._vend_name_map = {v["id"]: v["name"] for v in self.rows("vendors")}
        self._order_by_id = {o["id"]: o for o in self.rows("sales_orders")}
        self._po_by_id = {o["id"]: o for o in self.rows("purchase_orders")}
        self._inv_by_id = {i["id"]: i for i in self.rows("invoices")}

    def gen_stock_moves(self):
        wh0 = self._wh_de[0] if self._wh_de else None
        # opening inventory — the company did not start trading with an empty
        # parts store, and without it on-hand quantities go negative
        n_months = max(1, (self.p.years - 1) * 12 + self.end_month)
        opening_months = float(self.t.get("opening_stock_months", 3.0))
        sold_qty = {}
        for l in self.rows("sales_order_lines"):
            if l["line_type"] == "accessory":
                sold_qty[l["product_id"]] = sold_qty.get(l["product_id"], 0) + float(l["qty"])
        for pid, qty in sold_qty.items():
            open_qty = max(1.0, round(qty * opening_months / n_months, 2))
            cost = self._product_by_id[pid]["unit_cost"]
            self.add("stock_moves", {
                "id": self.nid("stock_moves"), "move_date": self.start_date,
                "item_type": "product", "item_id": pid, "warehouse_id": wh0,
                "move_type": "in", "qty": open_qty, "unit_cost": cost,
                "reference_type": "opening_balance", "reference_id": None,
                "machine_unit_id": None, "value_base": money(open_qty * cost),
                "lot_ref": None,
            })
        # machines: one receipt at acquisition, one issue at sale, at landed cost
        for u in self.rows("machine_units"):
            self.add("stock_moves", {
                "id": self.nid("stock_moves"), "move_date": u["acquisition_date"],
                "item_type": "machine_unit", "item_id": u["product_id"],
                "warehouse_id": u["warehouse_id"], "move_type": "in", "qty": 1,
                "unit_cost": u["landed_cost"], "reference_type": "machine_acquisition",
                "reference_id": u["acquisition_po_id"], "machine_unit_id": u["id"],
                "value_base": u["landed_cost"], "lot_ref": u["serial_no"],
            })
            if u["sale_date"]:
                self.add("stock_moves", {
                    "id": self.nid("stock_moves"), "move_date": u["sale_date"],
                    "item_type": "machine_unit", "item_id": u["product_id"],
                    "warehouse_id": u["warehouse_id"], "move_type": "out", "qty": 1,
                    "unit_cost": u["landed_cost"], "reference_type": "sales_order",
                    "reference_id": u["sale_order_id"], "machine_unit_id": u["id"],
                    "value_base": u["landed_cost"], "lot_ref": u["serial_no"],
                })
        # parts & tooling
        for l in self.rows("sales_order_lines"):
            if l["line_type"] != "accessory":
                continue
            o = self._order_by_id[l["order_id"]]
            if o["status"] == "cancelled":
                continue
            self.add("stock_moves", {
                "id": self.nid("stock_moves"), "move_date": o["order_date"],
                "item_type": "product", "item_id": l["product_id"],
                "warehouse_id": o["warehouse_id"], "move_type": "out", "qty": l["qty"],
                "unit_cost": round(l["line_cogs_base"] / max(float(l["qty"]), 1), 4),
                "reference_type": "sales_order", "reference_id": l["order_id"],
                "machine_unit_id": None, "value_base": l["line_cogs_base"], "lot_ref": None,
            })
        for l in self.rows("purchase_order_lines"):
            if l["item_type"] != "product" or not l["received_qty"]:
                continue
            po = self._po_by_id[l["po_id"]]
            if po["status"] == "cancelled":
                continue
            unit_b = l["line_total_base"] / max(float(l["qty"]), 1)
            self.add("stock_moves", {
                "id": self.nid("stock_moves"), "move_date": po["received_date"] or po["order_date"],
                "item_type": "product", "item_id": l["item_id"],
                "warehouse_id": po["warehouse_id"], "move_type": "in", "qty": l["received_qty"],
                "unit_cost": round(unit_b, 4), "reference_type": "purchase_order",
                "reference_id": l["po_id"], "machine_unit_id": None,
                "value_base": money(unit_b * float(l["received_qty"])), "lot_ref": None,
            })
        # returns come back into stock
        for rt in self.rows("returns"):
            if rt["status"] == "Rejected":
                continue
            self.add("stock_moves", {
                "id": self.nid("stock_moves"), "move_date": rt["return_date"],
                "item_type": "machine_unit" if rt["machine_unit_id"] else "product",
                "item_id": rt["product_id"], "warehouse_id": wh0, "move_type": "in",
                "qty": rt["qty"], "unit_cost": 0, "reference_type": "return",
                "reference_id": rt["id"], "machine_unit_id": rt["machine_unit_id"],
                "value_base": 0, "lot_ref": None,
            })

    def gen_bank(self):
        r = self.rng.stream("bank")
        ev = []
        for p in self.rows("payments"):
            ev.append((p["payment_date"], "in", p["amount_base"], "Operating Account",
                       "Customer Receipt", "payment", p["id"],
                       self._cust_name_map.get(p["customer_id"], "Customer"),
                       f"Invoice settlement {p['currency']} {p['amount']:,.2f}"))
        for vp in self.rows("vendor_payments"):
            ev.append((vp["payment_date"], "out", vp["amount_base"], "Operating Account",
                       "Supplier Payment", "vendor_payment", vp["id"],
                       self._vend_name_map.get(vp["vendor_id"], "Vendor"),
                       f"Bill settlement {vp['currency']} {vp['amount']:,.2f}"))
        cat_by_id = {c["id"]: c for c in self.rows("expense_categories")}
        for e in self.rows("expenses"):
            if e["source"] == "depreciation" or e["status"] != "paid":
                continue
            cat = cat_by_id[e["category_id"]]
            ev.append((e["expense_date"], "out", e["total_base"], "Operating Account",
                       cat["expense_group"], "expense", e["id"],
                       self._vend_name_map.get(e["vendor_id"], cat["name"]), e["description"]))
        # capitalised inbound costs on machines are paid in cash too
        for u in self.rows("machine_units"):
            extra = u["transport_in_cost"] + u["refurb_cost"] + u["other_cost"]
            if extra <= 0:
                continue
            d = add_days(u["acquisition_date"], r.randint(10, 55))
            if d > self._today():
                d = self._today()
            ev.append((d, "out", money(extra), "Operating Account", "Inbound Logistics",
                       "machine_unit", u["id"], "Rigging & refurbishment",
                       f"Inbound transport/refurb {u['unit_no']}"))
        ev.sort(key=lambda x: (x[0], x[6]))
        balance = float(self.t.get("opening_cash", 2500000))
        for (d, direction, amount, account, category, rtype, rid, cp, desc) in ev:
            balance += amount if direction == "in" else -amount
            self.add("bank_transactions", {
                "id": self.nid("bank_transactions"), "txn_date": d, "account": account,
                "direction": direction, "counterparty": cp, "reference_type": rtype,
                "reference_id": rid, "amount": money(amount), "balance_after": money(balance),
                "currency": self.base_ccy, "fx_rate": 1.0, "amount_base": money(amount),
                "category": category, "description": desc,
            })

    # --- double-entry ledger -------------------------------------------------
    def _je(self, d, journal, ref_type, ref_id, lines, memo="", dept=None):
        """Post one balanced journal entry (base currency)."""
        total_d = round(sum(x[1] for x in lines), 2)
        total_c = round(sum(x[2] for x in lines), 2)
        if abs(total_d - total_c) > 0.005:      # force balance onto the last line
            code, dr, cr = lines[-1]
            diff = round(total_d - total_c, 2)
            lines[-1] = (code, dr, round(cr + diff, 2)) if diff > 0 else (code, round(dr - diff, 2), cr)
        self._entry_no += 1
        no = f"JE-{d.year}-{self._entry_no:08d}"
        ln = 0
        for (code, dr, cr) in lines:
            if abs(dr) < 0.005 and abs(cr) < 0.005:
                continue
            ln += 1
            self.add("gl_entries", {
                "id": self.nid("gl_entries"), "entry_date": d, "account_code": code,
                "account_name": self._acct.get(code, code), "debit": money(dr),
                "credit": money(cr), "reference_type": ref_type, "reference_id": ref_id,
                "entry_no": no, "journal": journal, "line_no": ln, "department_id": dept,
                "currency": self.base_ccy, "fx_rate": 1.0, "debit_base": money(dr),
                "credit_base": money(cr), "period_year": d.year, "period_month": d.month,
                "memo": memo,
            })

    def gen_gl(self):
        rev_acct = {"machine": "4000", "accessory": "4100", "service": "4200"}
        cogs_acct = {"machine": "5000", "accessory": "5100", "service": "5200"}
        inv_acct = {"machine": "1300", "accessory": "1310", "service": "1310"}

        lines_by_invoice = {}
        for l in self.rows("invoice_lines"):
            lines_by_invoice.setdefault(l["invoice_id"], []).append(l)
        sol_by_order = {}
        for l in self.rows("sales_order_lines"):
            sol_by_order.setdefault(l["order_id"], []).append(l)

        # --- sales journal
        for inv in self.rows("invoices"):
            rev = {}
            cogs = {}
            for l in sol_by_order.get(inv["order_id"], []):
                rev[l["line_type"]] = rev.get(l["line_type"], 0.0) + l["line_subtotal_base"]
                cogs[l["line_type"]] = cogs.get(l["line_type"], 0.0) + l["line_cogs_base"]
            entry = [("1200", inv["total_base"], 0.0)]
            for k, v in rev.items():
                entry.append((rev_acct[k], 0.0, money(v)))
            if inv["tax_base"]:
                entry.append(("2200", 0.0, inv["tax_base"]))
            self._je(inv["invoice_date"], "Sales", "invoice", inv["id"], entry,
                     memo=f"{inv['invoice_no']} {inv['currency']} {inv['total']:,.2f}")
            centry = []
            for k, v in cogs.items():
                if v:
                    centry.append((cogs_acct[k], money(v), 0.0))
                    centry.append((inv_acct[k], 0.0, money(v)))
            if centry:
                self._je(inv["invoice_date"], "COGS", "invoice", inv["id"], centry,
                         memo=f"Cost of sales for {inv['invoice_no']}")

        # --- cash receipts, with realised FX difference
        for p in self.rows("payments"):
            inv = self._inv_by_id[p["invoice_id"]]
            at_invoice_rate = money(p["amount"] / inv["fx_rate"])
            entry = [("1000", p["amount_base"], 0.0), ("1200", 0.0, at_invoice_rate)]
            diff = money(p["amount_base"] - at_invoice_rate)
            if abs(diff) >= 0.01:
                entry.append(("7100", 0.0, diff) if diff > 0 else ("7100", -diff, 0.0))
            self._je(p["payment_date"], "Cash Receipts", "payment", p["id"], entry,
                     memo=f"{p['payment_no']} {p['currency']} {p['amount']:,.2f}")

        # --- purchasing / AP
        for vb in self.rows("vendor_invoices"):
            acct = "1300" if vb["spend_category"] == "Machine Acquisition" else "1310"
            sub_b = money(vb["total_base"] - (vb["tax"] / vb["fx_rate"] if vb["fx_rate"] else 0))
            entry = [(acct, sub_b, 0.0)]
            vat_b = money(vb["total_base"] - sub_b)
            if vat_b:
                entry.append(("1600", vat_b, 0.0))
            entry.append(("2000", 0.0, vb["total_base"]))
            self._je(vb["bill_date"], "Purchases", "vendor_invoice", vb["id"], entry,
                     memo=f"{vb['bill_no']} {vb['currency']} {vb['total']:,.2f}")
        for vp in self.rows("vendor_payments"):
            self._je(vp["payment_date"], "Cash Payments", "vendor_payment", vp["id"],
                     [("2000", vp["amount_base"], 0.0), ("1000", 0.0, vp["amount_base"])],
                     memo=f"{vp['payment_no']} {vp['currency']} {vp['amount']:,.2f}")

        # --- capitalised inbound cost on machines
        for u in self.rows("machine_units"):
            extra = money(u["transport_in_cost"] + u["refurb_cost"] + u["other_cost"])
            if extra <= 0:
                continue
            self._je(u["acquisition_date"], "Inventory", "machine_unit", u["id"],
                     [("1300", extra, 0.0), ("1000", 0.0, extra)],
                     memo=f"Inbound freight/refurb capitalised to {u['unit_no']}")

        # --- operating expenses (incl. payroll, depreciation, interest, tax)
        cat_by_id = {c["id"]: c for c in self.rows("expense_categories")}
        for e in self.rows("expenses"):
            cat = cat_by_id[e["category_id"]]
            if e["source"] == "depreciation":
                credit = ("1590", 0.0, e["amount_base"])
            elif e["source"] == "tax":
                credit = ("2400", 0.0, e["amount_base"])
            elif e["status"] == "paid":
                credit = ("1000", 0.0, e["total_base"])
            else:
                credit = ("2000", 0.0, e["total_base"])
            entry = [(cat["account_code"], e["amount_base"], 0.0)]
            if e["tax_amount"] and e["status"] == "paid" and e["source"] == "purchased":
                entry.append(("1600", e["tax_amount"], 0.0))
            entry.append(credit)
            self._je(e["expense_date"], cat["expense_group"], "expense", e["id"], entry,
                     memo=e["description"], dept=e["department_id"])

        # --- credit notes for returns
        for rt in self.rows("returns"):
            if rt["status"] == "Rejected":
                continue
            amt = rt["refund_amount_base"]
            self._je(rt["return_date"], "Sales Returns", "return", rt["id"],
                     [("4900", amt, 0.0), ("1200", 0.0, amt)],
                     memo=f"{rt['return_no']} {rt['reason']}")

    def gen_iot(self):
        return  # a dealer has no production line to instrument
