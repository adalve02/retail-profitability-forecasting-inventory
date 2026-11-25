-- =====================================================================
-- Step 2: Clean the raw data
-- Run AFTER 01_create_and_load.sql.
-- Each block fixes one issue from the README "Data-cleaning tasks" table.
-- Raw staging tables (stg_*) are never changed; the clean tables are new.
-- =====================================================================
USE iva_jewellers;

-- ---------------------------------------------------------------------
-- 1. PRODUCTS: trim category spaces (issue 7), fill missing weights (issue 8)
-- Missing weight fix: use the actual weight sold per unit from the sales
-- lines (most accurate). If a SKU never sold, fall back to the average of
-- the same design's other sizes.
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS dim_products;
CREATE TABLE dim_products AS
SELECT
  p.sku,
  p.design_name,
  TRIM(p.category)                         AS category,
  p.metal_type,
  p.karat,
  p.purity,
  NULLIF(TRIM(p.size), '')                 AS size,
  COALESCE(
    CAST(NULLIF(p.net_weight_g, '') AS DECIMAL(10,2)),
    (SELECT ROUND(AVG(s.net_weight_g / s.qty), 2) FROM stg_sales s WHERE s.sku = p.sku),
    (SELECT ROUND(AVG(CAST(p2.net_weight_g AS DECIMAL(10,2))), 2)
       FROM stg_products p2
      WHERE p2.design_name = p.design_name AND p2.net_weight_g <> '')
  )                                        AS net_weight_g,
  p.making_charge_pct,
  p.stone_cost_cad,
  p.stone_retail_cad,
  p.silver_list_price_cad,
  p.primary_supplier_id,
  p.collection,
  p.launch_date
FROM stg_products p;
ALTER TABLE dim_products ADD PRIMARY KEY (sku);

-- ---------------------------------------------------------------------
-- 2. SALES: fix store codes (2), dates (3), net sales (4), segment case (5),
--    walk-ins (6), then remove duplicate lines (1).
-- Fix formats FIRST, then dedupe - otherwise a duplicate whose store code
-- was messy would look "different" and survive.
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS fact_sales;
CREATE TABLE fact_sales AS
WITH fixed AS (
  SELECT
    line_id,
    invoice_id,
    CASE WHEN sale_date LIKE '%/%'
         THEN STR_TO_DATE(sale_date, '%d/%m/%Y')          -- DD/MM/YYYY rows
         ELSE STR_TO_DATE(sale_date, '%Y-%m-%d') END       AS sale_date,
    UPPER(TRIM(store_id))                                  AS store_id,
    COALESCE(NULLIF(TRIM(customer_id), ''), 'WALK-IN')     AS customer_id,
    CASE WHEN LOWER(customer_segment) = 'everyday' THEN 'Everyday'
         ELSE customer_segment END                         AS customer_segment,
    sku,
    qty,
    gold_rate_24k_cad,
    net_weight_g,
    metal_value_cad,
    making_charge_cad,
    stone_value_cad,
    silver_item_value_cad,
    discount_cad,
    COALESCE(CAST(NULLIF(net_sales_cad, '') AS DECIMAL(12,2)),
             metal_value_cad + making_charge_cad + stone_value_cad
             + silver_item_value_cad - discount_cad)        AS net_sales_cad,
    hst_cad,
    cogs_cad,
    payment_method,
    TRIM(TRAILING '\r' FROM promo_event)                   AS promo_event
  FROM stg_sales
),
ranked AS (
  SELECT f.*, ROW_NUMBER() OVER (PARTITION BY line_id ORDER BY line_id) AS rn
  FROM fixed f
)
SELECT
  line_id, invoice_id, sale_date, store_id, customer_id, customer_segment, sku, qty,
  gold_rate_24k_cad, net_weight_g, metal_value_cad, making_charge_cad, stone_value_cad,
  silver_item_value_cad, discount_cad, net_sales_cad, hst_cad, cogs_cad,
  net_sales_cad - cogs_cad AS gross_profit_cad,
  payment_method, promo_event
