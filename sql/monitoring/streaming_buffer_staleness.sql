-- Streaming Buffer Lag Inspection
SELECT
  table_name,
  SUM(total_rows) AS uncommitted_streaming_rows
FROM `data-pipeline-immune-system.dpis_bronze_dev.INFORMATION_SCHEMA.PARTITIONS`
WHERE partition_id = '__UNPARTITIONED__'
GROUP BY 1;
