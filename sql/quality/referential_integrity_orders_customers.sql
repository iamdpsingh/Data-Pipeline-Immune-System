-- Referential Integrity Verification (Orders -> Customers)
SELECT
  o.order_id,
  o.customer_id,
  o.order_timestamp
FROM `data-pipeline-immune-system.dpis_silver_dev.orders` o
LEFT JOIN `data-pipeline-immune-system.dpis_silver_dev.customers` c
  ON o.customer_id = c.customer_id
WHERE c.customer_id IS NULL;
