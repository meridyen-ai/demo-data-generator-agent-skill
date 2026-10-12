"""Talaşlı imalat / fason metal parça üretimi için ek ERP tabloları.

ddl.py çekirdek satış-satınalma-stok modelini, ddl_ext.py finans/İK/CRM/lojistik
modüllerini taşır. Bu modül bir seri üretim talaşlı imalat fabrikasının
gerçekten ihtiyaç duyduğu üretim derinliğini ekler:

* ``machines``           — atölyedeki her tezgah (CNC torna, işleme merkezi, taşlama)
* ``routings``           — parça başına operasyon rotası (standart süreler, fason adımlar)
* ``production_operations`` — iş emri operasyon kayıtları (fiili süre, duruş, hurda)
* ``quality_inspections``  — girdi/proses/final kalite kontrol ölçümleri
* ``nonconformances``      — uygunsuzluk (NCR/8D), müşteri şikayetleri, PPM
* ``subcontract_operations`` — fason işlemler (ısıl işlem, kaplama, taşlama)
* ``maintenance_orders``   — planlı bakım ve arıza müdahaleleri
* ``part_approvals``       — numune / PPAP onay süreçleri
* ``hse_incidents``        — İSG olay kayıtları

Ayrıca çok para birimli analiz için (TRY taban, EUR ve USD karşılıkları) mevcut
belge tablolarına ``*_eur`` / ``*_usd`` kolonları ekler; böylece raporlama para
birimi seçimi bir JOIN gerektirmez.
"""
from __future__ import annotations

ORDER_AFTER = [
    ("machines", "work_centers"),
    ("routings", "bom_lines"),
    ("part_approvals", "routings"),
    ("production_operations", "production_consumption"),
    ("subcontract_operations", "production_operations"),
    ("quality_inspections", "subcontract_operations"),
    ("nonconformances", "quality_inspections"),
    ("maintenance_orders", "nonconformances"),
    ("hse_incidents", "maintenance_orders"),
]

COLUMNS = {
    "machines": [
        "id", "code", "name", "machine_type", "work_center_id", "department_id",
        "manufacturer", "model", "control_system", "axis_count", "year_installed",
        "commissioned_date", "fixed_asset_id", "warehouse_id", "power_kw",
        "max_bar_dia_mm", "max_part_dia_mm", "spindle_count", "tool_capacity",
        "has_bar_feeder", "has_robot_loading", "hourly_rate", "capacity_per_hour",
        "target_oee_pct", "status", "serial_no", "notes"],

    "routings": [
        "id", "product_id", "version", "operation_no", "operation_name", "operation_type",
        "work_center_id", "machine_id", "setup_minutes", "cycle_time_sec",
        "pieces_per_hour", "std_labor_rate", "std_machine_rate", "tooling_cost_per_part",
        "is_subcontract", "subcontract_vendor_id", "subcontract_unit_price",
        "subcontract_currency", "scrap_pct", "is_active", "notes"],

    "part_approvals": [
        "id", "approval_no", "product_id", "customer_id", "program_name",
        "submission_level", "sample_qty", "request_date", "submission_date",
        "approval_date", "status", "engineer_id", "drawing_revision", "reject_reason",
        "days_to_approve", "notes"],

    "production_operations": [
        "id", "production_order_id", "routing_id", "operation_no", "operation_name",
        "operation_type", "work_center_id", "machine_id", "operator_id", "shift",
        "op_date", "start_ts", "end_ts", "setup_minutes_std", "setup_minutes_actual",
        "run_minutes_std", "run_minutes_actual", "downtime_minutes", "downtime_reason",
        "input_qty", "good_qty", "scrap_qty", "rework_qty", "labor_cost", "machine_cost",
        "tooling_cost", "total_cost", "efficiency_pct", "status", "notes"],

    "subcontract_operations": [
        "id", "sub_no", "production_order_id", "operation_id", "vendor_id",
        "purchase_order_id", "process_type", "sent_date", "expected_date",
        "received_date", "qty_sent", "qty_received", "qty_scrapped", "unit_price",
        "currency", "fx_rate", "total_cost", "total_cost_base", "lead_days",
        "planned_lead_days", "is_on_time", "status", "notes"],

    "quality_inspections": [
        "id", "inspection_no", "inspection_type", "inspection_date", "production_order_id",
        "operation_id", "product_id", "raw_material_id", "purchase_order_id", "vendor_id",
        "customer_id", "inspector_id", "work_center_id", "lot_no", "sample_size",
        "inspected_qty", "defect_qty", "defect_ppm", "result", "characteristic",
        "measurement_method", "nominal_value", "tolerance_lower", "tolerance_upper",
        "measured_value", "cpk", "notes"],

    "nonconformances": [
        "id", "ncr_no", "source", "ncr_date", "product_id", "production_order_id",
        "operation_id", "customer_id", "vendor_id", "work_center_id", "machine_id",
        "detected_by_id", "qty_affected", "defect_code", "defect_description",
        "root_cause", "root_cause_category", "disposition", "rework_cost", "scrap_cost",
        "other_cost", "total_cost", "is_customer_complaint", "complaint_ref", "ppm",
        "severity", "capa_status", "capa_owner_id", "opened_date", "closed_date",
        "days_to_close", "is_8d", "notes"],

    "maintenance_orders": [
        "id", "mo_no", "machine_id", "work_center_id", "maintenance_type",
        "request_date", "start_date", "end_date", "technician_id", "downtime_hours",
        "labor_hours", "labor_cost", "parts_cost", "external_cost", "total_cost",
        "failure_mode", "root_cause", "is_planned", "status", "notes"],

    "hse_incidents": [
        "id", "incident_no", "incident_date", "department_id", "work_center_id",
        "employee_id", "incident_type", "severity", "lost_days", "body_part",
        "description", "root_cause", "corrective_action", "reported_by_id",
        "is_lost_time", "status"],
}

