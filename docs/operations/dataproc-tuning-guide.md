# Dataproc Serverless PySpark Performance Tuning
## Key Configurations:
- `spark.dynamicAllocation.enabled=true`
- `spark.sql.shuffle.partitions=200`
- `spark.executor.memory=4g`
- `spark.driver.memory=2g`
- `spark.sql.adaptive.enabled=true`
