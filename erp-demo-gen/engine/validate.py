"""Post-load integrity + realism checks, run against the live database via psql.

Returns a list of (name, ok, detail) and a metrics dict. Catches the failure
modes that make demo data look fake: dangling FKs, totals that don't reconcile,
payments exceeding invoices, and revenue far off the requested target.
"""
from __future__ import annotations

from . import load


def _int(db, sql):
    v = load.query_value(db, sql)
    try:
        return int(v)
    except (ValueError, TypeError):
        return None


def _float(db, sql):
    v = load.query_value(db, sql)
    try:
        return float(v)
    except (ValueError, TypeError):
        return 0.0


def table_exists(db, t):
    return _int(db, f"SELECT count(*) FROM information_schema.tables "
                    f"WHERE table_schema='public' AND table_name='{t}'") == 1


def run_checks(db, profile, selected):
    checks = []

    def fk(child, col, parent, pcol="id"):
        if child in selected and parent in selected:
            n = _int(db, f"SELECT count(*) FROM {child} c "
                         f"LEFT JOIN {parent} p ON c.{col}=p.{pcol} "
                         f"WHERE c.{col} IS NOT NULL AND p.{pcol} IS NULL")
            checks.append((f"FK {child}.{col} -> {parent}", n == 0, f"{n} orphan(s)"))

    fk("sales_order_lines", "order_id", "sales_orders")
    fk("sales_order_lines", "product_id", "products")
    fk("sales_orders", "customer_id", "customers")
    fk("invoices", "order_id", "sales_orders")
    fk("invoice_lines", "invoice_id", "invoices")
    fk("payments", "invoice_id", "invoices")
    fk("returns", "order_id", "sales_orders")
    fk("purchase_order_lines", "po_id", "purchase_orders")
    fk("purchase_orders", "vendor_id", "vendors")
    fk("production_consumption", "production_order_id", "production_orders")
    fk("bom_lines", "bom_id", "bom")

    # order totals reconcile to their line totals
    if "sales_order_lines" in selected:
        bad = _int(db, """
            SELECT count(*) FROM (
              SELECT o.id, o.total, coalesce(sum(l.line_total),0) AS lt
              FROM sales_orders o JOIN sales_order_lines l ON l.order_id=o.id
              GROUP BY o.id, o.total
              HAVING abs(o.total - coalesce(sum(l.line_total),0)) > 0.05
            ) x""")
        checks.append(("Order totals reconcile to lines", bad == 0, f"{bad} mismatched order(s)"))

    # payments never exceed invoice total
    if "payments" in selected:
        bad = _int(db, "SELECT count(*) FROM invoices WHERE amount_paid > total + 0.05")
        checks.append(("Payments <= invoice total", bad == 0, f"{bad} over-paid invoice(s)"))
        bad2 = _int(db, "SELECT count(*) FROM invoices WHERE round(amount_paid+balance,2) <> round(total,2)")
        checks.append(("Invoice paid+balance = total", bad2 == 0, f"{bad2} inconsistent invoice(s)"))

    if "machine_units" in selected:
        _machinery_checks(db, profile, selected, checks)
        return checks

    if "production_operations" in selected:
        _contract_checks(db, profile, selected, checks)
        return checks

    # net revenue (subtotal - discount, excl. tax) close to target in final year
    final_year = profile.end_year()
    if "sales_orders" in selected:
        rev = _float(db, f"SELECT coalesce(sum(subtotal - discount),0) FROM sales_orders "
                         f"WHERE status<>'cancelled' AND extract(year from order_date)={final_year}")
        target = profile.annual_revenue
        ratio = rev / target if target else 0
        ok = 0.85 <= ratio <= 1.15
        checks.append((f"Final-year net revenue near target ({ratio:.0%})", ok,
                       f"actual ${rev:,.0f} vs target ${target:,.0f}"))

    return checks


