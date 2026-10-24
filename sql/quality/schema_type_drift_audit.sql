-- BigQuery INFORMATION_SCHEMA Drift Audit
SELECT
  table_name,
  column_name,
  data_type,
  is_nullable
FROM `data-pipeline-immune-system.dpis_silver_dev.INFORMATION_SCHEMA.COLUMNS`
ORDER BY table_name, ordinal_position;
