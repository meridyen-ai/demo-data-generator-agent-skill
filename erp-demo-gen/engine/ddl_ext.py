"""Extended ERP tables: finance, HR/payroll, CRM, logistics, assets, service.

The base ddl.py covers the sales/purchasing/inventory core shared by every
industry. This module adds the modules a "full ERP" demo needs so that a
complete P&L (gross profit -> operating profit -> net profit) can be derived
from the data, plus the serialized-unit model a used-machinery dealer needs.

Nothing here is active unless an industry's tables.json includes the table, so
existing industries are unaffected. ``install()`` merges these definitions into
ddl.py's module-level registries.
"""
from __future__ import annotations

# Where each new table slots into the canonical create/load order. The value is
# the existing table it must be created AFTER (parents before children).
ORDER_AFTER = [
    ("company", None),                 # None -> very front
    ("currencies", "company"),
    ("fx_rates", "currencies"),
    ("tax_codes", "fx_rates"),
    ("chart_of_accounts", "tax_codes"),
    ("expense_categories", "chart_of_accounts"),
    ("carriers", "vendors"),
    ("machine_units", "products"),
    ("refurbishment_jobs", "machine_units"),
    ("leads", "machine_units"),
    ("opportunities", "leads"),
    ("quotations", "opportunities"),
    ("quotation_lines", "quotations"),
    ("crm_activities", "quotations"),
    ("vendor_invoices", "purchase_order_lines"),
    ("vendor_payments", "vendor_invoices"),
    ("shipments", "vendor_payments"),
    ("shipment_lines", "shipments"),
    ("customs_declarations", "shipment_lines"),
    ("service_jobs", "customs_declarations"),
    ("warranty_contracts", "service_jobs"),
    ("payroll_runs", "warranty_contracts"),
    ("payroll_items", "payroll_runs"),
    ("leave_records", "payroll_items"),
    ("fixed_assets", "leave_records"),
    ("depreciation_entries", "fixed_assets"),
    ("expenses", "depreciation_entries"),
    ("budgets", "expenses"),
]

