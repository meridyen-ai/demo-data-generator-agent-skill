# User defaults for erp-demo-gen

These are the user's recurring preferences. Apply them as defaults during intake
so the user can answer fast (they can always override per run). Update this file
when the user expresses a new lasting preference.

- **Locale / currency**: English / Global, USD ($).
- **Purpose**: fresh fictional databases to feed an LLM-driven data-analysis
  product during demos and presales. Data should look real and meaningful.
- **Delivery**: local Postgres via Docker (connection string handed back).
- **Default span**: ask each time (user typically picks 5–15 years).
- **Default seed**: 42 unless the user wants a different/random one.
- **Naming style**: realistic, on-industry company and product names.

## Open tuning questions to refine over time
- Preferred default company size band when the user doesn't specify? (currently "medium")
- Any industries the user demos most? (track in changelog)
