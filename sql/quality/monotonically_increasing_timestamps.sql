-- Timestamp Monotony & Future-Date Guard
SELECT
  order_id,
  order_timestamp,
  CURRENT_TIMESTAMP() AS evaluation_time
FROM `data-pipeline-immune-system.dpis_silver_dev.orders`
WHERE order_timestamp > CURRENT_TIMESTAMP()
   OR order_timestamp < TIMESTAMP('2020-01-01');
