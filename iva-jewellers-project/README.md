# Retail Profitability, Demand Forecasting & Inventory Planning

**Case study: Iva Jewellers**, a fictional 3-store jewellery retailer in the Greater Toronto Area.

> 🚧 **In progress:** data and SQL are complete. The Excel forecast model, Power BI dashboard and Tableau story are coming next.

**Tools:** Python · MySQL · Excel · Power BI · Tableau

> **All data is synthetic.** Iva Jewellers and its stores, suppliers and customers are fictional. I generated the data with a Python script (`python/generate_data.py`) based on how jewellery retail actually works: gold-rate pricing, making charges, supplier wastage, festival seasons and reorder policies. No real business records are used.

---

## The business problem

Iva Jewellers sells 22K gold, diamond and silver jewellery and gold coins across 3 GTA stores (Brampton, Mississauga, and Toronto–Gerrard St, which opened in March 2024). Selling prices move with the daily gold rate, so revenue and margin depend on volume, gold price, making charges, discounts and product mix.

**In FY2026, the business came in close to its sales budget, but gross profit fell well below plan.** This project finds out why and recommends what to do about it.

## Business questions

1. **Profitability:** Which categories, collections, stores and customer segments actually make money after discounts, returns and inventory costs?
2. **Budget vs. actual:** Why did gross profit miss budget when sales were close? How much is due to gold price, volume, product mix and discounts?
3. **Forecast:** What will sales and gross profit be through Dec 2027 under different gold-price and discount scenarios?
4. **Inventory & supply chain:**
   - What are inventory turns by category?
   - Which stock is aging?
   - Are we stocking the right ring sizes?
   - Where are we losing sales to stockouts?
   - Which suppliers are late or charge the most gold wastage?
5. **Actions:** What happens to margin if we:
   - cut festival discounts,
   - switch to lower-wastage suppliers,
   - clear aged stock?

## Early findings (from the SQL KPI views)

| Area | Finding |
|---|---|
| Budget vs. actual (Jan–Sep 2026) | Sales were **3% under** budget, but gross profit was **17% under** |
| Margin trend | Gross margin fell from **19.2% (2025)** to **15.8% (2026)** |
| Aged stock | The Temple Heritage collection has about **CAD 494K** of stock with no sale in 31–90 days |
| Ring sizes | Size 7 has the most lost sales from stockouts, while sizes 5 and 9 sit in stock, because every size got the same stock depth |
| Suppliers | The slowest supplier delivers on time only **69%** of the time and charges the **highest wastage (7%)** |

*The full analysis, dashboards and recommendations will be added as the project progresses.*

---

## Repository structure

```
├── data/                  13 raw CSV files (sales, returns, POs, inventory, opex, budget, gold rates)
├── python/
│   └── generate_data.py   synthetic data generator (fixed seed, reproducible)
└── sql/
    ├── 01_create_and_load.sql   schema + load raw CSVs into staging tables
    ├── 02_clean.sql             cleaning: 9 data-quality issues fixed, with checks
    └── 03_kpi_views.sql         7 KPI views used by Excel / Power BI / Tableau
```

## Data model

| Table | Grain | Rows |
|---|---|---|
| `fact_sales` | invoice line | 34,633 (after cleaning) |
| `fact_returns` | return | 1,006 |
| `fact_po` | purchase order line | 5,365 |
| `fact_inventory` | month-end × store × SKU | 13,703 |
| `fact_missed_requests` | out-of-stock request | 1,423 |
| `fact_opex_monthly` | month × store × expense | 1,089 |
| `budget_fy2026_sales` / `_opex` | month × store × category / expense | 360 / 324 |
| `dim_products` · `dim_stores` · `dim_suppliers` · `dim_customers` · `gold_rates_daily` | lookups | 123 · 3 · 8 · 11,353 · 1,369 |

**How a sale is priced:**

```
metal_value   = net_weight_g × purity × gold_rate (sale date)
making_charge = metal_value × making_charge_pct
net_sales     = metal_value + making_charge + stone_value − discount        (excl. 13% HST)
cogs          = weighted-average cost (gold rate on receipt × (1 + supplier wastage) + labour + stone)
```

COGS is based on the gold rate when the stock arrived, so a rising gold price creates holding gains, and a flat price squeezes margin. This is a key part of the FY2026 story.

## Data cleaning (SQL)

| # | Issue | Fix | Rows |
|---|---|---|---|
| 1 | Duplicate invoice lines (double export) | Fix formats first, then keep 1 row per `line_id` with `ROW_NUMBER()` | 139 |
| 2 | Store codes like `st01`, `ST01 ` | `UPPER(TRIM())` | 104 |
| 3 | Dates in `DD/MM/YYYY` | `STR_TO_DATE` with a format check | 70 |
| 4 | Missing net sales | Recompute from its components | 6 |
| 5 | Segment `everyday` vs `Everyday` | Standardize the case | 25 |
| 6 | Blank customer ID (walk-ins) | Label as `WALK-IN`; keep the sale | 2,718 |
| 7 | Category with trailing spaces | `TRIM()` | 5 |
| 8 | Missing product weight | Fill from actual weight sold per unit | 2 |
| 9 | Open purchase orders | Keep, but exclude from lead-time KPIs | 100 |

One detail matters here: 138 duplicates are exact copies, but **one more only shows up after the date and store formats are fixed**. That's why the formats are cleaned before duplicates are removed. Clean result: **34,633 sales lines**.

## KPI views

| View | What it answers |
|---|---|
| `v_monthly_pnl` | Monthly P&L by store: sales, returns, gross profit, opex, operating profit |
| `v_category_profitability` | Margin and discount rate by year, category and collection |
| `v_inventory_turns` | Annualized inventory turns and days of inventory by category |
| `v_aged_stock` | Latest stock by age bucket (0–30 / 31–90 / 91–180 / 180+ days) |
| `v_supplier_scorecard` | On-time rate, lead time, spend and gold-wastage cost per supplier |
| `v_budget_vs_actual_2026` | FY2026 budget vs. actual sales and gross profit |
| `v_stockouts` | Missed requests and lost sales by category, collection and size |

## How to run

1. Install MySQL 8+ and MySQL Workbench.
2. Run `sql/01_create_and_load.sql`, `02_clean.sql` and `03_kpi_views.sql` in that order.
3. **Loading the CSVs on Windows:** if `LOAD DATA LOCAL` is blocked, do this instead:
   - Run `SHOW VARIABLES LIKE 'secure_file_priv';` to find the allowed folder.
   - Copy the CSVs into that folder.
   - In `01_create_and_load.sql`, change `LOAD DATA LOCAL INFILE` to `LOAD DATA INFILE` and point the file paths at that folder.

To regenerate the data:

```
pip install pandas numpy
python python/generate_data.py data
```

## Roadmap

- [x] Synthetic dataset (Python)
- [x] Load, clean and KPI views (MySQL)
- [ ] Driver-based forecast + budget-vs-actual bridge + scenarios (Excel)
- [ ] Finance dashboard: P&L, variance, profitability (Power BI)
- [ ] Inventory & supply chain story (Tableau Public)
- [ ] Findings memo and recommendations

---

**Ashwini Dalve** · [LinkedIn](https://www.linkedin.com/in/ashwini-dalve) · [GitHub](https://github.com/adalve02)
