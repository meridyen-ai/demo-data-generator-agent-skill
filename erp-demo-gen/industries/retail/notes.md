# Retail / E-commerce — tuning notes

- **High margins** (~45%) and **high return rate** (~9%) typical of consumer retail.
- **Strong Q4 seasonality** (Nov 1.35, Dec 1.6) for holiday shopping.
- **Many customers** (consumer-level, ~5000) and **small baskets** (2.4 lines).
- **Mostly immediate payment** (terms ~0 days), so very low overdue/open AR.
- **Channels**: Online / In-Store / Marketplace / Mobile App. Warehouses model stores.
- **Promotions** table active — a few campaigns per year by category.

## Seed guidance for the LLM
- Products = consumer SKUs across the retailer's categories.
- Customers = individual shoppers / loyalty members (person- or household-style names ok).
- Vendors = brands, wholesalers, importers.
