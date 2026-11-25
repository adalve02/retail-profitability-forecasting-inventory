-- =====================================================================
-- Step 3: KPI views (run after 02_clean.sql)
-- These views are what Excel, Power BI and Tableau will read.
-- =====================================================================
USE iva_jewellers;

-- ---------------------------------------------------------------------
-- 1. Monthly P&L by store
--    Net revenue = sales - refunds/exchanges (by return month)
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_monthly_pnl AS
WITH s AS (
  SELECT DATE_FORMAT(sale_date, '%Y-%m') AS month, store_id,
         SUM(net_sales_cad) AS gross_sales, SUM(cogs_cad) AS cogs,
         SUM(discount_cad) AS discounts, COUNT(DISTINCT invoice_id) AS invoices
  FROM fact_sales GROUP BY 1, 2
),
r AS (
  SELECT DATE_FORMAT(return_date, '%Y-%m') AS month, store_id,
         SUM(refund_amount_cad) AS returns_value, SUM(cogs_reversed_cad) AS cogs_reversed
  FROM fact_returns GROUP BY 1, 2
),
o AS (
  SELECT month, store_id, SUM(amount_cad) AS opex
  FROM fact_opex_monthly GROUP BY 1, 2
)
SELECT s.month, s.store_id, s.invoices,
       s.gross_sales,
       s.discounts,
       COALESCE(r.returns_value, 0)                                   AS returns_value,
       s.gross_sales - COALESCE(r.returns_value, 0)                   AS net_revenue,
       s.cogs - COALESCE(r.cogs_reversed, 0)                          AS net_cogs,
       (s.gross_sales - COALESCE(r.returns_value, 0))
         - (s.cogs - COALESCE(r.cogs_reversed, 0))                    AS gross_profit,
       COALESCE(o.opex, 0)                                            AS opex,
       (s.gross_sales - COALESCE(r.returns_value, 0))
         - (s.cogs - COALESCE(r.cogs_reversed, 0)) - COALESCE(o.opex, 0) AS operating_profit
FROM s
LEFT JOIN r ON r.month = s.month AND r.store_id = s.store_id
LEFT JOIN o ON o.month = s.month AND o.store_id = s.store_id;

-- ---------------------------------------------------------------------
-- 2. Product profitability by year, category and collection
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_category_profitability AS
SELECT YEAR(s.sale_date)                                  AS yr,
       p.category, p.collection,
       SUM(s.qty)                                         AS units,
       SUM(s.net_sales_cad)                               AS net_sales,
       SUM(s.gross_profit_cad)                            AS gross_profit,
       ROUND(SUM(s.gross_profit_cad) / SUM(s.net_sales_cad), 4) AS gross_margin_pct,
       SUM(s.making_charge_cad)                           AS making_charges,
       SUM(s.discount_cad)                                AS discounts,
       ROUND(SUM(s.discount_cad) / NULLIF(SUM(s.making_charge_cad + s.silver_item_value_cad), 0), 4)
                                                          AS discount_pct_of_markup
FROM fact_sales s
JOIN dim_products p USING (sku)
GROUP BY 1, 2, 3;

-- ---------------------------------------------------------------------
-- 3. Inventory turns by year and category
--    Turns = COGS / average month-end inventory value
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_inventory_turns AS
WITH inv AS (
  SELECT YEAR(i.snapshot_date) AS yr, p.category,
         SUM(i.inventory_cost_value_cad) / COUNT(DISTINCT i.snapshot_date) AS avg_inventory_value
  FROM fact_inventory i JOIN dim_products p USING (sku)
  GROUP BY 1, 2
),
c AS (
  SELECT YEAR(s.sale_date) AS yr, p.category,
         SUM(s.cogs_cad) AS cogs, COUNT(DISTINCT MONTH(s.sale_date)) AS months
  FROM fact_sales s JOIN dim_products p USING (sku)
  GROUP BY 1, 2
)
SELECT c.yr, c.category, c.cogs, inv.avg_inventory_value,
       ROUND((c.cogs * 12 / c.months) / inv.avg_inventory_value, 2)       AS annualised_turns,
       ROUND(365 / ((c.cogs * 12 / c.months) / inv.avg_inventory_value), 0) AS days_of_inventory