def _machinery_checks(db, profile, selected, checks):
    """Extra integrity + realism checks for the serialized multi-currency model."""

    def fk(child, col, parent, pcol="id"):
        if child in selected and parent in selected:
            n = _int(db, f"SELECT count(*) FROM {child} c "
                         f"LEFT JOIN {parent} p ON c.{col}=p.{pcol} "
                         f"WHERE c.{col} IS NOT NULL AND p.{pcol} IS NULL")
            checks.append((f"FK {child}.{col} -> {parent}", n == 0, f"{n} orphan(s)"))

    fk("machine_units", "product_id", "products")
    fk("machine_units", "vendor_id", "vendors")
    fk("machine_units", "sale_order_id", "sales_orders")
    fk("machine_units", "acquisition_po_id", "purchase_orders")
    fk("sales_order_lines", "machine_unit_id", "machine_units")
    fk("expenses", "category_id", "expense_categories")
    fk("payroll_items", "employee_id", "employees")
    fk("depreciation_entries", "asset_id", "fixed_assets")
    fk("shipments", "order_id", "sales_orders")
    fk("shipment_lines", "shipment_id", "shipments")
    fk("customs_declarations", "shipment_id", "shipments")
    fk("service_jobs", "machine_unit_id", "machine_units")
    fk("quotations", "opportunity_id", "opportunities")
    fk("vendor_invoices", "po_id", "purchase_orders")
    fk("budgets", "expense_category_id", "expense_categories")

    # every machine unit is either in stock or attached to exactly one sold line
    bad = _int(db, """
        SELECT count(*) FROM machine_units m
        WHERE (m.status = 'sold' AND (m.sale_order_line_id IS NULL OR m.sale_date IS NULL))
           OR (m.status <> 'sold' AND m.sale_order_id IS NOT NULL)""")
    checks.append(("Machine units consistently sold/in-stock", bad == 0, f"{bad} bad unit(s)"))

    dup = _int(db, """
        SELECT count(*) FROM (
          SELECT machine_unit_id FROM sales_order_lines
          WHERE machine_unit_id IS NOT NULL
          GROUP BY 1 HAVING count(*) > 1) x""")
    checks.append(("No machine sold twice", dup == 0, f"{dup} duplicate(s)"))

    bad = _int(db, """
        SELECT count(*) FROM machine_units
        WHERE abs(landed_cost - (acquisition_cost_base + transport_in_cost
                                 + refurb_cost + other_cost)) > 0.05""")
    checks.append(("Landed cost = acquisition + transport + refurb + other", bad == 0,
                   f"{bad} mismatch(es)"))

    bad = _int(db, """
        SELECT count(*) FROM (
          SELECT m.id FROM machine_units m
          JOIN refurbishment_jobs j ON j.machine_unit_id = m.id
          GROUP BY m.id, m.refurb_cost
          HAVING abs(m.refurb_cost - sum(j.total_cost)) > 0.05) x""")
    checks.append(("Refurb jobs reconcile to unit refurb cost", bad == 0, f"{bad} mismatch(es)"))

    # order totals reconcile in both currencies
    bad = _int(db, """
        SELECT count(*) FROM (
          SELECT o.id FROM sales_orders o JOIN sales_order_lines l ON l.order_id = o.id
          GROUP BY o.id, o.total, o.total_base
          HAVING abs(o.total - sum(l.line_total)) > 0.05
              OR abs(o.total_base - sum(l.line_total_base)) > 0.05) x""")
    checks.append(("Order totals reconcile (local + base)", bad == 0, f"{bad} mismatched order(s)"))

    bad = _int(db, "SELECT count(*) FROM invoices "
                   "WHERE abs(total_base - (subtotal_base + tax_base)) > 0.05")
    checks.append(("Invoice base totals reconcile", bad == 0, f"{bad} bad invoice(s)"))

    bad = _int(db, "SELECT count(*) FROM invoices WHERE round(amount_paid + balance, 2) <> round(total, 2)")
    checks.append(("Invoice paid + balance = total", bad == 0, f"{bad} inconsistent invoice(s)"))

    bad = _int(db, "SELECT count(*) FROM vendor_invoices WHERE round(amount_paid + balance, 2) <> round(total, 2)")
    checks.append(("Vendor bill paid + balance = total", bad == 0, f"{bad} inconsistent bill(s)"))

    # double-entry ledger balances, overall and entry by entry
    diff = _float(db, "SELECT coalesce(sum(debit_base) - sum(credit_base), 0) FROM gl_entries")
    checks.append(("GL balanced overall", abs(diff) < 1.0, f"debit-credit = {diff:,.2f}"))
    bad = _int(db, """
        SELECT count(*) FROM (
          SELECT entry_no FROM gl_entries GROUP BY entry_no
          HAVING abs(sum(debit_base) - sum(credit_base)) > 0.05) x""")
    checks.append(("Every journal entry balances", bad == 0, f"{bad} unbalanced entry/entries"))

    # FX: no document left without a rate, and base amounts actually differ
    bad = _int(db, "SELECT count(*) FROM sales_orders WHERE fx_rate IS NULL OR fx_rate <= 0")
    checks.append(("Every order carries an FX rate", bad == 0, f"{bad} missing"))
    ncur = _int(db, "SELECT count(DISTINCT currency) FROM sales_orders")
    checks.append(("Multi-currency trading present", (ncur or 0) >= 4, f"{ncur} currencies"))

    # revenue lands on the authored per-year curve
    off = []
    for yi in range(profile.years):
        year = profile.start_year + yi
        target = profile.revenue_for_year(yi)
        if yi == profile.years - 1 and profile.end_month < 12:
            share = sum(profile.seasonality[:profile.end_month]) / 12.0
            target *= share
        actual = _float(db, f"""
            SELECT coalesce(sum(l.line_subtotal_base), 0)
            FROM sales_orders o JOIN sales_order_lines l ON l.order_id = o.id
            WHERE o.status <> 'cancelled' AND extract(year FROM o.order_date) = {year}""")
        ratio = actual / target if target else 0
        if not (0.90 <= ratio <= 1.12):
            off.append(f"{year}:{ratio:.0%}")
    checks.append(("Revenue tracks the authored per-year curve", not off,
                   "all years within tolerance" if not off else "off-target " + ", ".join(off)))

    # the P&L must actually be profitable, but not absurdly so
    row = load.query_value(db, """
        SELECT round(sum(net_revenue))::text || '|' || round(sum(gross_profit))::text || '|' ||
               round(sum(operating_profit))::text || '|' || round(sum(net_profit))::text
        FROM v_pnl_yearly""")
    try:
        nr, gp, op, np_ = [float(x) for x in row.split("|")]
        gm = 100 * gp / nr if nr else 0
        nm = 100 * np_ / nr if nr else 0
        checks.append(("Gross margin in a dealer-plausible band", 12 <= gm <= 30,
                       f"{gm:.1f}% gross margin over the full history"))
        checks.append(("Net margin in a dealer-plausible band", 0.5 <= nm <= 12,
                       f"{nm:.1f}% net margin (net profit {np_:,.0f})"))
    except (ValueError, AttributeError):
        checks.append(("P&L view queryable", False, f"unexpected result: {row!r}"))

    # the P&L view and the ledger must tell the same story
    a = _float(db, "SELECT coalesce(sum(net_profit), 0) FROM v_pnl_yearly")
    b = _float(db, """
        SELECT coalesce(sum(CASE WHEN coa.account_type IN ('Revenue','Expense')
                                 THEN g.credit_base - g.debit_base ELSE 0 END), 0)
        FROM gl_entries g
        JOIN chart_of_accounts coa ON coa.account_code = g.account_code""")
    checks.append(("P&L view reconciles to the general ledger", abs(a - b) < 1.0,
                   f"P&L {a:,.0f} vs GL {b:,.0f}"))

    # inventory must never go negative — replenishment has to match consumption
    neg = _int(db, "SELECT count(*) FROM v_inventory_valuation WHERE on_hand_qty < 0")
    checks.append(("No negative stock on hand", neg == 0, f"{neg} negative categories"))

    # opex must be split across many categories, incl. the staff-catering line
    ncat = _int(db, "SELECT count(DISTINCT category_id) FROM expenses")
    checks.append(("Operating costs spread across categories", (ncat or 0) >= 25,
                   f"{ncat} expense categories used"))
    nsrc = _int(db, "SELECT count(DISTINCT source) FROM expenses")
    checks.append(("Cost sources complete (opex/payroll/depr/logistics/fin/tax)",
                   (nsrc or 0) >= 6, f"{nsrc} distinct sources"))

    return checks


