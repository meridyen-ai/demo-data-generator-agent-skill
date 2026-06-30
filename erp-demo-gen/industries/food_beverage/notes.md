# Food & Beverage / Process Manufacturing — tuning notes

- **Margins** ~28%; tighter than discrete mfg, commodity input pressure.
- **Summer-peaking seasonality** (Jun–Aug) — beverages/cold goods.
- **Lots + expiry**: every production order yields a `lots` row with a shelf
  life of `shelf_life_days` (default 180) from production date.
- **Cold-chain IoT**: temperature/humidity in cold storage + batch yield, sampled
  for the most recent `iot_days`.
- **Lower sales tax** (groceries often reduced-rate). Payment terms 15–45 days.

## Seed guidance for the LLM
- Products = finished consumables (e.g. "Cold Brew Concentrate 1L", "Organic Granola 500g").
- Raw materials = ingredients + packaging (e.g. "Arabica Beans", "Cane Sugar", "PET Bottle 1L").
- Customers = distributors, grocery/retail chains, foodservice. Vendors = ingredient/packaging suppliers, co-packers.
- Work centers = process lines (e.g. "Brew Line 1", "Bottling Line A", "Packaging Line").
