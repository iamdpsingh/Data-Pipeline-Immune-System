-- Intraday Null Rate Spike Sensor
SELECT
  DATE(_ingested_at) AS ingestion_date,
  COUNT(1) AS total_rows,
  COUNTIF(JSON_VALUE(_raw_payload, '$.customer_id') IS NULL) AS null_customer_ids,
  ROUND(SAFE_DIVIDE(COUNTIF(JSON_VALUE(_raw_payload, '$.customer_id') IS NULL), COUNT(1)) * 100, 2) AS null_rate_pct
FROM `data-pipeline-immune-system.dpis_bronze_dev.orders_raw`
GROUP BY 1
HAVING null_rate_pct > 2.0;
