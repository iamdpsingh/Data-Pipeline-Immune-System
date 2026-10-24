-- ==============================================================================
-- Data Pipeline Immune System — Data Quality Verification Queries
-- Dataset: dpis_{environment}
-- ==============================================================================

-- 1. Silver Orders Completeness & Null Ratio Check
SELECT
  CURRENT_TIMESTAMP() AS check_timestamp,
  'orders' AS pipeline_id,
  'dpis_silver.orders' AS table_name,
  'COMPLETENESS' AS check_type,
  'null_check_critical_fields' AS check_name,
  COUNT(1) AS total_rows,
  COUNTIF(order_id IS NULL) AS null_order_id_count,
  COUNTIF(customer_id IS NULL) AS null_customer_id_count,
  COUNTIF(order_amount IS NULL) AS null_order_amount_count,
  ROUND(SAFE_DIVIDE(COUNTIF(customer_id IS NULL), COUNT(1)), 4) AS customer_id_null_ratio,
  ROUND(SAFE_DIVIDE(COUNTIF(order_amount IS NULL), COUNT(1)), 4) AS order_amount_null_ratio
FROM
  `{project}.{dataset}.orders`
WHERE
  DATE(order_date) = CURRENT_DATE();

-- 2. Uniqueness & Duplicate Primary Key Detection
SELECT
  CURRENT_TIMESTAMP() AS check_timestamp,
  'orders' AS pipeline_id,
  'dpis_silver.orders' AS table_name,
  'UNIQUENESS' AS check_type,
  'duplicate_check_order_id' AS check_name,
  order_id,
  COUNT(1) AS duplicate_count
FROM
  `{project}.{dataset}.orders`
WHERE
  DATE(order_date) = CURRENT_DATE()
GROUP BY
  order_id
HAVING
  COUNT(1) > 1;

-- 3. Data Freshness & Ingestion Latency Check
SELECT
  CURRENT_TIMESTAMP() AS check_timestamp,
  'orders' AS pipeline_id,
  'dpis_silver.orders' AS table_name,
  'FRESHNESS' AS check_type,
  'max_ingestion_delay' AS check_name,
  MAX(updated_at) AS latest_record_timestamp,
  TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), MAX(updated_at), MINUTE) AS latency_minutes,
  CASE
    WHEN TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), MAX(updated_at), MINUTE) > 120 THEN 'CRITICAL'
    WHEN TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), MAX(updated_at), MINUTE) > 60 THEN 'WARNING'
    ELSE 'HEALTHY'
  END AS freshness_status
FROM
  `{project}.{dataset}.orders`;