DDL = {
    "machines": """
CREATE TABLE {s}machines (
    id INT PRIMARY KEY, code TEXT, name TEXT, machine_type TEXT,
    work_center_id INT REFERENCES {s}work_centers(id),
    department_id INT REFERENCES {s}departments(id),
    manufacturer TEXT, model TEXT, control_system TEXT, axis_count INT,
    year_installed INT, commissioned_date DATE, fixed_asset_id INT, warehouse_id INT,
    power_kw NUMERIC(10,2), max_bar_dia_mm NUMERIC(8,2), max_part_dia_mm NUMERIC(8,2),
    spindle_count INT, tool_capacity INT, has_bar_feeder BOOLEAN,
    has_robot_loading BOOLEAN, hourly_rate NUMERIC(12,2),
    capacity_per_hour NUMERIC(10,2), target_oee_pct NUMERIC(5,2), status TEXT,
    serial_no TEXT, notes TEXT
);""",
    "routings": """
CREATE TABLE {s}routings (
    id INT PRIMARY KEY, product_id INT REFERENCES {s}products(id), version TEXT,
    operation_no INT, operation_name TEXT, operation_type TEXT,
    work_center_id INT REFERENCES {s}work_centers(id),
    machine_id INT REFERENCES {s}machines(id),
    setup_minutes NUMERIC(10,2), cycle_time_sec NUMERIC(10,3),
    pieces_per_hour NUMERIC(10,2), std_labor_rate NUMERIC(12,2),
    std_machine_rate NUMERIC(12,2), tooling_cost_per_part NUMERIC(12,4),
    is_subcontract BOOLEAN, subcontract_vendor_id INT REFERENCES {s}vendors(id),
    subcontract_unit_price NUMERIC(14,4), subcontract_currency TEXT,
    scrap_pct NUMERIC(6,3), is_active BOOLEAN, notes TEXT
);""",
    "part_approvals": """
CREATE TABLE {s}part_approvals (
    id INT PRIMARY KEY, approval_no TEXT, product_id INT REFERENCES {s}products(id),
    customer_id INT REFERENCES {s}customers(id), program_name TEXT,
    submission_level TEXT, sample_qty NUMERIC(12,2), request_date DATE,
    submission_date DATE, approval_date DATE, status TEXT,
    engineer_id INT REFERENCES {s}employees(id), drawing_revision TEXT,
    reject_reason TEXT, days_to_approve INT, notes TEXT
);""",
    "production_operations": """
CREATE TABLE {s}production_operations (
    id BIGINT PRIMARY KEY,
    production_order_id INT REFERENCES {s}production_orders(id),
    routing_id INT REFERENCES {s}routings(id), operation_no INT, operation_name TEXT,
    operation_type TEXT, work_center_id INT REFERENCES {s}work_centers(id),
    machine_id INT REFERENCES {s}machines(id),
    operator_id INT REFERENCES {s}employees(id), shift TEXT, op_date DATE,
    start_ts TIMESTAMP, end_ts TIMESTAMP, setup_minutes_std NUMERIC(10,2),
    setup_minutes_actual NUMERIC(10,2), run_minutes_std NUMERIC(12,2),
    run_minutes_actual NUMERIC(12,2), downtime_minutes NUMERIC(10,2),
    downtime_reason TEXT, input_qty NUMERIC(12,2), good_qty NUMERIC(12,2),
    scrap_qty NUMERIC(12,2), rework_qty NUMERIC(12,2), labor_cost NUMERIC(14,2),
    machine_cost NUMERIC(14,2), tooling_cost NUMERIC(14,2), total_cost NUMERIC(14,2),
    efficiency_pct NUMERIC(7,2), status TEXT, notes TEXT
);""",
    "subcontract_operations": """
CREATE TABLE {s}subcontract_operations (
    id INT PRIMARY KEY, sub_no TEXT,
    production_order_id INT REFERENCES {s}production_orders(id),
    operation_id BIGINT, vendor_id INT REFERENCES {s}vendors(id),
    purchase_order_id INT REFERENCES {s}purchase_orders(id), process_type TEXT,
    sent_date DATE, expected_date DATE, received_date DATE, qty_sent NUMERIC(12,2),
    qty_received NUMERIC(12,2), qty_scrapped NUMERIC(12,2), unit_price NUMERIC(14,4),
    currency TEXT, fx_rate NUMERIC(18,8), total_cost NUMERIC(16,2),
    total_cost_base NUMERIC(16,2), lead_days INT, planned_lead_days INT,
    is_on_time BOOLEAN, status TEXT, notes TEXT
);""",
    "quality_inspections": """
CREATE TABLE {s}quality_inspections (
    id BIGINT PRIMARY KEY, inspection_no TEXT, inspection_type TEXT,
    inspection_date DATE, production_order_id INT REFERENCES {s}production_orders(id),
    operation_id BIGINT, product_id INT REFERENCES {s}products(id),
    raw_material_id INT REFERENCES {s}raw_materials(id),
    purchase_order_id INT REFERENCES {s}purchase_orders(id),
    vendor_id INT REFERENCES {s}vendors(id), customer_id INT REFERENCES {s}customers(id),
    inspector_id INT REFERENCES {s}employees(id),
    work_center_id INT REFERENCES {s}work_centers(id), lot_no TEXT,
    sample_size NUMERIC(12,2), inspected_qty NUMERIC(12,2), defect_qty NUMERIC(12,2),
    defect_ppm NUMERIC(12,2), result TEXT, characteristic TEXT,
    measurement_method TEXT, nominal_value NUMERIC(14,4),
    tolerance_lower NUMERIC(14,4), tolerance_upper NUMERIC(14,4),
    measured_value NUMERIC(14,4), cpk NUMERIC(8,3), notes TEXT
);""",
    "nonconformances": """
CREATE TABLE {s}nonconformances (
    id INT PRIMARY KEY, ncr_no TEXT, source TEXT, ncr_date DATE,
    product_id INT REFERENCES {s}products(id),
    production_order_id INT REFERENCES {s}production_orders(id), operation_id BIGINT,
    customer_id INT REFERENCES {s}customers(id), vendor_id INT REFERENCES {s}vendors(id),
    work_center_id INT REFERENCES {s}work_centers(id),
    machine_id INT REFERENCES {s}machines(id),
    detected_by_id INT REFERENCES {s}employees(id), qty_affected NUMERIC(12,2),
    defect_code TEXT, defect_description TEXT, root_cause TEXT,
    root_cause_category TEXT, disposition TEXT, rework_cost NUMERIC(14,2),
    scrap_cost NUMERIC(14,2), other_cost NUMERIC(14,2), total_cost NUMERIC(14,2),
    is_customer_complaint BOOLEAN, complaint_ref TEXT, ppm NUMERIC(12,2),
    severity TEXT, capa_status TEXT, capa_owner_id INT REFERENCES {s}employees(id),
    opened_date DATE, closed_date DATE, days_to_close INT, is_8d BOOLEAN, notes TEXT
);""",
    "maintenance_orders": """
CREATE TABLE {s}maintenance_orders (
    id INT PRIMARY KEY, mo_no TEXT, machine_id INT REFERENCES {s}machines(id),
    work_center_id INT REFERENCES {s}work_centers(id), maintenance_type TEXT,
    request_date DATE, start_date DATE, end_date DATE,
    technician_id INT REFERENCES {s}employees(id), downtime_hours NUMERIC(10,2),
    labor_hours NUMERIC(10,2), labor_cost NUMERIC(14,2), parts_cost NUMERIC(14,2),
    external_cost NUMERIC(14,2), total_cost NUMERIC(14,2), failure_mode TEXT,
    root_cause TEXT, is_planned BOOLEAN, status TEXT, notes TEXT
);""",
    "hse_incidents": """
CREATE TABLE {s}hse_incidents (
    id INT PRIMARY KEY, incident_no TEXT, incident_date DATE,
    department_id INT REFERENCES {s}departments(id),
    work_center_id INT REFERENCES {s}work_centers(id),
    employee_id INT REFERENCES {s}employees(id), incident_type TEXT, severity TEXT,
    lost_days INT, body_part TEXT, description TEXT, root_cause TEXT,
    corrective_action TEXT, reported_by_id INT REFERENCES {s}employees(id),
    is_lost_time BOOLEAN, status TEXT
);""",
}