COLUMNS = {
    "company": [
        "id", "name", "legal_name", "tagline", "founded_year", "hq_address", "hq_city",
        "hq_postcode", "hq_country", "vat_number", "registration_no", "domain",
        "base_currency", "fiscal_year_end", "employee_count", "website", "phone"],

    "currencies": ["code", "name", "symbol", "is_base", "decimals"],

    "fx_rates": ["id", "rate_date", "currency_code", "base_currency",
                 "rate_per_base", "base_per_unit"],

    "tax_codes": ["id", "code", "name", "rate_pct", "tax_type", "region",
                  "applies_to", "description"],

    "chart_of_accounts": ["id", "account_code", "account_name", "account_type",
                          "account_subtype", "normal_side", "is_pnl", "pnl_section",
                          "parent_code"],

    "expense_categories": ["id", "code", "name", "expense_group", "account_code",
                           "is_fixed", "variability_pct", "is_cash", "description"],

    "expenses": ["id", "expense_no", "expense_date", "period_year", "period_month",
                 "category_id", "department_id", "vendor_id", "employee_id",
                 "warehouse_id", "cost_center", "description", "currency", "amount",
                 "fx_rate", "amount_base", "tax_amount", "total_base", "payment_method",
                 "status", "source", "reference_type", "reference_id"],

    "budgets": ["id", "fiscal_year", "period_month", "department_id",
                "expense_category_id", "budget_amount", "budget_type", "approved_by"],

    "fixed_assets": ["id", "asset_no", "name", "category", "department_id",
                     "warehouse_id", "vendor_id", "acquisition_date", "acquisition_cost",
                     "useful_life_years", "salvage_value", "method", "status",
                     "disposal_date", "disposal_proceeds", "accumulated_depreciation",
                     "net_book_value", "serial_no"],

    "depreciation_entries": ["id", "asset_id", "period_year", "period_month",
                             "period_date", "depreciation_amount", "accumulated_after",
                             "book_value_after"],

    "vendor_invoices": ["id", "bill_no", "vendor_id", "po_id", "bill_date", "due_date",
                        "spend_category", "currency", "fx_rate", "subtotal", "tax",
                        "total", "total_base", "amount_paid", "balance", "status"],

    "vendor_payments": ["id", "payment_no", "vendor_invoice_id", "vendor_id",
                        "payment_date", "method", "currency", "fx_rate", "amount",
                        "amount_base"],

    "payroll_runs": ["id", "run_no", "period_year", "period_month", "period_date",
                     "country", "pay_date", "currency", "employee_count", "gross_total",
                     "employee_deductions_total", "net_total", "employer_cost_total",
                     "employer_cost_base", "status"],

    "payroll_items": ["id", "payroll_run_id", "employee_id", "period_year",
                      "period_month", "period_date", "country", "base_salary",
                      "overtime_pay", "bonus", "allowances", "gross_pay",
                      "employee_social", "income_tax", "other_deductions", "net_pay",
                      "employer_social", "employer_other", "employer_cost", "currency",
                      "fx_rate", "employer_cost_base"],

    "leave_records": ["id", "employee_id", "leave_type", "start_date", "end_date",
                      "days", "status", "approved_by", "note"],

    "leads": ["id", "lead_no", "company_name", "contact_name", "email", "phone",
              "country", "city", "source", "interest_category", "created_date",
              "status", "score", "owner_id", "converted_customer_id", "converted_date",
              "lost_reason"],

    "opportunities": ["id", "opp_no", "customer_id", "lead_id", "owner_id", "title",
                      "product_category", "machine_category", "created_date",
                      "expected_close_date", "close_date", "stage", "probability_pct",
                      "currency", "amount", "fx_rate", "amount_base", "status",
                      "win_loss_reason", "competitor", "source"],

    "quotations": ["id", "quote_no", "opportunity_id", "customer_id", "salesperson_id",
                   "quote_date", "valid_until", "currency", "fx_rate", "subtotal",
                   "discount", "tax", "total", "total_base", "status",
                   "converted_order_id", "incoterm", "lead_time_days"],

    "quotation_lines": ["id", "quote_id", "line_no", "product_id", "machine_unit_id",
                        "description", "qty", "unit_price", "discount_pct", "line_total"],

    "crm_activities": ["id", "activity_date", "activity_type", "opportunity_id",
                       "lead_id", "customer_id", "employee_id", "subject", "outcome",
                       "duration_min"],

    "carriers": ["id", "name", "carrier_type", "mode", "country", "city", "scac",
                 "is_customs_broker", "email", "phone"],

    "shipments": ["id", "shipment_no", "order_id", "invoice_id", "customer_id",
                  "carrier_id", "warehouse_id", "ship_date", "eta_date", "delivery_date",
                  "incoterm", "mode", "origin_country", "dest_country", "dest_city",
                  "is_export", "is_intra_eu", "gross_weight_kg", "volume_m3", "packages",
                  "container_type", "freight_cost", "insurance_cost", "packing_cost",
                  "handling_cost", "total_logistics_cost", "currency", "fx_rate",
                  "cost_base", "billed_to_customer", "status", "tracking_no",
                  "transit_days"],

    "shipment_lines": ["id", "shipment_id", "order_line_id", "product_id",
                       "machine_unit_id", "description", "qty", "weight_kg", "hs_code",
                       "country_of_origin"],

    "customs_declarations": ["id", "declaration_no", "shipment_id", "decl_date",
                             "direction", "customs_office", "document_type", "hs_code",
                             "dest_country", "currency", "fx_rate", "customs_value",
                             "customs_value_base", "duty_rate_pct", "duty_amount",
                             "vat_amount", "broker_id", "broker_fee", "status"],

    "machine_units": ["id", "unit_no", "product_id", "manufacturer", "model",
                      "serial_no", "year_built", "control_system", "spindle_hours",
                      "operating_hours", "condition_grade", "weight_kg", "power_kw",
                      "dimensions", "source_type", "vendor_id", "acquisition_po_id",
                      "acquisition_date", "currency", "fx_rate", "acquisition_cost",
                      "acquisition_cost_base", "transport_in_cost", "refurb_cost",
                      "other_cost", "landed_cost", "asking_price", "status",
                      "warehouse_id", "listed_date", "sale_order_id",
                      "sale_order_line_id", "sale_invoice_id", "sale_date",
                      "sale_price_base", "days_in_stock", "gross_profit",
                      "gross_margin_pct"],

    "refurbishment_jobs": ["id", "job_no", "machine_unit_id", "work_type", "start_date",
                           "end_date", "technician_id", "warehouse_id", "labor_hours",
                           "labor_rate", "labor_cost", "parts_cost", "external_cost",
                           "total_cost", "status", "notes"],

    "service_jobs": ["id", "job_no", "machine_unit_id", "customer_id", "job_type",
                     "request_date", "scheduled_date", "completion_date", "technician_id",
                     "country", "labor_hours", "labor_cost", "parts_cost", "travel_cost",
                     "total_cost", "billable_amount", "currency", "fx_rate",
                     "billable_base", "is_warranty", "status", "sla_days",
                     "response_days", "satisfaction_score"],

    "warranty_contracts": ["id", "contract_no", "machine_unit_id", "customer_id",
                           "invoice_id", "start_date", "end_date", "months",
                           "coverage_type", "price", "currency", "price_base", "status",
                           "claims_count", "claims_cost"],
}

