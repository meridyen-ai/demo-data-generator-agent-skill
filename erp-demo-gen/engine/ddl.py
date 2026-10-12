"""DDL for every possible table, plus the canonical create/load order.

Each generated database includes only the subset of tables selected for its
industry (see catalog.select_tables), but DDL is defined once here so column
contracts stay in one place. Generators in generators.py MUST emit columns in
the same order as COLUMNS below (used for the CSV header and COPY).
"""
from __future__ import annotations

# Canonical dependency order: parents before children. Loading/creation follows
# this order; selection filters it.
TABLE_ORDER = [
    "departments",
    "employees",
    "customers",
    "vendors",
    "warehouses",
    "work_centers",
    "products",
    "raw_materials",
    "price_list",
    "promotions",
    "bom",
    "bom_lines",
    "sales_orders",
    "sales_order_lines",
    "invoices",
    "invoice_lines",
    "payments",
    "returns",
    "purchase_orders",
    "purchase_order_lines",
    "production_orders",
    "production_consumption",
    "lots",
    "stock_moves",
    "bank_transactions",
    "gl_entries",
    "iot_readings",
]

# Column order per table — the single source of truth shared by DDL, the CSV
# writer, and the generators.
COLUMNS = {
    "departments": ["id", "name", "cost_center"],
    "employees": ["id", "first_name", "last_name", "full_name", "email", "department_id",
                  "role", "hire_date", "salary", "is_active"],
    "customers": ["id", "name", "segment", "address", "city", "state", "country",
                  "email", "phone", "credit_limit", "created_at"],
    "vendors": ["id", "name", "category", "address", "city", "state", "country",
                "email", "phone", "lead_time_days", "created_at"],
    "warehouses": ["id", "code", "name", "type", "city", "state", "country", "capacity_sqft"],
    "work_centers": ["id", "code", "name", "capacity_per_hour", "cost_per_hour", "is_active"],
    "products": ["id", "sku", "name", "category", "uom", "unit_cost", "list_price",
                 "is_active", "created_at"],
    "raw_materials": ["id", "code", "name", "category", "uom", "unit_cost", "vendor_id"],
    "price_list": ["id", "product_id", "valid_from", "valid_to", "price"],
    "promotions": ["id", "code", "name", "category", "discount_pct", "start_date", "end_date"],
    "bom": ["id", "product_id", "name", "version", "output_qty", "is_active"],
    "bom_lines": ["id", "bom_id", "raw_material_id", "qty_per", "scrap_pct"],
    "sales_orders": ["id", "order_no", "customer_id", "salesperson_id", "warehouse_id",
                     "channel", "order_date", "status", "currency", "subtotal",
                     "discount", "tax", "total", "cogs", "margin"],
    "sales_order_lines": ["id", "order_id", "line_no", "product_id", "qty", "unit_price",
                          "discount_pct", "line_subtotal", "tax", "line_total",
                          "unit_cost", "line_cogs", "line_margin"],
    "invoices": ["id", "invoice_no", "order_id", "customer_id", "invoice_date", "due_date",
                 "status", "currency", "subtotal", "tax", "total", "amount_paid", "balance"],
    "invoice_lines": ["id", "invoice_id", "line_no", "product_id", "qty", "unit_price", "line_total"],
    "payments": ["id", "payment_no", "invoice_id", "customer_id", "payment_date", "method", "amount"],
    "returns": ["id", "return_no", "order_id", "order_line_id", "product_id", "customer_id",
                "return_date", "qty", "reason", "refund_amount"],
    "purchase_orders": ["id", "po_no", "vendor_id", "warehouse_id", "order_date", "status",
                        "currency", "subtotal", "tax", "total"],
    "purchase_order_lines": ["id", "po_id", "line_no", "item_type", "item_id", "qty",
                             "unit_cost", "line_total", "received_qty"],
    "production_orders": ["id", "mo_no", "product_id", "bom_id", "work_center_id",
                          "planned_qty", "produced_qty", "scrap_qty", "start_date",
                          "end_date", "status", "unit_cost"],
    "production_consumption": ["id", "production_order_id", "raw_material_id",
                               "planned_qty", "consumed_qty", "unit_cost"],
    "lots": ["id", "lot_no", "product_id", "production_order_id", "production_date",
             "expiry_date", "qty"],
    "stock_moves": ["id", "move_date", "item_type", "item_id", "warehouse_id", "move_type",
                    "qty", "unit_cost", "reference_type", "reference_id"],
    "bank_transactions": ["id", "txn_date", "account", "direction", "counterparty",
                          "reference_type", "reference_id", "amount", "balance_after"],
    "gl_entries": ["id", "entry_date", "account_code", "account_name", "debit", "credit",
                   "reference_type", "reference_id"],
    "iot_readings": ["id", "source_type", "source_id", "reading_ts", "metric", "value", "unit"],
}

