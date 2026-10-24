# ADR-011: PySpark on Google Cloud Dataproc Serverless

## Status: Accepted (In Production)

## Context
High-volume data transformations (e.g. processing 10 million transactions daily, deduplicating high-cardinality event streams, computing complex joins between orders and customer reference tables) exceed the memory and compute capacity of standard single-node Python workers.

Traditional managed Spark deployments (such as persistent Dataproc or EMR clusters) introduce:
1. Significant idle compute and master-node VM costs when jobs are not running.
2. Complex cluster sizing and auto-scaling configuration tuning.
3. Operating system and Hadoop dependency maintenance overhead.

## Decision
We standardize all large-scale Lakehouse batch transformations and quarantine extraction jobs on **PySpark running on Google Cloud Dataproc Serverless for Spark**:

1. **Serverless Execution Model**:
   - Jobs are submitted as self-contained Spark workloads via the Dataproc Batches API (`gcloud dataproc batches submit pyspark`).
   - Google Cloud automatically provisions, scales, and tears down the underlying compute infrastructure per workload.
   - Billing is per-second of actual Spark CPU and memory usage, with zero idle cluster cost.

2. **Standardized PySpark Transformation Logic (`spark/`)**:
   - Medallion transitions (Bronze to Silver, Silver to Gold) are implemented as deterministic Spark Dataframe transformations.
   - Built-in schema enforcement validates incoming JSON/Parquet against strict schemas before writing to BigQuery tables using the `spark-bigquery-connector`.

3. **Graceful Local Development Decoupling**:
   - To ensure local testing, unit tests, and CI/CD pipelines run rapidly without requiring a multi-gigabyte Java Virtual Machine or PySpark runtime installed, all Spark modules ([`spark/utils/__init__.py`](file:///Volumes/Work/daemons-lab/d.automation/Data%20Pipeline%20Immune%20System/spark/utils/__init__.py)) use dynamic, conditional import handling (`try...except ImportError`).
   - Local unit tests mock or stub Spark sessions while integration tests run against ephemeral Dataproc batches or test datasets.

## Consequences

### Positive
- **Elastic Scale**: Seamlessly scales from thousands to tens of millions of records per batch without manual cluster provisioning.
- **Cost Optimization**: Eliminates 100% of idle cluster VM billing; compute expenses scale linearly with actual processed record volume.
- **Fast Developer Workflow**: Local unit tests execute in seconds without JVM or local Hadoop daemon dependencies.

### Negative / Trade-Offs
- Cold start provisioning latency: Initial Dataproc Serverless batch startup takes approximately 45s-90s to allocate Spark worker containers.
- Debugging distributed Spark failures requires inspecting Google Cloud Logging and Spark UI history servers rather than a local terminal debugger.