def metrics(db, profile, selected):
    m = {}
    if "sales_orders" in selected:
        m["total_revenue"] = _float(db, "SELECT coalesce(sum(subtotal - discount),0) FROM sales_orders WHERE status<>'cancelled'")
        m["gross_with_tax"] = _float(db, "SELECT coalesce(sum(total),0) FROM sales_orders WHERE status<>'cancelled'")
        m["sales_orders"] = _int(db, "SELECT count(*) FROM sales_orders")
        m["date_min"] = load.query_value(db, "SELECT min(order_date) FROM sales_orders")
        m["date_max"] = load.query_value(db, "SELECT max(order_date) FROM sales_orders")
    if "invoices" in selected:
        m["open_ar"] = _float(db, "SELECT coalesce(sum(balance),0) FROM invoices")
    if "customers" in selected:
        m["customers"] = _int(db, "SELECT count(*) FROM customers")
    if "products" in selected:
        m["products"] = _int(db, "SELECT count(*) FROM products")
    if "production_operations" in selected:
        m["total_revenue"] = _float(db, """
            SELECT coalesce(sum(l.line_subtotal_base), 0)
            FROM sales_orders o JOIN sales_order_lines l ON l.order_id = o.id
            WHERE o.status <> 'İptal'""")
        m["gross_with_tax"] = _float(db, "SELECT coalesce(sum(total_base), 0) FROM invoices")
        m["open_ar"] = _float(db, "SELECT coalesce(sum(balance_base), 0) FROM invoices")
        m["units_sold"] = _float(db, """
            SELECT coalesce(sum(l.qty), 0)
            FROM sales_orders o JOIN sales_order_lines l ON l.order_id = o.id
            WHERE o.status <> 'İptal'""")
        m["pnl"] = load.query_value(db, """
            SELECT string_agg(yil || ': ciro ' || to_char(net_satislar_try/1e6, 'FM999.9') ||
                   ' mn TL / ' || to_char(net_satislar_eur/1e6, 'FM999.99') || ' mn EUR' ||
                   '  brüt(tam) ' || to_char(brut_kar_tam_yukleme_marj_pct, 'FM990.0') ||
                   '%  faaliyet ' || to_char(faaliyet_kari_marj_pct, 'FM990.0') ||
                   '%  net ' || to_char(net_kar_try/1e6, 'FM999.9') || ' mn TL (' ||
                   to_char(net_kar_marj_pct, 'FM990.0') || '%)', E'\n            ' ORDER BY yil)
            FROM v_pnl_yearly""")

    if "machine_units" in selected:
        m["total_revenue"] = _float(db, """
            SELECT coalesce(sum(l.line_subtotal_base), 0)
            FROM sales_orders o JOIN sales_order_lines l ON l.order_id = o.id
            WHERE o.status <> 'cancelled'""")
        m["open_ar"] = _float(db, "SELECT coalesce(sum(balance_base), 0) FROM invoices")
        m["gross_with_tax"] = _float(db, "SELECT coalesce(sum(total_base), 0) FROM invoices")
        m["machines_sold"] = _int(db, "SELECT count(*) FROM machine_units WHERE status = 'sold'")
        m["machines_in_stock"] = _int(db, "SELECT count(*) FROM machine_units WHERE status <> 'sold'")
        m["stock_value"] = _float(db, "SELECT coalesce(sum(landed_cost), 0) FROM machine_units WHERE status <> 'sold'")
        m["pnl"] = load.query_value(db, """
            SELECT string_agg(year || ': rev ' || to_char(net_revenue/1e6, 'FM999.9') ||
                   'M  gross ' || to_char(gross_margin_pct, 'FM990.0') || '%  net ' ||
                   to_char(net_profit/1e6, 'FM999.99') || 'M (' ||
                   to_char(net_margin_pct, 'FM990.0') || '%)', E'\n            ' ORDER BY year)
            FROM v_pnl_yearly""")
    return m


