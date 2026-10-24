-- Mean Time To Detect (MTTD) by Pipeline
SELECT
  pipeline_id,
  AVG(TIMESTAMP_DIFF(detected_at, pipeline_run_started_at, SECOND)) AS avg_mttd_seconds,
  MAX(TIMESTAMP_DIFF(detected_at, pipeline_run_started_at, SECOND)) AS max_mttd_seconds
FROM `data-pipeline-immune-system.dpis_dev.incidents`
GROUP BY 1;