INDEXES = {
    "machines": ["work_center_id", "status"],
    "routings": ["product_id", "work_center_id"],
    "production_operations": ["production_order_id", "op_date", "machine_id", "work_center_id"],
    "quality_inspections": ["inspection_date", "product_id", "result"],
    "nonconformances": ["ncr_date", "product_id", "customer_id", "source"],
    "subcontract_operations": ["sent_date", "vendor_id"],
    "maintenance_orders": ["start_date", "machine_id", "maintenance_type"],
    "part_approvals": ["product_id", "customer_id", "status"],
    "hse_incidents": ["incident_date", "department_id"],
    "production_orders": ["start_date", "product_id", "status"],
    "production_consumption": ["production_order_id", "raw_material_id"],
    "lots": ["product_id", "production_date"],
    "expenses": ["source", "period_year"],
    "gl_entries": ["entry_date", "account_code", "period_year"],
}


# Mevcut tablolara eklenen kolonlar. İki amaca hizmet eder:
#  1) çok para birimli raporlama (TRY taban + EUR/USD karşılığı her belgede hazır),
#  2) talaşlı imalata özgü nitelikler (parça teknik bilgileri, iş emri detayı, İK).
EXTRA_COLUMNS = {
    "company": [
        ("plant_area_sqm", "NUMERIC(12,2)"), ("closed_area_sqm", "NUMERIC(12,2)"),
        ("osb_name", "TEXT"), ("iso_certificates", "TEXT"), ("shift_model", "TEXT"),
        ("export_country_count", "INT"),
    ],
    "warehouses": [
        ("capacity_sqm", "NUMERIC(12,2)"), ("storage_type", "TEXT"),
        ("is_bonded", "BOOLEAN"),
    ],
    "departments": [
        ("manager_id", "INT"), ("is_production", "BOOLEAN"),
        ("headcount_target", "INT"), ("description", "TEXT"),
    ],
    "employees": [
        ("phone", "TEXT"), ("shift", "TEXT"), ("job_family", "TEXT"),
        ("skill_level", "TEXT"), ("education", "TEXT"), ("marital_status", "TEXT"),
        ("children_count", "INT"), ("leave_entitlement_days", "INT"),
        ("overtime_eligible", "BOOLEAN"), ("cost_center", "TEXT"),
        ("work_center_id", "INT"), ("union_member", "BOOLEAN"),
        ("monthly_gross_try", "NUMERIC(14,2)"), ("seniority_years", "NUMERIC(6,2)"),
    ],
    "work_centers": [
        ("department_id", "INT"), ("machine_count", "INT"), ("shift_count", "INT"),
        ("area_sqm", "NUMERIC(10,2)"), ("cost_center", "TEXT"),
        ("target_oee_pct", "NUMERIC(5,2)"), ("process_family", "TEXT"),
        ("is_subcontract", "BOOLEAN"),
    ],
    "products": [
        ("drawing_no", "TEXT"), ("revision", "TEXT"), ("customer_id", "INT"),
        ("program_name", "TEXT"), ("material_grade", "TEXT"),
        ("net_weight_kg", "NUMERIC(12,4)"), ("gross_weight_kg", "NUMERIC(12,4)"),
        ("raw_weight_kg", "NUMERIC(12,4)"), ("surface_treatment", "TEXT"),
        ("tolerance_class", "TEXT"), ("is_safety_part", "BOOLEAN"),
        ("annual_volume", "NUMERIC(14,2)"), ("std_cost_material", "NUMERIC(14,4)"),
        ("std_cost_labor", "NUMERIC(14,4)"), ("std_cost_machine", "NUMERIC(14,4)"),
        ("std_cost_tooling", "NUMERIC(14,4)"), ("std_cost_subcontract", "NUMERIC(14,4)"),
        ("std_cost_overhead", "NUMERIC(14,4)"), ("std_cost_total", "NUMERIC(14,4)"),
        ("unit_cost_eur", "NUMERIC(14,4)"), ("list_price_eur", "NUMERIC(14,4)"),
        ("list_price_usd", "NUMERIC(14,4)"), ("pricing_currency", "TEXT"),
        ("cavity_count", "INT"), ("operation_count", "INT"),
    ],
    "raw_materials": [
        ("material_grade", "TEXT"), ("standard", "TEXT"), ("form", "TEXT"),
        ("diameter_mm", "NUMERIC(10,2)"), ("wall_thickness_mm", "NUMERIC(10,2)"),
        ("density_kg_dm3", "NUMERIC(8,3)"), ("unit_cost_eur", "NUMERIC(14,4)"),
        ("pricing_currency", "TEXT"), ("moq", "NUMERIC(12,2)"),
        ("lead_time_days", "INT"), ("is_customer_supplied", "BOOLEAN"),
        ("origin_country", "TEXT"), ("hs_code", "TEXT"),
    ],
    "price_list": [
        ("currency", "TEXT"), ("price_try", "NUMERIC(16,4)"),
        ("price_eur", "NUMERIC(16,4)"), ("price_usd", "NUMERIC(16,4)"),
        ("customer_id", "INT"), ("min_qty", "NUMERIC(12,2)"),
        ("agreement_no", "TEXT"), ("price_type", "TEXT"),
    ],
    "sales_orders": [
        ("fx_rate_eur", "NUMERIC(18,8)"), ("fx_rate_usd", "NUMERIC(18,8)"),
        ("subtotal_eur", "NUMERIC(16,2)"), ("subtotal_usd", "NUMERIC(16,2)"),
        ("total_eur", "NUMERIC(16,2)"), ("total_usd", "NUMERIC(16,2)"),
        ("cogs_eur", "NUMERIC(16,2)"), ("margin_eur", "NUMERIC(16,2)"),
        ("margin_usd", "NUMERIC(16,2)"), ("customer_po_no", "TEXT"),
        ("requested_date", "DATE"), ("confirmed_date", "DATE"),
        ("shipped_date", "DATE"), ("is_on_time", "BOOLEAN"),
        ("delay_days", "INT"), ("total_qty", "NUMERIC(16,2)"),
        ("order_source", "TEXT"), ("notes", "TEXT"),
    ],
    "sales_order_lines": [
        ("line_subtotal_eur", "NUMERIC(16,2)"), ("line_subtotal_usd", "NUMERIC(16,2)"),
        ("line_cogs_eur", "NUMERIC(16,2)"), ("line_margin_eur", "NUMERIC(16,2)"),
        ("line_margin_usd", "NUMERIC(16,2)"), ("unit_price_eur", "NUMERIC(16,4)"),
        ("requested_date", "DATE"), ("shipped_qty", "NUMERIC(14,2)"),
    ],
    "invoices": [
        ("fx_rate_eur", "NUMERIC(18,8)"), ("fx_rate_usd", "NUMERIC(18,8)"),
        ("subtotal_eur", "NUMERIC(16,2)"), ("subtotal_usd", "NUMERIC(16,2)"),
        ("total_eur", "NUMERIC(16,2)"), ("total_usd", "NUMERIC(16,2)"),
        ("balance_eur", "NUMERIC(16,2)"), ("balance_usd", "NUMERIC(16,2)"),
        ("e_invoice_no", "TEXT"), ("invoice_type", "TEXT"),
    ],
    "payments": [
        ("amount_eur", "NUMERIC(16,2)"), ("amount_usd", "NUMERIC(16,2)"),
    ],
    "purchase_orders": [
        ("fx_rate_eur", "NUMERIC(18,8)"), ("fx_rate_usd", "NUMERIC(18,8)"),
        ("total_eur", "NUMERIC(16,2)"), ("total_usd", "NUMERIC(16,2)"),
        ("spend_category", "TEXT"), ("notes", "TEXT"),
    ],
    "vendor_invoices": [
        ("total_eur", "NUMERIC(16,2)"), ("total_usd", "NUMERIC(16,2)"),
        ("balance_base", "NUMERIC(16,2)"),
    ],
    "expenses": [
        ("amount_eur", "NUMERIC(16,2)"), ("amount_usd", "NUMERIC(16,2)"),
        ("fx_rate_eur", "NUMERIC(18,8)"), ("fx_rate_usd", "NUMERIC(18,8)"),
        ("work_center_id", "INT"),
    ],
    "payroll_runs": [
        ("employer_cost_eur", "NUMERIC(16,2)"), ("employer_cost_usd", "NUMERIC(16,2)"),
        ("overtime_total", "NUMERIC(16,2)"), ("department_id", "INT"),
    ],
    "payroll_items": [
        ("employer_cost_eur", "NUMERIC(14,2)"), ("employer_cost_usd", "NUMERIC(14,2)"),
        ("department_id", "INT"), ("shift", "TEXT"), ("shift_premium", "NUMERIC(14,2)"),
        ("overtime_hours", "NUMERIC(8,2)"), ("severance_provision", "NUMERIC(14,2)"),
        ("meal_allowance", "NUMERIC(14,2)"), ("transport_allowance", "NUMERIC(14,2)"),
        ("stamp_duty", "NUMERIC(14,2)"), ("unemployment_employee", "NUMERIC(14,2)"),
        ("unemployment_employer", "NUMERIC(14,2)"),
    ],
    "production_orders": [
        ("wo_no", "TEXT"), ("sales_order_id", "INT"), ("customer_id", "INT"),
        ("routing_version", "TEXT"), ("priority", "TEXT"), ("lot_no", "TEXT"),
        ("warehouse_id", "INT"), ("planner_id", "INT"), ("supervisor_id", "INT"),
        ("shift", "TEXT"), ("planned_start", "DATE"), ("planned_end", "DATE"),
        ("actual_start", "DATE"), ("actual_end", "DATE"), ("good_qty", "NUMERIC(14,2)"),
        ("rework_qty", "NUMERIC(14,2)"), ("yield_pct", "NUMERIC(7,3)"),
        ("scrap_pct", "NUMERIC(7,3)"), ("material_cost", "NUMERIC(16,2)"),
        ("labor_cost", "NUMERIC(16,2)"), ("machine_cost", "NUMERIC(16,2)"),
        ("tooling_cost", "NUMERIC(16,2)"), ("subcontract_cost", "NUMERIC(16,2)"),
        ("overhead_cost", "NUMERIC(16,2)"), ("total_cost", "NUMERIC(16,2)"),
        ("total_cost_eur", "NUMERIC(16,2)"), ("total_cost_usd", "NUMERIC(16,2)"),
        ("std_total_cost", "NUMERIC(16,2)"), ("cost_variance", "NUMERIC(16,2)"),
        ("setup_minutes_total", "NUMERIC(12,2)"), ("run_minutes_total", "NUMERIC(14,2)"),
        ("downtime_minutes_total", "NUMERIC(12,2)"), ("is_on_time", "BOOLEAN"),
        ("delay_days", "INT"), ("notes", "TEXT"),
    ],
    "production_consumption": [
        ("issue_date", "DATE"), ("warehouse_id", "INT"), ("lot_no", "TEXT"),
        ("total_cost", "NUMERIC(16,2)"), ("variance_qty", "NUMERIC(14,4)"),
    ],
    "lots": [
        ("customer_id", "INT"), ("heat_no", "TEXT"), ("material_lot", "TEXT"),
        ("warehouse_id", "INT"), ("status", "TEXT"), ("remaining_qty", "NUMERIC(14,2)"),
        ("certificate_no", "TEXT"),
    ],
    "shipments": [
        ("cost_eur", "NUMERIC(14,2)"), ("cost_usd", "NUMERIC(14,2)"),
        ("pallet_count", "INT"), ("packaging_type", "TEXT"), ("border_gate", "TEXT"),
        ("plate_no", "TEXT"),
    ],
    "gl_entries": [
        ("fx_rate_eur", "NUMERIC(18,8)"), ("fx_rate_usd", "NUMERIC(18,8)"),
    ],
    "bank_transactions": [
        ("amount_eur", "NUMERIC(16,2)"), ("amount_usd", "NUMERIC(16,2)"),
        ("bank_name", "TEXT"), ("account_currency", "TEXT"),
    ],
    "customers": [
        ("customer_since", "DATE"), ("abc_class", "TEXT"), ("edi_enabled", "BOOLEAN"),
        ("quality_agreement", "BOOLEAN"), ("supplier_code", "TEXT"),
        ("region", "TEXT"), ("ppm_target", "NUMERIC(10,2)"),
    ],
    "vendors": [
        ("is_approved", "BOOLEAN"), ("approval_date", "DATE"),
        ("quality_score", "NUMERIC(5,2)"), ("otd_score", "NUMERIC(5,2)"),
        ("iso_certified", "BOOLEAN"), ("region", "TEXT"),
    ],
    "returns": [
        ("ncr_id", "INT"), ("credit_note_no", "TEXT"),
    ],
    "fixed_assets": [
        ("machine_id", "INT"), ("acquisition_cost_eur", "NUMERIC(16,2)"),
        ("fx_rate", "NUMERIC(18,8)"), ("currency", "TEXT"),
    ],
    "iot_readings": [
        ("work_center_id", "INT"), ("shift", "TEXT"),
    ],
}

