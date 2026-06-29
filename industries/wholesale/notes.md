# Wholesale / Distribution — tuning notes

- **Margins** thin (~22%): buy-and-resell, value is in volume + logistics.
- **More lines per order** (5) and **more customers** than manufacturing — many
  resellers ordering broad assortments.
- **Multiple warehouses/DCs** (4) to support multi-region distribution.
- **Longer payment terms** (up to 90 days) and higher overdue rate — typical B2B.
- No production: purchases are finished `products` for resale (item_type=product).

## Seed guidance for the LLM
- Products = resold finished goods across categories the distributor carries.
- Customers = retailers, resellers, regional chains. Vendors = brands/importers/manufacturers.