DDL = {
    "company": """
CREATE TABLE {s}company (
    id INT PRIMARY KEY, name TEXT, legal_name TEXT, tagline TEXT, founded_year INT,
    hq_address TEXT, hq_city TEXT, hq_postcode TEXT, hq_country TEXT, vat_number TEXT,
    registration_no TEXT, domain TEXT, base_currency TEXT, fiscal_year_end TEXT,
    employee_count INT, website TEXT, phone TEXT
);""",
    "currencies": """
CREATE TABLE {s}currencies (
    code TEXT PRIMARY KEY, name TEXT, symbol TEXT, is_base BOOLEAN, decimals INT
);""",
    "fx_rates": """
CREATE TABLE {s}fx_rates (
    id INT PRIMARY KEY, rate_date DATE, currency_code TEXT REFERENCES {s}currencies(code),
    base_currency TEXT, rate_per_base NUMERIC(18,8), base_per_unit NUMERIC(18,8)
);""",
    "tax_codes": """
CREATE TABLE {s}tax_codes (
    id INT PRIMARY KEY, code TEXT, name TEXT, rate_pct NUMERIC(6,3), tax_type TEXT,
    region TEXT, applies_to TEXT, description TEXT
);""",
    "chart_of_accounts": """
CREATE TABLE {s}chart_of_accounts (
    id INT PRIMARY KEY, account_code TEXT UNIQUE, account_name TEXT, account_type TEXT,
    account_subtype TEXT, normal_side TEXT, is_pnl BOOLEAN, pnl_section TEXT,
    parent_code TEXT
);""",
    "expense_categories": """
CREATE TABLE {s}expense_categories (
    id INT PRIMARY KEY, code TEXT, name TEXT, expense_group TEXT, account_code TEXT,
    is_fixed BOOLEAN, variability_pct NUMERIC(5,2), is_cash BOOLEAN, description TEXT
);""",
    "expenses": """
CREATE TABLE {s}expenses (
    id BIGINT PRIMARY KEY, expense_no TEXT, expense_date DATE, period_year INT,
    period_month INT, category_id INT REFERENCES {s}expense_categories(id),
    department_id INT REFERENCES {s}departments(id), vendor_id INT REFERENCES {s}vendors(id),
    employee_id INT REFERENCES {s}employees(id), warehouse_id INT, cost_center TEXT,
    description TEXT, currency TEXT, amount NUMERIC(16,2), fx_rate NUMERIC(18,8),
    amount_base NUMERIC(16,2), tax_amount NUMERIC(16,2), total_base NUMERIC(16,2),
    payment_method TEXT, status TEXT, source TEXT, reference_type TEXT, reference_id INT
);""",
    "budgets": """
CREATE TABLE {s}budgets (
    id INT PRIMARY KEY, fiscal_year INT, period_month INT,
    department_id INT REFERENCES {s}departments(id),
    expense_category_id INT REFERENCES {s}expense_categories(id),
    budget_amount NUMERIC(16,2), budget_type TEXT, approved_by TEXT
);""",
    "fixed_assets": """
CREATE TABLE {s}fixed_assets (
    id INT PRIMARY KEY, asset_no TEXT, name TEXT, category TEXT,
    department_id INT REFERENCES {s}departments(id), warehouse_id INT,
    vendor_id INT REFERENCES {s}vendors(id), acquisition_date DATE,
    acquisition_cost NUMERIC(16,2), useful_life_years INT, salvage_value NUMERIC(16,2),
    method TEXT, status TEXT, disposal_date DATE, disposal_proceeds NUMERIC(16,2),
    accumulated_depreciation NUMERIC(16,2), net_book_value NUMERIC(16,2), serial_no TEXT
);""",
    "depreciation_entries": """
CREATE TABLE {s}depreciation_entries (
    id BIGINT PRIMARY KEY, asset_id INT REFERENCES {s}fixed_assets(id),
    period_year INT, period_month INT, period_date DATE,
    depreciation_amount NUMERIC(16,2), accumulated_after NUMERIC(16,2),
    book_value_after NUMERIC(16,2)
);""",
    "vendor_invoices": """
CREATE TABLE {s}vendor_invoices (
    id INT PRIMARY KEY, bill_no TEXT, vendor_id INT REFERENCES {s}vendors(id),
    po_id INT REFERENCES {s}purchase_orders(id), bill_date DATE, due_date DATE,
    spend_category TEXT, currency TEXT, fx_rate NUMERIC(18,8), subtotal NUMERIC(16,2),
    tax NUMERIC(16,2), total NUMERIC(16,2), total_base NUMERIC(16,2),
    amount_paid NUMERIC(16,2), balance NUMERIC(16,2), status TEXT
);""",
    "vendor_payments": """
CREATE TABLE {s}vendor_payments (
    id INT PRIMARY KEY, payment_no TEXT,
    vendor_invoice_id INT REFERENCES {s}vendor_invoices(id),
    vendor_id INT REFERENCES {s}vendors(id), payment_date DATE, method TEXT,
    currency TEXT, fx_rate NUMERIC(18,8), amount NUMERIC(16,2), amount_base NUMERIC(16,2)
);""",
    "payroll_runs": """
CREATE TABLE {s}payroll_runs (
    id INT PRIMARY KEY, run_no TEXT, period_year INT, period_month INT, period_date DATE,
    country TEXT, pay_date DATE, currency TEXT, employee_count INT,
    gross_total NUMERIC(16,2), employee_deductions_total NUMERIC(16,2),
    net_total NUMERIC(16,2), employer_cost_total NUMERIC(16,2),
    employer_cost_base NUMERIC(16,2), status TEXT
);""",
    "payroll_items": """
CREATE TABLE {s}payroll_items (
    id BIGINT PRIMARY KEY, payroll_run_id INT REFERENCES {s}payroll_runs(id),
    employee_id INT REFERENCES {s}employees(id), period_year INT, period_month INT,
    period_date DATE, country TEXT, base_salary NUMERIC(14,2), overtime_pay NUMERIC(14,2),
    bonus NUMERIC(14,2), allowances NUMERIC(14,2), gross_pay NUMERIC(14,2),
    employee_social NUMERIC(14,2), income_tax NUMERIC(14,2),
    other_deductions NUMERIC(14,2), net_pay NUMERIC(14,2), employer_social NUMERIC(14,2),
    employer_other NUMERIC(14,2), employer_cost NUMERIC(14,2), currency TEXT,
    fx_rate NUMERIC(18,8), employer_cost_base NUMERIC(14,2)
);""",
    "leave_records": """
CREATE TABLE {s}leave_records (
    id INT PRIMARY KEY, employee_id INT REFERENCES {s}employees(id), leave_type TEXT,
    start_date DATE, end_date DATE, days NUMERIC(6,2), status TEXT, approved_by INT,
    note TEXT
);""",
    "leads": """
CREATE TABLE {s}leads (
    id INT PRIMARY KEY, lead_no TEXT, company_name TEXT, contact_name TEXT, email TEXT,
    phone TEXT, country TEXT, city TEXT, source TEXT, interest_category TEXT,
    created_date DATE, status TEXT, score INT, owner_id INT REFERENCES {s}employees(id),
    converted_customer_id INT REFERENCES {s}customers(id), converted_date DATE,
    lost_reason TEXT
);""",
    "opportunities": """
CREATE TABLE {s}opportunities (
    id INT PRIMARY KEY, opp_no TEXT, customer_id INT REFERENCES {s}customers(id),
    lead_id INT REFERENCES {s}leads(id), owner_id INT REFERENCES {s}employees(id),
    title TEXT, product_category TEXT, machine_category TEXT, created_date DATE,
    expected_close_date DATE, close_date DATE, stage TEXT, probability_pct NUMERIC(5,2),
    currency TEXT, amount NUMERIC(16,2), fx_rate NUMERIC(18,8), amount_base NUMERIC(16,2),
    status TEXT, win_loss_reason TEXT, competitor TEXT, source TEXT
);""",
    "quotations": """
CREATE TABLE {s}quotations (
    id INT PRIMARY KEY, quote_no TEXT, opportunity_id INT REFERENCES {s}opportunities(id),
    customer_id INT REFERENCES {s}customers(id), salesperson_id INT REFERENCES {s}employees(id),
    quote_date DATE, valid_until DATE, currency TEXT, fx_rate NUMERIC(18,8),
    subtotal NUMERIC(16,2), discount NUMERIC(16,2), tax NUMERIC(16,2),
    total NUMERIC(16,2), total_base NUMERIC(16,2), status TEXT, converted_order_id INT,
    incoterm TEXT, lead_time_days INT
);""",
    "quotation_lines": """
CREATE TABLE {s}quotation_lines (
    id BIGINT PRIMARY KEY, quote_id INT REFERENCES {s}quotations(id), line_no INT,
    product_id INT REFERENCES {s}products(id), machine_unit_id INT, description TEXT,
    qty NUMERIC(12,2), unit_price NUMERIC(16,4), discount_pct NUMERIC(5,2),
    line_total NUMERIC(16,2)
);""",
    "crm_activities": """
CREATE TABLE {s}crm_activities (
    id BIGINT PRIMARY KEY, activity_date DATE, activity_type TEXT,
    opportunity_id INT REFERENCES {s}opportunities(id), lead_id INT REFERENCES {s}leads(id),
    customer_id INT REFERENCES {s}customers(id), employee_id INT REFERENCES {s}employees(id),
    subject TEXT, outcome TEXT, duration_min INT
);""",
    "carriers": """
CREATE TABLE {s}carriers (
    id INT PRIMARY KEY, name TEXT, carrier_type TEXT, mode TEXT, country TEXT, city TEXT,
    scac TEXT, is_customs_broker BOOLEAN, email TEXT, phone TEXT
);""",
    "shipments": """
CREATE TABLE {s}shipments (
    id INT PRIMARY KEY, shipment_no TEXT, order_id INT REFERENCES {s}sales_orders(id),
    invoice_id INT REFERENCES {s}invoices(id), customer_id INT REFERENCES {s}customers(id),
    carrier_id INT REFERENCES {s}carriers(id), warehouse_id INT, ship_date DATE,
    eta_date DATE, delivery_date DATE, incoterm TEXT, mode TEXT, origin_country TEXT,
    dest_country TEXT, dest_city TEXT, is_export BOOLEAN, is_intra_eu BOOLEAN,
    gross_weight_kg NUMERIC(14,2), volume_m3 NUMERIC(12,2), packages INT,
    container_type TEXT, freight_cost NUMERIC(14,2), insurance_cost NUMERIC(14,2),
    packing_cost NUMERIC(14,2), handling_cost NUMERIC(14,2),
    total_logistics_cost NUMERIC(14,2), currency TEXT, fx_rate NUMERIC(18,8),
    cost_base NUMERIC(14,2), billed_to_customer NUMERIC(14,2), status TEXT,
    tracking_no TEXT, transit_days INT
);""",
    "shipment_lines": """
CREATE TABLE {s}shipment_lines (
    id BIGINT PRIMARY KEY, shipment_id INT REFERENCES {s}shipments(id),
    order_line_id BIGINT, product_id INT REFERENCES {s}products(id),
    machine_unit_id INT, description TEXT, qty NUMERIC(12,2), weight_kg NUMERIC(14,2),
    hs_code TEXT, country_of_origin TEXT
);""",
    "customs_declarations": """
CREATE TABLE {s}customs_declarations (
    id INT PRIMARY KEY, declaration_no TEXT, shipment_id INT REFERENCES {s}shipments(id),
    decl_date DATE, direction TEXT, customs_office TEXT, document_type TEXT, hs_code TEXT,
    dest_country TEXT, currency TEXT, fx_rate NUMERIC(18,8), customs_value NUMERIC(16,2),
    customs_value_base NUMERIC(16,2), duty_rate_pct NUMERIC(6,3), duty_amount NUMERIC(14,2),
    vat_amount NUMERIC(14,2), broker_id INT REFERENCES {s}carriers(id),
    broker_fee NUMERIC(12,2), status TEXT
);""",
    "machine_units": """
CREATE TABLE {s}machine_units (
    id INT PRIMARY KEY, unit_no TEXT, product_id INT REFERENCES {s}products(id),
    manufacturer TEXT, model TEXT, serial_no TEXT, year_built INT, control_system TEXT,
    spindle_hours INT, operating_hours INT, condition_grade TEXT, weight_kg NUMERIC(12,2),
    power_kw NUMERIC(10,2), dimensions TEXT, source_type TEXT,
    vendor_id INT REFERENCES {s}vendors(id), acquisition_po_id INT,
    acquisition_date DATE, currency TEXT, fx_rate NUMERIC(18,8),
    acquisition_cost NUMERIC(16,2), acquisition_cost_base NUMERIC(16,2),
    transport_in_cost NUMERIC(14,2), refurb_cost NUMERIC(14,2), other_cost NUMERIC(14,2),
    landed_cost NUMERIC(16,2), asking_price NUMERIC(16,2), status TEXT, warehouse_id INT,
    listed_date DATE, sale_order_id INT, sale_order_line_id BIGINT, sale_invoice_id INT,
    sale_date DATE, sale_price_base NUMERIC(16,2), days_in_stock INT,
    gross_profit NUMERIC(16,2), gross_margin_pct NUMERIC(7,3)
);""",
    "refurbishment_jobs": """
CREATE TABLE {s}refurbishment_jobs (
    id INT PRIMARY KEY, job_no TEXT, machine_unit_id INT REFERENCES {s}machine_units(id),
    work_type TEXT, start_date DATE, end_date DATE,
    technician_id INT REFERENCES {s}employees(id), warehouse_id INT,
    labor_hours NUMERIC(10,2), labor_rate NUMERIC(10,2), labor_cost NUMERIC(14,2),
    parts_cost NUMERIC(14,2), external_cost NUMERIC(14,2), total_cost NUMERIC(14,2),
    status TEXT, notes TEXT
);""",
    "service_jobs": """
CREATE TABLE {s}service_jobs (
    id INT PRIMARY KEY, job_no TEXT, machine_unit_id INT REFERENCES {s}machine_units(id),
    customer_id INT REFERENCES {s}customers(id), job_type TEXT, request_date DATE,
    scheduled_date DATE, completion_date DATE, technician_id INT REFERENCES {s}employees(id),
    country TEXT, labor_hours NUMERIC(10,2), labor_cost NUMERIC(14,2),
    parts_cost NUMERIC(14,2), travel_cost NUMERIC(14,2), total_cost NUMERIC(14,2),
    billable_amount NUMERIC(14,2), currency TEXT, fx_rate NUMERIC(18,8),
    billable_base NUMERIC(14,2), is_warranty BOOLEAN, status TEXT, sla_days INT,
    response_days INT, satisfaction_score NUMERIC(4,2)
);""",
    "warranty_contracts": """
CREATE TABLE {s}warranty_contracts (
    id INT PRIMARY KEY, contract_no TEXT, machine_unit_id INT REFERENCES {s}machine_units(id),
    customer_id INT REFERENCES {s}customers(id), invoice_id INT, start_date DATE,
    end_date DATE, months INT, coverage_type TEXT, price NUMERIC(14,2), currency TEXT,
    price_base NUMERIC(14,2), status TEXT, claims_count INT, claims_cost NUMERIC(14,2)
);""",
}

