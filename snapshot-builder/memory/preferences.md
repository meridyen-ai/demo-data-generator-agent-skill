# User defaults for snapshot-builder

- **Default target**: the demo Postgres (`erp-demo-gen`'s `erp_demo_pg` container),
  connection name `demo`. Auto-detect the single `erp_*` database.
- **Dialect**: PostgreSQL for all generated SQL in instructions.
- **Output**: content-only snapshot (platform IDs left null; user wires them on import).
- **Verification**: full self-test — execute every metric recipe before finalizing.
- **Style**: be concrete and verified — exact column names, exact Postgres expressions,
  and real discovered distinct values; route each question to the fewest tables.

Update this when the user states a new lasting preference (e.g. a default remote DB,
preferred prompt set, or naming conventions).