# CREATE TABLE statements. {s} is replaced with the schema-qualified name prefix.
DDL = {
    "departments": """
CREATE TABLE {s}departments (
    id INT PRIMARY KEY, name TEXT NOT NULL, cost_center TEXT
);""",
    "employees": """
CREATE TABLE {s}employees (
    id INT PRIMARY KEY, first_name TEXT, last_name TEXT, full_name TEXT, email TEXT,
    department_id INT REFERENCES {s}departments(id), role TEXT, hire_date DATE,
    salary NUMERIC(12,2), is_active BOOLEAN
);""",
    "customers": """
CREATE TABLE {s}customers (
    id INT PRIMARY KEY, name TEXT NOT NULL, segment TEXT, address TEXT, city TEXT,
    state TEXT, country TEXT, email TEXT, phone TEXT, credit_limit NUMERIC(12,2),
    created_at DATE
);""",
    "vendors": """
CREATE TABLE {s}vendors (
    id INT PRIMARY KEY, name TEXT NOT NULL, category TEXT, address TEXT, city TEXT,
    state TEXT, country TEXT, email TEXT, phone TEXT, lead_time_days INT, created_at DATE
);""",
    "warehouses": """
CREATE TABLE {s}warehouses (
    id INT PRIMARY KEY, code TEXT, name TEXT, type TEXT, city TEXT, state TEXT,
    country TEXT, capacity_sqft INT
);""",
    "work_centers": """
CREATE TABLE {s}work_centers (
    id INT PRIMARY KEY, code TEXT, name TEXT, capacity_per_hour NUMERIC(10,2),
    cost_per_hour NUMERIC(10,2), is_active BOOLEAN
);""",
    "products": """
CREATE TABLE {s}products (
    id INT PRIMARY KEY, sku TEXT, name TEXT, category TEXT, uom TEXT,
    unit_cost NUMERIC(12,4), list_price NUMERIC(12,4), is_active BOOLEAN, created_at DATE
);""",
    "raw_materials": """
CREATE TABLE {s}raw_materials (
    id INT PRIMARY KEY, code TEXT, name TEXT, category TEXT, uom TEXT,
    unit_cost NUMERIC(12,4), vendor_id INT REFERENCES {s}vendors(id)
);""",
    "price_list": """
CREATE TABLE {s}price_list (
    id INT PRIMARY KEY, product_id INT REFERENCES {s}products(id),
    valid_from DATE, valid_to DATE, price NUMERIC(12,4)
);""",
    "promotions": """
CREATE TABLE {s}promotions (
    id INT PRIMARY KEY, code TEXT, name TEXT, category TEXT, discount_pct NUMERIC(5,2),
    start_date DATE, end_date DATE
);""",
    "bom": """
CREATE TABLE {s}bom (
    id INT PRIMARY KEY, product_id INT REFERENCES {s}products(id), name TEXT,
    version TEXT, output_qty NUMERIC(12,2), is_active BOOLEAN
);""",
    "bom_lines": """
CREATE TABLE {s}bom_lines (
    id INT PRIMARY KEY, bom_id INT REFERENCES {s}bom(id),
    raw_material_id INT REFERENCES {s}raw_materials(id),
    qty_per NUMERIC(12,4), scrap_pct NUMERIC(5,2)
);""",
    "sales_orders": """
CREATE TABLE {s}sales_orders (
    id INT PRIMARY KEY, order_no TEXT, customer_id INT REFERENCES {s}customers(id),
    salesperson_id INT, warehouse_id INT, channel TEXT, order_date DATE, status TEXT,
    currency TEXT, subtotal NUMERIC(14,2), discount NUMERIC(14,2), tax NUMERIC(14,2),
    total NUMERIC(14,2), cogs NUMERIC(14,2), margin NUMERIC(14,2)
);""",
    "sales_order_lines": """
CREATE TABLE {s}sales_order_lines (
    id BIGINT PRIMARY KEY, order_id INT REFERENCES {s}sales_orders(id), line_no INT,
    product_id INT REFERENCES {s}products(id), qty NUMERIC(12,2), unit_price NUMERIC(12,4),
    discount_pct NUMERIC(5,2), line_subtotal NUMERIC(14,2), tax NUMERIC(14,2),
    line_total NUMERIC(14,2), unit_cost NUMERIC(12,4), line_cogs NUMERIC(14,2),
    line_margin NUMERIC(14,2)
);""",
    "invoices": """
CREATE TABLE {s}invoices (
    id INT PRIMARY KEY, invoice_no TEXT, order_id INT REFERENCES {s}sales_orders(id),
    customer_id INT REFERENCES {s}customers(id), invoice_date DATE, due_date DATE,
    status TEXT, currency TEXT, subtotal NUMERIC(14,2), tax NUMERIC(14,2),
    total NUMERIC(14,2), amount_paid NUMERIC(14,2), balance NUMERIC(14,2)
);""",
    "invoice_lines": """
CREATE TABLE {s}invoice_lines (
    id BIGINT PRIMARY KEY, invoice_id INT REFERENCES {s}invoices(id), line_no INT,
    product_id INT REFERENCES {s}products(id), qty NUMERIC(12,2), unit_price NUMERIC(12,4),
    line_total NUMERIC(14,2)
);""",
    "payments": """
CREATE TABLE {s}payments (
    id INT PRIMARY KEY, payment_no TEXT, invoice_id INT REFERENCES {s}invoices(id),
    customer_id INT REFERENCES {s}customers(id), payment_date DATE, method TEXT,
    amount NUMERIC(14,2)
);""",
    "returns": """
CREATE TABLE {s}returns (
    id INT PRIMARY KEY, return_no TEXT, order_id INT REFERENCES {s}sales_orders(id),
    order_line_id BIGINT, product_id INT REFERENCES {s}products(id),
    customer_id INT REFERENCES {s}customers(id), return_date DATE, qty NUMERIC(12,2),
    reason TEXT, refund_amount NUMERIC(14,2)
);""",
    "purchase_orders": """
CREATE TABLE {s}purchase_orders (
    id INT PRIMARY KEY, po_no TEXT, vendor_id INT REFERENCES {s}vendors(id),
    warehouse_id INT, order_date DATE, status TEXT, currency TEXT,
    subtotal NUMERIC(14,2), tax NUMERIC(14,2), total NUMERIC(14,2)
);""",
    "purchase_order_lines": """
CREATE TABLE {s}purchase_order_lines (
    id BIGINT PRIMARY KEY, po_id INT REFERENCES {s}purchase_orders(id), line_no INT,
    item_type TEXT, item_id INT, qty NUMERIC(12,2), unit_cost NUMERIC(12,4),
    line_total NUMERIC(14,2), received_qty NUMERIC(12,2)
);""",
    "production_orders": """
CREATE TABLE {s}production_orders (
    id INT PRIMARY KEY, mo_no TEXT, product_id INT REFERENCES {s}products(id),
    bom_id INT, work_center_id INT, planned_qty NUMERIC(12,2), produced_qty NUMERIC(12,2),
    scrap_qty NUMERIC(12,2), start_date DATE, end_date DATE, status TEXT, unit_cost NUMERIC(12,4)
);""",
    "production_consumption": """
CREATE TABLE {s}production_consumption (
    id BIGINT PRIMARY KEY, production_order_id INT REFERENCES {s}production_orders(id),
    raw_material_id INT REFERENCES {s}raw_materials(id), planned_qty NUMERIC(12,4),
    consumed_qty NUMERIC(12,4), unit_cost NUMERIC(12,4)
);""",
    "lots": """
CREATE TABLE {s}lots (
    id INT PRIMARY KEY, lot_no TEXT, product_id INT REFERENCES {s}products(id),
    production_order_id INT, production_date DATE, expiry_date DATE, qty NUMERIC(12,2)
);""",
    "stock_moves": """
CREATE TABLE {s}stock_moves (
    id BIGINT PRIMARY KEY, move_date DATE, item_type TEXT, item_id INT, warehouse_id INT,
    move_type TEXT, qty NUMERIC(12,2), unit_cost NUMERIC(12,4), reference_type TEXT,
    reference_id INT
);""",
    "bank_transactions": """
CREATE TABLE {s}bank_transactions (
    id INT PRIMARY KEY, txn_date DATE, account TEXT, direction TEXT, counterparty TEXT,
    reference_type TEXT, reference_id INT, amount NUMERIC(14,2), balance_after NUMERIC(16,2)
);""",
    "gl_entries": """
CREATE TABLE {s}gl_entries (
    id BIGINT PRIMARY KEY, entry_date DATE, account_code TEXT, account_name TEXT,
    debit NUMERIC(14,2), credit NUMERIC(14,2), reference_type TEXT, reference_id INT
);""",
    "iot_readings": """
CREATE TABLE {s}iot_readings (
    id BIGINT PRIMARY KEY, source_type TEXT, source_id INT, reading_ts TIMESTAMP,
    metric TEXT, value NUMERIC(14,4), unit TEXT
);""",
}

# Helpful indexes on the high-traffic fact tables.
INDEXES = {
    "sales_orders": ["order_date", "customer_id"],
    "sales_order_lines": ["order_id", "product_id"],
    "invoices": ["invoice_date", "customer_id", "status"],
    "payments": ["invoice_id", "payment_date"],
    "stock_moves": ["move_date", "item_id"],
    "iot_readings": ["source_id", "reading_ts"],
    "purchase_orders": ["order_date", "vendor_id"],
}


# --- extended ERP modules (finance, HR, CRM, logistics, assets, service) -----
# Merged in at import time so every registry above stays the single source of
# truth. Tables only materialise for industries whose tables.json includes them.
from . import ddl_ext  # noqa: E402

ddl_ext.install(TABLE_ORDER, COLUMNS, DDL, INDEXES)