INDEXES = {
    "fx_rates": ["rate_date", "currency_code"],
    "expenses": ["expense_date", "category_id", "department_id"],
    "payroll_items": ["employee_id", "period_date"],
    "machine_units": ["status", "sale_date", "product_id"],
    "shipments": ["ship_date", "dest_country", "customer_id"],
    "opportunities": ["created_date", "stage", "customer_id"],
    "service_jobs": ["completion_date", "machine_unit_id"],
    "depreciation_entries": ["period_date", "asset_id"],
    "vendor_invoices": ["bill_date", "vendor_id", "status"],
    "quotations": ["quote_date", "customer_id"],
}

# Columns appended to tables that already exist in ddl.py. Keeps multi-currency,
# serialized-unit and geography attributes on the core documents without
# duplicating their definitions.
EXTRA_COLUMNS = {
    "customers": [
        ("country_code", "TEXT"), ("postcode", "TEXT"), ("currency", "TEXT"),
        ("payment_terms_days", "INT"), ("incoterm", "TEXT"), ("tax_regime", "TEXT"),
        ("vat_number", "TEXT"), ("industry", "TEXT"), ("account_manager_id", "INT"),
        ("is_export", "BOOLEAN"), ("is_intra_eu", "BOOLEAN"), ("contact_name", "TEXT"),
        ("first_order_date", "DATE"), ("status", "TEXT"),
    ],
    "vendors": [
        ("country_code", "TEXT"), ("postcode", "TEXT"), ("currency", "TEXT"),
        ("vendor_type", "TEXT"), ("payment_terms_days", "INT"), ("vat_number", "TEXT"),
        ("rating", "NUMERIC(4,2)"), ("contact_name", "TEXT"), ("status", "TEXT"),
    ],
    "employees": [
        ("employee_no", "TEXT"), ("country", "TEXT"), ("country_code", "TEXT"),
        ("city", "TEXT"), ("work_location", "TEXT"), ("warehouse_id", "INT"),
        ("employment_type", "TEXT"), ("manager_id", "INT"), ("currency", "TEXT"),
        ("annual_gross", "NUMERIC(14,2)"), ("employer_cost_rate", "NUMERIC(6,4)"),
        ("weekly_hours", "NUMERIC(5,2)"), ("termination_date", "DATE"),
        ("gender", "TEXT"), ("birth_year", "INT"),
    ],
    "warehouses": [
        ("country_code", "TEXT"), ("address", "TEXT"), ("postcode", "TEXT"),
        ("manager_id", "INT"), ("is_active", "BOOLEAN"), ("opened_date", "DATE"),
        ("monthly_rent", "NUMERIC(14,2)"),
    ],
    "products": [
        ("item_type", "TEXT"), ("subcategory", "TEXT"), ("brand", "TEXT"),
        ("condition", "TEXT"), ("weight_kg", "NUMERIC(12,2)"), ("hs_code", "TEXT"),
        ("origin_country", "TEXT"), ("lead_time_days", "INT"),
        ("is_stocked", "BOOLEAN"), ("reorder_point", "NUMERIC(12,2)"),
        ("target_margin_pct", "NUMERIC(6,3)"),
    ],
    "sales_orders": [
        ("quote_id", "INT"), ("opportunity_id", "INT"), ("order_type", "TEXT"),
        ("fx_rate", "NUMERIC(18,8)"), ("subtotal_base", "NUMERIC(16,2)"),
        ("discount_base", "NUMERIC(16,2)"), ("tax_base", "NUMERIC(16,2)"),
        ("total_base", "NUMERIC(16,2)"), ("cogs_base", "NUMERIC(16,2)"),
        ("margin_base", "NUMERIC(16,2)"), ("incoterm", "TEXT"),
        ("dest_country", "TEXT"), ("is_export", "BOOLEAN"), ("is_intra_eu", "BOOLEAN"),
        ("tax_code", "TEXT"), ("payment_terms_days", "INT"), ("delivery_date", "DATE"),
    ],
    "sales_order_lines": [
        ("machine_unit_id", "INT"), ("line_type", "TEXT"), ("description", "TEXT"),
        ("fx_rate", "NUMERIC(18,8)"), ("line_subtotal_base", "NUMERIC(16,2)"),
        ("line_total_base", "NUMERIC(16,2)"), ("line_cogs_base", "NUMERIC(16,2)"),
        ("line_margin_base", "NUMERIC(16,2)"),
    ],
    "invoices": [
        ("fx_rate", "NUMERIC(18,8)"), ("subtotal_base", "NUMERIC(16,2)"),
        ("tax_base", "NUMERIC(16,2)"), ("total_base", "NUMERIC(16,2)"),
        ("amount_paid_base", "NUMERIC(16,2)"), ("balance_base", "NUMERIC(16,2)"),
        ("tax_code", "TEXT"), ("payment_terms_days", "INT"), ("dest_country", "TEXT"),
        ("days_overdue", "INT"),
    ],
    "invoice_lines": [
        ("machine_unit_id", "INT"), ("line_type", "TEXT"), ("description", "TEXT"),
        ("line_total_base", "NUMERIC(16,2)"),
    ],
    "payments": [
        ("currency", "TEXT"), ("fx_rate", "NUMERIC(18,8)"),
        ("amount_base", "NUMERIC(16,2)"), ("fx_gain_loss", "NUMERIC(14,2)"),
        ("days_to_pay", "INT"), ("bank_account", "TEXT"),
    ],
    "returns": [
        ("machine_unit_id", "INT"), ("currency", "TEXT"),
        ("refund_amount_base", "NUMERIC(16,2)"), ("restocking_fee", "NUMERIC(14,2)"),
        ("status", "TEXT"),
    ],
    "purchase_orders": [
        ("po_type", "TEXT"), ("fx_rate", "NUMERIC(18,8)"),
        ("subtotal_base", "NUMERIC(16,2)"), ("tax_base", "NUMERIC(16,2)"),
        ("total_base", "NUMERIC(16,2)"), ("buyer_id", "INT"), ("incoterm", "TEXT"),
        ("expected_date", "DATE"), ("received_date", "DATE"),
        ("origin_country", "TEXT"),
    ],
    "purchase_order_lines": [
        ("machine_unit_id", "INT"), ("description", "TEXT"),
        ("line_total_base", "NUMERIC(16,2)"),
    ],
    "stock_moves": [
        ("machine_unit_id", "INT"), ("value_base", "NUMERIC(16,2)"), ("lot_ref", "TEXT"),
    ],
    "bank_transactions": [
        ("currency", "TEXT"), ("fx_rate", "NUMERIC(18,8)"),
        ("amount_base", "NUMERIC(16,2)"), ("category", "TEXT"), ("description", "TEXT"),
    ],
    "gl_entries": [
        ("entry_no", "TEXT"), ("journal", "TEXT"), ("line_no", "INT"),
        ("department_id", "INT"), ("currency", "TEXT"), ("fx_rate", "NUMERIC(18,8)"),
        ("debit_base", "NUMERIC(16,2)"), ("credit_base", "NUMERIC(16,2)"),
        ("period_year", "INT"), ("period_month", "INT"), ("memo", "TEXT"),
    ],
}