# TRY tutarları nominal olarak yüksektir (500 milyon TL ciro, milyarlarca liralık
# yevmiye toplamı), bu yüzden bazı kolonların tamsayı basamağı genişletilir.
WIDEN = {
    "sales_orders": {"subtotal": "NUMERIC(18,2)", "discount": "NUMERIC(18,2)",
                     "tax": "NUMERIC(18,2)", "total": "NUMERIC(18,2)",
                     "cogs": "NUMERIC(18,2)", "margin": "NUMERIC(18,2)"},
    "sales_order_lines": {"line_subtotal": "NUMERIC(18,2)", "tax": "NUMERIC(18,2)",
                          "line_total": "NUMERIC(18,2)", "line_cogs": "NUMERIC(18,2)",
                          "line_margin": "NUMERIC(18,2)", "qty": "NUMERIC(16,2)"},
    "invoices": {"subtotal": "NUMERIC(18,2)", "tax": "NUMERIC(18,2)",
                 "total": "NUMERIC(18,2)", "amount_paid": "NUMERIC(18,2)",
                 "balance": "NUMERIC(18,2)"},
    "invoice_lines": {"qty": "NUMERIC(16,2)", "line_total": "NUMERIC(18,2)"},
    "payments": {"amount": "NUMERIC(18,2)"},
    "purchase_orders": {"subtotal": "NUMERIC(18,2)", "tax": "NUMERIC(18,2)",
                        "total": "NUMERIC(18,2)"},
    "purchase_order_lines": {"qty": "NUMERIC(16,2)", "line_total": "NUMERIC(18,2)",
                             "received_qty": "NUMERIC(16,2)"},
    "returns": {"qty": "NUMERIC(16,2)", "refund_amount": "NUMERIC(18,2)"},
    "production_orders": {"planned_qty": "NUMERIC(16,2)", "produced_qty": "NUMERIC(16,2)",
                          "scrap_qty": "NUMERIC(16,2)"},
    "production_consumption": {"planned_qty": "NUMERIC(18,4)",
                               "consumed_qty": "NUMERIC(18,4)"},
    "lots": {"qty": "NUMERIC(16,2)"},
    "stock_moves": {"qty": "NUMERIC(18,2)", "value_base": "NUMERIC(18,2)"},
    "bank_transactions": {"amount": "NUMERIC(18,2)", "balance_after": "NUMERIC(20,2)"},
    "gl_entries": {"debit": "NUMERIC(18,2)", "credit": "NUMERIC(18,2)",
                   "debit_base": "NUMERIC(18,2)", "credit_base": "NUMERIC(18,2)"},
    "expenses": {"amount": "NUMERIC(18,2)", "amount_base": "NUMERIC(18,2)",
                 "tax_amount": "NUMERIC(18,2)", "total_base": "NUMERIC(18,2)"},
    "budgets": {"budget_amount": "NUMERIC(18,2)"},
    "payroll_runs": {"gross_total": "NUMERIC(18,2)",
                     "employee_deductions_total": "NUMERIC(18,2)",
                     "net_total": "NUMERIC(18,2)",
                     "employer_cost_total": "NUMERIC(18,2)",
                     "employer_cost_base": "NUMERIC(18,2)"},
    "payroll_items": {"base_salary": "NUMERIC(16,2)", "gross_pay": "NUMERIC(16,2)",
                      "net_pay": "NUMERIC(16,2)", "employer_cost": "NUMERIC(16,2)",
                      "employer_cost_base": "NUMERIC(16,2)"},
    "vendor_invoices": {"subtotal": "NUMERIC(18,2)", "tax": "NUMERIC(18,2)",
                        "total": "NUMERIC(18,2)", "total_base": "NUMERIC(18,2)",
                        "amount_paid": "NUMERIC(18,2)", "balance": "NUMERIC(18,2)"},
    "vendor_payments": {"amount": "NUMERIC(18,2)", "amount_base": "NUMERIC(18,2)"},
    "fixed_assets": {"acquisition_cost": "NUMERIC(18,2)",
                     "accumulated_depreciation": "NUMERIC(18,2)",
                     "net_book_value": "NUMERIC(18,2)", "salvage_value": "NUMERIC(18,2)"},
    "depreciation_entries": {"depreciation_amount": "NUMERIC(18,2)",
                             "accumulated_after": "NUMERIC(18,2)",
                             "book_value_after": "NUMERIC(18,2)"},
    "quotations": {"subtotal": "NUMERIC(18,2)", "discount": "NUMERIC(18,2)",
                   "tax": "NUMERIC(18,2)", "total": "NUMERIC(18,2)",
                   "total_base": "NUMERIC(18,2)"},
    "quotation_lines": {"qty": "NUMERIC(16,2)", "line_total": "NUMERIC(18,2)"},
    "opportunities": {"amount": "NUMERIC(18,2)", "amount_base": "NUMERIC(18,2)"},
    "customers": {"credit_limit": "NUMERIC(18,2)"},
    "employees": {"salary": "NUMERIC(16,2)", "annual_gross": "NUMERIC(16,2)"},
    "products": {"unit_cost": "NUMERIC(16,4)", "list_price": "NUMERIC(16,4)"},
    "raw_materials": {"unit_cost": "NUMERIC(16,4)"},
    "price_list": {"price": "NUMERIC(16,4)"},
    "shipments": {"freight_cost": "NUMERIC(16,2)", "insurance_cost": "NUMERIC(16,2)",
                  "packing_cost": "NUMERIC(16,2)", "handling_cost": "NUMERIC(16,2)",
                  "total_logistics_cost": "NUMERIC(16,2)", "cost_base": "NUMERIC(16,2)",
                  "billed_to_customer": "NUMERIC(16,2)"},
    "customs_declarations": {"customs_value": "NUMERIC(18,2)",
                             "customs_value_base": "NUMERIC(18,2)",
                             "duty_amount": "NUMERIC(16,2)",
                             "vat_amount": "NUMERIC(16,2)"},
}


def install(table_order: list, columns: dict, ddl_map: dict, indexes: dict) -> None:
    """ddl.py kayıtlarına bu modülün tanımlarını birleştirir."""
    from .ddl_ext import _append_columns, _widen

    for table, defs in EXTRA_COLUMNS.items():
        if table not in columns:
            continue
        new = [c for c, _ in defs if c not in columns[table]]
        if not new:
            continue
        columns[table] = columns[table] + new
        ddl_map[table] = _append_columns(ddl_map[table], [d for d in defs if d[0] in new])

    columns.update(COLUMNS)
    ddl_map.update(DDL)

    for table, cols in WIDEN.items():
        if table in ddl_map:
            ddl_map[table] = _widen(ddl_map[table], cols)

    for t, cols in INDEXES.items():
        indexes.setdefault(t, []).extend(c for c in cols if c not in indexes.get(t, []))

    for table, after in ORDER_AFTER:
        if table in table_order:
            continue
        if after in table_order:
            table_order.insert(table_order.index(after) + 1, table)
        else:
            table_order.append(table)
