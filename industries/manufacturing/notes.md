# Manufacturing — tuning notes

Human-readable rationale behind `tuning.json`. Update this whenever a generated
database looked wrong so future runs improve.

- **Margins** ~34% gross; discrete mfg sits below distribution markups but above
  commodity process goods.
- **Seasonality** dips in Jul/Aug (summer slowdown / maintenance shutdowns),
  peaks Sep–Dec (Q4 push).
- **Production**: each finished product has a BOM consuming 2–5 raw materials;
  production volume tracks ~105% of units sold (scrap + safety stock).
- **IoT**: machine telemetry sampled for the most recent `iot_days` only (kept
  bounded on purpose — note this in demos). Metrics: uptime, units, temp, vibration.

## Seed guidance for the LLM
- Products = finished goods (e.g. "CNC Spindle Motor 5kW", "Hydraulic Valve Block").
- Raw materials = inputs (e.g. "Cold-Rolled Steel Sheet", "Copper Wire 1.5mm").
- Customers = OEMs, distributors, industrial buyers. Vendors = material/component suppliers.
- Work centers = production lines / cells (e.g. "CNC Cell A", "Assembly Line 2").