# Unit prices are stored in the document's own currency. A machine priced in
# forint or lira needs far more integer digits than the single-currency default
# NUMERIC(12,4) allows, so these columns are widened. Harmless for
# single-currency industries.
WIDEN = {
    "sales_order_lines": {"unit_price": "NUMERIC(20,4)", "unit_cost": "NUMERIC(20,4)"},
    "invoice_lines": {"unit_price": "NUMERIC(20,4)"},
    "purchase_order_lines": {"unit_cost": "NUMERIC(20,4)"},
    "quotation_lines": {"unit_price": "NUMERIC(20,4)"},
    "stock_moves": {"unit_cost": "NUMERIC(20,4)"},
}


def _widen(ddl_sql: str, cols: dict) -> str:
    import re
    for col, newtype in cols.items():
        ddl_sql = re.sub(rf"(\b{col}\s+)NUMERIC\(\d+,\d+\)", rf"\g<1>{newtype}", ddl_sql)
    return ddl_sql


def _append_columns(ddl_sql: str, defs: list) -> str:
    """Splice extra column definitions into an existing CREATE TABLE string."""
    head, _, _tail = ddl_sql.rstrip().rpartition(");")
    head = head.rstrip().rstrip(",")
    extra = ",\n    ".join(f"{c} {t}" for c, t in defs)
    return f"{head},\n    {extra}\n);"


def install(table_order: list, columns: dict, ddl_map: dict, indexes: dict) -> None:
    """Merge the extended module definitions into ddl.py's registries."""
    # 1. extra columns on existing tables
    for table, defs in EXTRA_COLUMNS.items():
        if table not in columns:
            continue
        new = [c for c, _ in defs if c not in columns[table]]
        if not new:
            continue
        columns[table] = columns[table] + new
        ddl_map[table] = _append_columns(ddl_map[table], [d for d in defs if d[0] in new])

    # 2. new tables
    columns.update(COLUMNS)
    ddl_map.update(DDL)
    for table, cols in WIDEN.items():
        if table in ddl_map:
            ddl_map[table] = _widen(ddl_map[table], cols)
    for t, cols in INDEXES.items():
        indexes.setdefault(t, []).extend(c for c in cols if c not in indexes.get(t, []))

    # 3. splice into the canonical order
    for table, after in ORDER_AFTER:
        if table in table_order:
            continue
        if after is None:
            table_order.insert(0, table)
        elif after in table_order:
            table_order.insert(table_order.index(after) + 1, table)
        else:
            table_order.append(table)