FROM ranked
WHERE rn = 1;
ALTER TABLE fact_sales ADD PRIMARY KEY (line_id);
CREATE INDEX ix_sales_date  ON fact_sales (sale_date);
CREATE INDEX ix_sales_sku   ON fact_sales (sku);

-- ---------------------------------------------------------------------
-- 3. PURCHASE ORDERS: blank receipt fields -> NULL (issue 9: open POs)
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS fact_po;
CREATE TABLE fact_po AS
SELECT
  po_id, supplier_id, store_id, sku, order_date, expected_date,
  CAST(NULLIF(received_date, '') AS DATE)                    AS received_date,
  status, qty_ordered, gold_wastage_pct,
  CAST(NULLIF(gold_rate_24k_on_receipt, '') AS DECIMAL(10,2)) AS gold_rate_24k_on_receipt,
  CAST(NULLIF(unit_cost_cad, '') AS DECIMAL(12,2))            AS unit_cost_cad,
  CAST(NULLIF(total_cost_cad, '') AS DECIMAL(14,2))           AS total_cost_cad,
  -- lead-time KPIs only make sense for received POs
  CASE WHEN status = 'Received'
       THEN DATEDIFF(CAST(received_date AS DATE), order_date) END AS actual_lead_days,
  CASE WHEN status = 'Received'
       THEN CAST(received_date AS DATE) <= expected_date END    AS on_time_flag
FROM fact_purchase_orders;
ALTER TABLE fact_po ADD PRIMARY KEY (po_id);

-- ---------------------------------------------------------------------
-- 4. INVENTORY: blank "days since" -> NULL (never sold / never received)
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS fact_inventory;
CREATE TABLE fact_inventory AS
SELECT
  snapshot_date, store_id, sku, on_hand_qty, on_order_qty, avg_unit_cost_cad,
  inventory_cost_value_cad, gold_rate_24k_cad,
  CAST(NULLIF(days_since_last_sale, '') AS DECIMAL(8,0))                     AS days_since_last_sale,
  CAST(NULLIF(TRIM(TRAILING '\r' FROM days_since_last_receipt), '') AS DECIMAL(8,0)) AS days_since_last_receipt
FROM fact_inventory_month_end;

-- ---------------------------------------------------------------------
-- 5. Small fixes: True/False text -> 1/0
-- ---------------------------------------------------------------------
UPDATE dim_customers
   SET gold_savings_plan_member = CASE WHEN gold_savings_plan_member = 'True' THEN '1' ELSE '0' END;
UPDATE fact_missed_requests
   SET substituted = CASE WHEN substituted = 'True' THEN '1' ELSE '0' END,
       substitute_sku = NULLIF(TRIM(TRAILING '\r' FROM substitute_sku), '');

-- =====================================================================
-- CHECKS - every number on the right should match the "expected" column
-- =====================================================================
SELECT 'sales rows after cleaning'          AS check_name, COUNT(*) AS result, 34633 AS expected FROM fact_sales
UNION ALL SELECT 'duplicate line_ids left',  COUNT(*) - COUNT(DISTINCT line_id), 0 FROM fact_sales
UNION ALL SELECT 'bad store codes left',     SUM(store_id NOT IN ('ST01','ST02','ST03')), 0 FROM fact_sales
UNION ALL SELECT 'NULL sale dates',          SUM(sale_date IS NULL), 0 FROM fact_sales
UNION ALL SELECT 'NULL net sales',           SUM(net_sales_cad IS NULL), 0 FROM fact_sales
UNION ALL SELECT 'segments (should be 5)',   COUNT(DISTINCT customer_segment), 5 FROM fact_sales
UNION ALL SELECT 'categories (should be 10)',COUNT(DISTINCT category), 10 FROM dim_products
UNION ALL SELECT 'products missing weight',  SUM(net_weight_g IS NULL), 0 FROM dim_products
UNION ALL SELECT 'sales SKUs not in products',
          (SELECT COUNT(*) FROM fact_sales s LEFT JOIN dim_products p USING (sku) WHERE p.sku IS NULL), 0
UNION ALL SELECT 'open POs',                 SUM(status = 'Open'), 100 FROM fact_po;
