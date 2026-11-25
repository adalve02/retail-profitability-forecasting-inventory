# Retail Profitability, Demand Forecasting & Inventory Planning

**Case study: Iva Jewellers** (fictional 3-store GTA jewellery retailer)

> **All data is synthetic.** Iva Jewellers, its stores, suppliers and customers are fictional. The data was generated with `generate_data.py` using realistic jewellery-retail rules (gold-rate pricing, making charges, supplier wastage, festival seasonality, reorder policies). No real business records are used.

## Business context

Iva Jewellers is a South Asian jewellery retailer with 3 stores in the Greater Toronto Area:

- **Brampton:** the flagship store.
- **Mississauga.**
- **Toronto (Gerrard St):** opened March 2024.

The stores sell 22K gold, diamond, silver jewellery and gold coins. Prices move with the daily gold rate, so revenue and margin depend on volume, gold price, making charges, discounts and product mix.

**Period:** Jan 2023 – Sep 2026 actuals, plus the FY2026 budget. All amounts are in CAD.

## Business questions

1. **Profitability:** Which categories, collections, stores and customer segments make money after discounts, returns and inventory costs? (Contribution margin)
2. **Budget vs. actual (FY2026 YTD):** Sales are close to plan, but gross profit is well below plan. Why? Split the gap into price (gold rate), volume, mix and margin effects.
3. **Forecast:** What will Oct 2026 – Dec 2027 sales and gross profit be? How do they change under gold-price and discount scenarios?
4. **Inventory and supply chain:**
   - Inventory turns and days of inventory by category.
   - Slow-moving and aged stock, including the Temple Heritage collection.
   - Stock depth by ring size.
   - Stockouts and missed sales.
   - Supplier on-time delivery and the cost of gold wastage.
5. **Scenarios:** What happens to margin if we:
   - cut festival making-charge discounts by 10 points,
   - move orders to lower-wastage suppliers,
   - mark down or return aged stock?

## Files (`/data`)

| File | Grain | Rows | Notes |
|---|---|---|---|
| `dim_stores.csv` | store | 3 | Headcount and rent |
| `dim_suppliers.csv` | supplier | 8 | Gold wastage %, labour CAD/g, standard lead time |
| `dim_products.csv` | SKU (design × size) | 123 | Category, karat, weight, making charge %, collection, launch date. **Raw (has issues).** |
| `dim_customers.csv` | customer | ~11.4k | Segment, city, gold savings plan member |
| `gold_rates_daily.csv` | day | 1,369 | Simulated 24K/22K/18K gold and silver CAD per gram |
| `fact_sales_raw.csv` | invoice line | 34,772 | POS export. **Raw (has issues).** |
| `fact_returns.csv` | return | 1,006 | Exchange, refund or store credit, with reason. Links to `line_id`. |
| `fact_purchase_orders.csv` | PO line | 5,365 | Order, expected and received dates, unit cost, wastage. Open POs have no receipt date. |
| `fact_inventory_month_end.csv` | month × store × SKU | 13,703 | On hand, on order, average cost, value, days since last sale |
| `fact_missed_requests.csv` | request | 1,423 | Customer asked for an out-of-stock SKU; shows whether a substitute was sold |
| `fact_opex_monthly.csv` | month × store × expense | 1,089 | Rent, wages, marketing, card fees and other expenses |
| `budget_fy2026_sales.csv` | month × store × category | 360 | Budget units, gold-rate assumption (CAD 165/g), net sales, gross profit |
| `budget_fy2026_opex.csv` | month × store × expense | 324 | FY2026 opex budget |

### How a sales line is priced

```
metal_value   = net_weight_g × purity × gold_rate_24k (on sale date)
making_charge = metal_value × making_charge_pct
net_sales     = metal_value + making_charge + stone_value + silver_item_value − discount   (excl. 13% HST)
cogs          = weighted-average unit cost of that SKU in that store
                (supplier cost = weight × purity × gold rate on receipt × (1 + wastage) + labour + stone cost)
```

Because COGS is based on the gold rate when the stock was received, rising gold prices create holding gains, and flat or falling prices squeeze margin. This is a key part of the FY2026 story.

## Data-cleaning tasks (step 2: do these in SQL or Python)

| # | Issue | Table | Count |
|---|---|---|---|
| 1 | Exact duplicate lines (double export) | sales | 138 |
| 2 | Store code with lowercase or extra spaces (`st01`, `ST01 `) | sales | 104 |
| 3 | Dates in `DD/MM/YYYY` instead of `YYYY-MM-DD` | sales | 70 |
| 4 | Missing `net_sales_cad`: recompute from its components | sales | 6 |
| 5 | Segment `everyday` vs `Everyday` | sales | 25 |
| 6 | Blank `customer_id` (walk-in): label as `WALK-IN`, don't delete | sales | 2,718 |
| 7 | Category with trailing space | products | 5 |
| 8 | Missing `net_weight_g`: fill from the same design's other sizes | products | 2 |
| 9 | Open POs (not yet received): keep them, but exclude from lead-time KPIs | POs | 100 |

After cleaning, sales should have **34,633 rows**. (138 duplicates are exact copies; 1 more only shows up after you fix the date and store formats, which is why you fix formats before removing duplicates.)

## Project roadmap

| Step | Tool | Output |
|---|---|---|
| 1 | Python | Synthetic dataset (this folder) ✅ |
| 2 | MySQL | `01_create_and_load.sql` → `02_clean.sql` → `03_kpi_views.sql` ✅ (P&L, product profitability, inventory turns, aged stock, supplier scorecard, budget vs actual, stockouts) |
| 3 | Excel | Driver-based forecast (units × weight × gold rate × (1 + making %)), budget-vs-actual bridge (price / volume / mix / margin), scenario toggles |
| 4 | Power BI | Finance dashboard: Executive P&L, Budget vs. Actual bridge, Product & collection profitability, Forecast & scenarios |
| 5 | Tableau Public | Inventory & supply chain story: turns and aging, ring-size depth, stockouts, supplier scorecard. Gets a public link for the resume. |
| 6 | GitHub + LinkedIn | README with screenshots, a 1-page findings memo, and a post |

## Regenerating the data

```
pip install pandas numpy
python generate_data.py data
```

The generator uses a fixed seed, so it produces the same output every run.
