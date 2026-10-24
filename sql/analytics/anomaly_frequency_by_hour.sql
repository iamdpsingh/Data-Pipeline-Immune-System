-- Hourly Anomaly Detection Distribution
SELECT
  EXTRACT(HOUR FROM detected_at) AS hour_of_day,
  severity,
  COUNT(1) AS incident_count,
  AVG(confidence) AS avg_detection_confidence
FROM `data-pipeline-immune-system.dpis_dev.incidents`
GROUP BY 1, 2
ORDER BY 1, 2;
