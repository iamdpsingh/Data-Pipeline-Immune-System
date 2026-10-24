-- BigQuery Partition Skew & Data Volume Distribution
SELECT
  partition_id,
  total_rows,
  total_logical_bytes / 1024 / 1024 AS size_mb,
  last_modified_time
FROM `data-pipeline-immune-system.dpis_silver_dev.INFORMATION_SCHEMA.PARTITIONS`
WHERE table_name = 'orders'
ORDER BY total_rows DESC;