def _contract_checks(db, profile, selected, checks):
    """Talaşlı imalat (contract_machining) veritabanı için bütünlük ve
    gerçekçilik kontrolleri."""

    def fk(child, col, parent, pcol="id"):
        if child in selected and parent in selected:
            n = _int(db, f"SELECT count(*) FROM {child} c "
                         f"LEFT JOIN {parent} p ON c.{col}=p.{pcol} "
                         f"WHERE c.{col} IS NOT NULL AND p.{pcol} IS NULL")
            checks.append((f"FK {child}.{col} -> {parent}", n == 0, f"{n} artık kayıt"))

    fk("machines", "work_center_id", "work_centers")
    fk("routings", "product_id", "products")
    fk("routings", "work_center_id", "work_centers")
    fk("routings", "machine_id", "machines")
    fk("production_orders", "product_id", "products")
    fk("production_orders", "sales_order_id", "sales_orders")
    fk("production_operations", "production_order_id", "production_orders")
    fk("production_operations", "routing_id", "routings")
    fk("production_operations", "machine_id", "machines")
    fk("production_operations", "operator_id", "employees")
    fk("production_consumption", "raw_material_id", "raw_materials")
    fk("subcontract_operations", "production_order_id", "production_orders")
    fk("subcontract_operations", "purchase_order_id", "purchase_orders")
    fk("quality_inspections", "production_order_id", "production_orders")
    fk("nonconformances", "product_id", "products")
    fk("maintenance_orders", "machine_id", "machines")
    fk("hse_incidents", "employee_id", "employees")
    fk("lots", "production_order_id", "production_orders")
    fk("expenses", "category_id", "expense_categories")
    fk("payroll_items", "employee_id", "employees")
    fk("depreciation_entries", "asset_id", "fixed_assets")
    fk("shipments", "order_id", "sales_orders")
    fk("customs_declarations", "shipment_id", "shipments")
    fk("part_approvals", "product_id", "products")
    fk("vendor_invoices", "po_id", "purchase_orders")
    fk("budgets", "expense_category_id", "expense_categories")
    fk("fixed_assets", "machine_id", "machines")

    # --- belge toplamları
    bad = _int(db, """
        SELECT count(*) FROM (
          SELECT o.id FROM sales_orders o JOIN sales_order_lines l ON l.order_id = o.id
          GROUP BY o.id, o.total, o.total_base
          HAVING abs(o.total - sum(l.line_total)) > 0.05
              OR abs(o.total_base - sum(l.line_total_base)) > 0.05) x""")
    checks.append(("Sipariş toplamları satırlarla uyumlu (TL + belge PB)", bad == 0,
                   f"{bad} uyumsuz sipariş"))
    bad = _int(db, "SELECT count(*) FROM invoices "
                   "WHERE abs(total_base - (subtotal_base + tax_base)) > 0.05")
    checks.append(("Fatura TL toplamları tutarlı", bad == 0, f"{bad} hatalı fatura"))
    bad = _int(db, "SELECT count(*) FROM invoices "
                   "WHERE round(amount_paid + balance, 2) <> round(total, 2)")
    checks.append(("Fatura: tahsil + bakiye = toplam", bad == 0, f"{bad} tutarsız fatura"))
    bad = _int(db, "SELECT count(*) FROM vendor_invoices "
                   "WHERE round(amount_paid + balance, 2) <> round(total, 2)")
    checks.append(("Alış faturası: ödenen + bakiye = toplam", bad == 0, f"{bad} tutarsız"))

    # --- çok para birimi
    bad = _int(db, "SELECT count(*) FROM sales_orders WHERE fx_rate IS NULL OR fx_rate <= 0 "
                   "OR fx_rate_eur IS NULL OR fx_rate_usd IS NULL")
    checks.append(("Her siparişte TL/EUR/USD kuru var", bad == 0, f"{bad} eksik"))
    ncur = _int(db, "SELECT count(DISTINCT currency) FROM sales_orders")
    checks.append(("Çok para birimli satış mevcut", (ncur or 0) >= 3, f"{ncur} para birimi"))
    bad = _int(db, """
        SELECT count(*) FROM sales_orders
        WHERE subtotal_eur > 0
          AND abs(subtotal_eur - round(subtotal_base / fx_rate_eur, 2))
              > greatest(0.05, subtotal_base * 0.00002)""")
    checks.append(("EUR karşılıkları TL / kur ile tutarlı", bad == 0, f"{bad} sapma"))
    bad = _int(db, """
        SELECT count(*) FROM sales_orders
        WHERE subtotal_usd > 0
          AND abs(subtotal_usd - round(subtotal_base / fx_rate_usd, 2))
              > greatest(0.05, subtotal_base * 0.00002)""")
    checks.append(("USD karşılıkları TL / kur ile tutarlı", bad == 0, f"{bad} sapma"))
    n = _int(db, "SELECT count(*) FROM fx_rates WHERE currency_code = 'EUR'")
    checks.append(("Günlük EUR kuru serisi tam", (n or 0) > 1500, f"{n} günlük kur kaydı"))

    # --- ciro hedef eğrisine oturuyor mu
    off = []
    for yi in range(profile.years):
        year = profile.start_year + yi
        target = profile.revenue_for_year(yi)
        if yi == profile.years - 1 and profile.end_month < 12:
            target *= sum(profile.seasonality[:profile.end_month]) / 12.0
        actual = _float(db, f"""
            SELECT coalesce(sum(l.line_subtotal_base), 0)
            FROM sales_orders o JOIN sales_order_lines l ON l.order_id = o.id
            WHERE o.status <> 'İptal' AND extract(year FROM o.order_date) = {year}""")
        ratio = actual / target if target else 0
        if not (0.92 <= ratio <= 1.10):
            off.append(f"{year}:{ratio:.0%}")
    checks.append(("Ciro yazılan yıllık eğriyi takip ediyor", not off,
                   "tüm yıllar tolerans içinde" if not off else "sapan: " + ", ".join(off)))

    # --- yevmiye dengesi
    diff = _float(db, "SELECT coalesce(sum(debit_base) - sum(credit_base), 0) FROM gl_entries")
    checks.append(("Yevmiye genel dengesi", abs(diff) < 2.0, f"borç-alacak = {diff:,.2f}"))
    bad = _int(db, """
        SELECT count(*) FROM (
          SELECT entry_no FROM gl_entries GROUP BY entry_no
          HAVING abs(sum(debit_base) - sum(credit_base)) > 0.05) x""")
    checks.append(("Her yevmiye fişi dengeli", bad == 0, f"{bad} dengesiz fiş"))
    bad = _int(db, """
        SELECT count(*) FROM gl_entries g
        LEFT JOIN chart_of_accounts c ON c.account_code = g.account_code
        WHERE c.account_code IS NULL""")
    checks.append(("Tüm yevmiye satırları hesap planında", bad == 0, f"{bad} tanımsız hesap"))

    # --- gelir tablosu
    row = load.query_value(db, """
        SELECT round(sum(net_satislar_try))::text || '|' || round(sum(brut_kar_try))::text
               || '|' || round(sum(brut_kar_tam_yukleme_try))::text || '|'
               || round(sum(faaliyet_kari_try))::text || '|' || round(sum(net_kar_try))::text
        FROM v_pnl_yearly""")
    try:
        nr, gp, gpf, op, np_ = [float(x) for x in row.split("|")]
        gm = 100 * gp / nr if nr else 0
        gmf = 100 * gpf / nr if nr else 0
        om = 100 * op / nr if nr else 0
        nm = 100 * np_ / nr if nr else 0
        checks.append(("Direkt brüt kâr marjı fason imalata uygun bantta", 40 <= gm <= 60,
                       f"%{gm:.1f} (direkt SMM üzerinden)"))
        checks.append(("Tam yükleme brüt kâr marjı bantta", 20 <= gmf <= 38,
                       f"%{gmf:.1f} (üretim genel giderleri dahil)"))
        checks.append(("Faaliyet kâr marjı bantta", 6 <= om <= 20, f"%{om:.1f}"))
        checks.append(("Net kâr marjı bantta", 2 <= nm <= 14,
                       f"%{nm:.1f} (net kâr {np_:,.0f} TL)"))
    except (ValueError, AttributeError):
        checks.append(("Gelir tablosu görünümü sorgulanabilir", False, f"beklenmeyen: {row!r}"))

    a = _float(db, "SELECT coalesce(sum(net_kar_try), 0) FROM v_pnl_yearly")
    b = _float(db, """
        SELECT coalesce(sum(CASE WHEN coa.account_type IN ('Revenue','Expense')
                                 THEN g.credit_base - g.debit_base ELSE 0 END), 0)
        FROM gl_entries g JOIN chart_of_accounts coa ON coa.account_code = g.account_code""")
    checks.append(("Gelir tablosu yevmiye ile mutabık", abs(a - b) < 2.0,
                   f"gelir tablosu {a:,.0f} TL vs yevmiye {b:,.0f} TL"))

    # --- stok
    neg = _int(db, "SELECT count(*) FROM v_inventory_valuation WHERE eldeki_miktar < 0")
    checks.append(("Negatif stok yok", neg == 0, f"{neg} kalemde negatif bakiye"))

    # --- maliyet ve gider dağılımı
    ncat = _int(db, "SELECT count(DISTINCT category_id) FROM expenses")
    checks.append(("Giderler kategorilere yayılmış", (ncat or 0) >= 35,
                   f"{ncat} gider kategorisi kullanıldı"))
    nsrc = _int(db, "SELECT count(DISTINCT source) FROM expenses")
    checks.append(("Gider kaynakları tam (satın alma/personel/amortisman/lojistik/finansman/vergi)",
                   (nsrc or 0) >= 6, f"{nsrc} farklı kaynak"))
    bad = _int(db, """
        SELECT count(*) FROM expenses e JOIN expense_categories ec ON ec.id = e.category_id
        WHERE ec.account_code = '620'""")
    checks.append(("Direkt maliyet gider tablosunda tekrarlanmıyor", bad == 0,
                   f"{bad} satır 620 hesabına gider olarak yazılmış"))

    # --- üretim
    bad = _int(db, """
        SELECT count(*) FROM production_orders w
        WHERE w.status <> 'İptal' AND NOT EXISTS
              (SELECT 1 FROM production_operations o WHERE o.production_order_id = w.id)""")
    checks.append(("Her iş emrinin operasyon kaydı var", bad == 0, f"{bad} operasyonsuz iş emri"))
    bad = _int(db, "SELECT count(*) FROM production_orders "
                   "WHERE produced_qty > planned_qty + 0.01")
    checks.append(("Üretilen miktar planlananı aşmıyor", bad == 0, f"{bad} iş emri"))
    bad = _int(db, """
        SELECT count(*) FROM production_orders w
        WHERE w.status <> 'İptal'
          AND abs(w.total_cost - (w.material_cost + w.labor_cost + w.machine_cost
                                  + w.tooling_cost + w.subcontract_cost
                                  + w.overhead_cost)) > 0.05""")
    checks.append(("İş emri maliyeti bileşenlerine eşit", bad == 0, f"{bad} uyumsuz iş emri"))
    bad = _int(db, """
        SELECT count(*) FROM production_orders w
        WHERE w.status <> 'İptal' AND NOT EXISTS
              (SELECT 1 FROM production_consumption c WHERE c.production_order_id = w.id)""")
    checks.append(("Her iş emrinde malzeme sarfiyatı var", bad == 0, f"{bad} sarfiyatsız iş emri"))
    bad = _int(db, """
        SELECT count(*) FROM (
          SELECT p.id FROM products p
          JOIN sales_order_lines l ON l.product_id = p.id
          WHERE NOT EXISTS (SELECT 1 FROM routings r WHERE r.product_id = p.id)
          GROUP BY p.id) x""")
    checks.append(("Satılan her parçanın operasyon rotası var", bad == 0, f"{bad} rotasız parça"))
    n = _int(db, "SELECT count(*) FROM subcontract_operations")
    checks.append(("Fason operasyon akışı mevcut", (n or 0) > 100, f"{n} fason sevkiyatı"))

    # --- kapasite gerçekçiliği
    util = _float(db, """
        SELECT coalesce(avg(kapasite_kullanim_pct), 0) FROM v_capacity_by_work_center
        WHERE yuklenen_saat > 0""")
    checks.append(("Tezgah kapasite kullanımı makul bantta", 8 <= util <= 95,
                   f"ortalama %{util:.1f} iş merkezi kapasite kullanımı"))

    # --- kalite
    n = _int(db, "SELECT count(*) FROM quality_inspections")
    checks.append(("Kalite kontrol kayıtları mevcut", (n or 0) > 1000, f"{n} kontrol kaydı"))
    n = _int(db, "SELECT count(*) FROM nonconformances WHERE is_customer_complaint")
    checks.append(("Müşteri şikayeti kayıtları mevcut", (n or 0) > 20, f"{n} müşteri şikayeti"))
    bad = _int(db, """
        SELECT count(*) FROM nonconformances
        WHERE abs(total_cost - (rework_cost + scrap_cost + other_cost)) > 0.05""")
    checks.append(("Uygunsuzluk maliyeti bileşenlerine eşit", bad == 0, f"{bad} uyumsuz kayıt"))

    # --- İK
    months = (profile.years - 1) * 12 + profile.end_month
    n = _int(db, "SELECT count(*) FROM payroll_runs")
    checks.append(("Her ay için bordro dönemi var", n == months, f"{n}/{months} bordro dönemi"))
    bad = _int(db, """
        SELECT count(*) FROM payroll_items
        WHERE abs(net_pay - (gross_pay - employee_social - income_tax
                             - other_deductions)) > 0.05""")
    checks.append(("Bordro: net = brüt - kesintiler", bad == 0, f"{bad} tutarsız satır"))
    bad = _int(db, """
        SELECT count(*) FROM payroll_items pi JOIN employees e ON e.id = pi.employee_id
        WHERE pi.period_date < e.hire_date
           OR (e.termination_date IS NOT NULL AND pi.period_date > e.termination_date + 31)""")
    checks.append(("Bordro dönemleri istihdam süresiyle uyumlu", bad == 0, f"{bad} hatalı satır"))

    # --- lojistik ve gümrük
    bad = _int(db, """
        SELECT count(*) FROM sales_orders o
        WHERE o.status <> 'İptal'
          AND NOT EXISTS (SELECT 1 FROM shipments s WHERE s.order_id = o.id)""")
    checks.append(("Her sipariş için sevkiyat kaydı var", bad == 0, f"{bad} sevkiyatsız sipariş"))
    bad = _int(db, """
        SELECT count(*) FROM shipments s
        WHERE s.is_export
          AND NOT EXISTS (SELECT 1 FROM customs_declarations c WHERE c.shipment_id = s.id)""")
    checks.append(("Her ihracat sevkiyatının gümrük beyannamesi var", bad == 0,
                   f"{bad} beyannamesiz ihracat"))
    share = _float(db, """
        SELECT 100.0 * sum(CASE WHEN o.is_export THEN l.line_subtotal_base ELSE 0 END)
               / NULLIF(sum(l.line_subtotal_base), 0)
        FROM sales_orders o JOIN sales_order_lines l ON l.order_id = o.id
        WHERE o.status <> 'İptal'""")
    checks.append(("İhracat payı hedefe yakın", 28 <= share <= 46, f"ciro içinde %{share:.1f}"))

    # --- tarih sınırları
    bad = _int(db, f"SELECT count(*) FROM sales_orders WHERE order_date > DATE "
                   f"'{profile.end_year()}-{profile.end_month:02d}-28' + 4")
    checks.append(("Gelecek tarihli sipariş yok", bad == 0, f"{bad} sipariş"))

    return checks
