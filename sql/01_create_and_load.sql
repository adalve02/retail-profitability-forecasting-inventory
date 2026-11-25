-- =====================================================================
-- Iva Jewellers (fictional) - MySQL 8 schema + CSV load
-- Step 1 of the project: load RAW files into staging tables.
-- Cleaning happens in step 2 (02_clean.sql) - see README "Data cleaning tasks".
--
-- Before running: put the CSV files in a folder MySQL can read, e.g.
--   SHOW VARIABLES LIKE 'secure_file_priv';   -- copy CSVs into that folder
-- or use LOAD DATA LOCAL INFILE (enable local_infile in MySQL Workbench:
--   Edit connection > Advanced > Others: OPT_LOCAL_INFILE=1)
-- Replace C:/iva/data/ below with your folder path (use forward slashes).
-- =====================================================================

CREATE DATABASE IF NOT EXISTS iva_jewellers;
USE iva_jewellers;

-- ---------- dimensions ----------
DROP TABLE IF EXISTS dim_stores;
CREATE TABLE dim_stores (
  store_id VARCHAR(10) PRIMARY KEY,
  store_name VARCHAR(60),
  city VARCHAR(40),
  open_date DATE,
  headcount INT,
  monthly_rent_cad DECIMAL(12,2)
);

DROP TABLE IF EXISTS dim_suppliers;
CREATE TABLE dim_suppliers (
  supplier_id VARCHAR(10) PRIMARY KEY,
  supplier_name VARCHAR(80),
  country VARCHAR(30),
  gold_wastage_pct DECIMAL(6,4),
  labour_cad_per_g DECIMAL(8,2),
  standard_lead_time_days INT
);

DROP TABLE IF EXISTS stg_products;          -- raw: has trailing spaces + 2 missing weights
CREATE TABLE stg_products (
  sku VARCHAR(10), design_name VARCHAR(60), category VARCHAR(40), metal_type VARCHAR(20),
  karat VARCHAR(15), purity DECIMAL(5,3), size VARCHAR(10), net_weight_g VARCHAR(20),
  making_charge_pct DECIMAL(6,4), stone_cost_cad DECIMAL(12,2), stone_retail_cad DECIMAL(12,2),
  silver_list_price_cad DECIMAL(12,2), primary_supplier_id VARCHAR(10), collection VARCHAR(40),
  launch_date DATE
);

DROP TABLE IF EXISTS dim_customers;
CREATE TABLE dim_customers (
  customer_id VARCHAR(10) PRIMARY KEY,
  home_store_id VARCHAR(10),
  city VARCHAR(40),
  first_purchase_date DATE,
  primary_segment VARCHAR(30),
  gold_savings_plan_member VARCHAR(5),
  customer_type VARCHAR(20)
);

DROP TABLE IF EXISTS gold_rates_daily;
CREATE TABLE gold_rates_daily (
  rate_date DATE PRIMARY KEY,
  gold_24k_cad_per_g DECIMAL(10,2),
  gold_22k_cad_per_g DECIMAL(10,2),
  gold_18k_cad_per_g DECIMAL(10,2),
  silver_cad_per_g DECIMAL(10,3)
);

-- ---------- facts ----------
DROP TABLE IF EXISTS stg_sales;             -- raw POS export, loaded as text on purpose
CREATE TABLE stg_sales (
  line_id VARCHAR(12), invoice_id VARCHAR(12), sale_date VARCHAR(12), store_id VARCHAR(10),
  customer_id VARCHAR(10), customer_segment VARCHAR(30), sku VARCHAR(10), qty INT,
  gold_rate_24k_cad DECIMAL(10,2), net_weight_g DECIMAL(10,2), metal_value_cad DECIMAL(12,2),
  making_charge_cad DECIMAL(12,2), stone_value_cad DECIMAL(12,2), silver_item_value_cad DECIMAL(12,2),
  discount_cad DECIMAL(12,2), net_sales_cad VARCHAR(20), hst_cad DECIMAL(12,2), cogs_cad DECIMAL(12,2),
  payment_method VARCHAR(25), promo_event VARCHAR(30)
);

DROP TABLE IF EXISTS fact_returns;
CREATE TABLE fact_returns (
  return_id VARCHAR(10) PRIMARY KEY, line_id VARCHAR(12), invoice_id VARCHAR(12), return_date DATE,
  store_id VARCHAR(10), sku VARCHAR(10), qty INT, return_type VARCHAR(20), reason VARCHAR(40),
  refund_amount_cad DECIMAL(12,2), cogs_reversed_cad DECIMAL(12,2)
);