FROM c JOIN inv ON inv.yr = c.yr AND inv.category = c.category;

-- ---------------------------------------------------------------------
-- 4. Aged stock at the latest month-end (no sale in 90+ days)
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_aged_stock AS
SELECT i.snapshot_date, i.store_id, i.sku, p.design_name, p.category, p.collection, p.size,
       i.on_hand_qty, i.inventory_cost_value_cad, i.days_since_last_sale,
       CASE WHEN i.days_since_last_sale IS NULL OR i.days_since_last_sale > 180 THEN '180+ days / never sold'
            WHEN i.days_since_last_sale > 90 THEN '91-180 days'
            WHEN i.days_since_last_sale > 30 THEN '31-90 days'
            ELSE '0-30 days' END AS age_bucket
FROM fact_inventory i
JOIN dim_products p USING (sku)
WHERE i.snapshot_date = (SELECT MAX(snapshot_date) FROM fact_inventory)
  AND i.on_hand_qty > 0;

-- ---------------------------------------------------------------------
-- 5. Supplier scorecard (received POs only for delivery KPIs)
--    Wastage cost = extra gold paid above net metal weight
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_supplier_scorecard AS
SELECT po.supplier_id, sp.supplier_name, sp.country,
       COUNT(*)                                             AS po_lines,
       SUM(po.status = 'Received')                          AS received_lines,
       ROUND(AVG(po.on_time_flag), 3)                       AS on_time_rate,
       ROUND(AVG(po.actual_lead_days), 1)                   AS avg_lead_days,
       sp.standard_lead_time_days,
       SUM(po.total_cost_cad)                               AS spend_cad,
       sp.gold_wastage_pct,
       ROUND(SUM(po.qty_ordered * p.net_weight_g * p.purity
                 * po.gold_rate_24k_on_receipt * sp.gold_wastage_pct), 2) AS wastage_cost_cad
FROM fact_po po
JOIN dim_suppliers sp USING (supplier_id)
JOIN dim_products p USING (sku)
GROUP BY po.supplier_id, sp.supplier_name, sp.country, sp.standard_lead_time_days, sp.gold_wastage_pct;

-- ---------------------------------------------------------------------
-- 6. FY2026 budget vs actual (month x store x category)
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_budget_vs_actual_2026 AS
WITH a AS (
  SELECT DATE_FORMAT(s.sale_date, '%Y-%m') AS month, s.store_id, p.category,
         SUM(s.qty) AS actual_units, SUM(s.net_sales_cad) AS actual_net_sales,
         SUM(s.gross_profit_cad) AS actual_gross_profit,
         AVG(s.gold_rate_24k_cad) AS actual_avg_gold_rate
  FROM fact_sales s JOIN dim_products p USING (sku)
  WHERE YEAR(s.sale_date) = 2026
  GROUP BY 1, 2, 3
)
SELECT b.month, b.store_id, b.category,
       b.budget_units, a.actual_units,
       b.budget_net_sales_cad, a.actual_net_sales,
       a.actual_net_sales - b.budget_net_sales_cad         AS sales_variance,
       b.budget_gross_profit_cad, a.actual_gross_profit,
       a.actual_gross_profit - b.budget_gross_profit_cad   AS gp_variance,
       b.budget_gold_rate_24k_cad, ROUND(a.actual_avg_gold_rate, 2) AS actual_avg_gold_rate
FROM budget_fy2026_sales b
JOIN a ON a.month = b.month AND a.store_id = b.store_id AND a.category = b.category
WHERE b.month <= '2026-09';

-- ---------------------------------------------------------------------
-- 7. Stockouts: missed customer requests by category and size
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_stockouts AS
SELECT YEAR(m.request_date) AS yr, m.store_id, p.category, p.collection, p.size,
       COUNT(*)                         AS requests_out_of_stock,
       SUM(m.substituted = '1')         AS saved_by_substitute,
       SUM(m.substituted = '0')         AS lost_sales
FROM fact_missed_requests m
JOIN dim_products p ON p.sku = m.sku_requested
GROUP BY 1, 2, 3, 4, 5;