DROP TABLE IF EXISTS fact_purchase_orders;
CREATE TABLE fact_purchase_orders (
  po_id VARCHAR(10) PRIMARY KEY, supplier_id VARCHAR(10), store_id VARCHAR(10), sku VARCHAR(10),
  order_date DATE, expected_date DATE, received_date VARCHAR(12), status VARCHAR(10), qty_ordered INT,
  gold_wastage_pct DECIMAL(6,4), gold_rate_24k_on_receipt VARCHAR(20), unit_cost_cad VARCHAR(20),
  total_cost_cad VARCHAR(20), reason VARCHAR(30)
);

DROP TABLE IF EXISTS fact_inventory_month_end;
CREATE TABLE fact_inventory_month_end (
  snapshot_date DATE, store_id VARCHAR(10), sku VARCHAR(10), on_hand_qty INT, on_order_qty INT,
  avg_unit_cost_cad DECIMAL(12,2), inventory_cost_value_cad DECIMAL(14,2), gold_rate_24k_cad DECIMAL(10,2),
  days_since_last_sale VARCHAR(10), days_since_last_receipt VARCHAR(10),
  PRIMARY KEY (snapshot_date, store_id, sku)
);

DROP TABLE IF EXISTS fact_missed_requests;
CREATE TABLE fact_missed_requests (
  request_date DATE, store_id VARCHAR(10), sku_requested VARCHAR(10), category VARCHAR(40),
  qty INT, substituted VARCHAR(5), substitute_sku VARCHAR(10)
);

DROP TABLE IF EXISTS fact_opex_monthly;
CREATE TABLE fact_opex_monthly (
  month CHAR(7), store_id VARCHAR(10), expense_category VARCHAR(40), amount_cad DECIMAL(12,2)
);

DROP TABLE IF EXISTS budget_fy2026_sales;
CREATE TABLE budget_fy2026_sales (
  month CHAR(7), store_id VARCHAR(10), category VARCHAR(40), budget_units DECIMAL(10,1),
  budget_gold_rate_24k_cad DECIMAL(10,2), budget_net_sales_cad DECIMAL(14,2),
  budget_gross_margin_pct DECIMAL(6,4), budget_gross_profit_cad DECIMAL(14,2)
);

DROP TABLE IF EXISTS budget_fy2026_opex;
CREATE TABLE budget_fy2026_opex (
  month CHAR(7), store_id VARCHAR(10), expense_category VARCHAR(40), budget_amount_cad DECIMAL(12,2)
);

-- ---------- load ----------
-- One block per file. Change the path, run all.
LOAD DATA LOCAL INFILE 'C:/iva/data/dim_stores.csv' INTO TABLE dim_stores
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 LINES;
LOAD DATA LOCAL INFILE 'C:/iva/data/dim_suppliers.csv' INTO TABLE dim_suppliers
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 LINES;
LOAD DATA LOCAL INFILE 'C:/iva/data/dim_products.csv' INTO TABLE stg_products
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 LINES;
LOAD DATA LOCAL INFILE 'C:/iva/data/dim_customers.csv' INTO TABLE dim_customers
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 LINES;
LOAD DATA LOCAL INFILE 'C:/iva/data/gold_rates_daily.csv' INTO TABLE gold_rates_daily
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 LINES;
LOAD DATA LOCAL INFILE 'C:/iva/data/fact_sales_raw.csv' INTO TABLE stg_sales
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 LINES;
LOAD DATA LOCAL INFILE 'C:/iva/data/fact_returns.csv' INTO TABLE fact_returns
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 LINES;
LOAD DATA LOCAL INFILE 'C:/iva/data/fact_purchase_orders.csv' INTO TABLE fact_purchase_orders
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 LINES;
LOAD DATA LOCAL INFILE 'C:/iva/data/fact_inventory_month_end.csv' INTO TABLE fact_inventory_month_end
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 LINES;
LOAD DATA LOCAL INFILE 'C:/iva/data/fact_missed_requests.csv' INTO TABLE fact_missed_requests
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 LINES;
LOAD DATA LOCAL INFILE 'C:/iva/data/fact_opex_monthly.csv' INTO TABLE fact_opex_monthly
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 LINES;
LOAD DATA LOCAL INFILE 'C:/iva/data/budget_fy2026_sales.csv' INTO TABLE budget_fy2026_sales
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 LINES;
LOAD DATA LOCAL INFILE 'C:/iva/data/budget_fy2026_opex.csv' INTO TABLE budget_fy2026_opex
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 LINES;

-- ---------- quick checks (expected values in README) ----------
SELECT 'stg_sales' t, COUNT(*) n FROM stg_sales
UNION ALL SELECT 'stg_products', COUNT(*) FROM stg_products
UNION ALL SELECT 'fact_purchase_orders', COUNT(*) FROM fact_purchase_orders
UNION ALL SELECT 'fact_inventory_month_end', COUNT(*) FROM fact_inventory_month_end;
