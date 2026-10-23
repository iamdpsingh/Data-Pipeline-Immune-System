# ==============================================================================
# Data Pipeline Immune System — Bronze Raw Ingestion Job
# ==============================================================================
"""Ingests raw orders files from GCS source bucket into the Bronze raw lake tier.

Appends lineage metadata (_source_file, _ingested_at, _run_id) without altering
raw field values, guaranteeing an immutable audit trail of landing payloads.
"""

from __future__ import annotations

import argparse
import logging
from datetime import datetime, timezone

from pyspark.sql import functions as F
from pyspark.sql.types import (
    DoubleType,
    IntegerType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

from spark.utils.spark_session import get_spark_session

logger = logging.getLogger(__name__)


SOURCE_ORDERS_SCHEMA = StructType([
    StructField("order_id", StringType(), False),
    StructField("customer_id", StringType(), False),
    StructField("order_date", StringType(), False),
    StructField("status", StringType(), False),
    StructField("total_amount", DoubleType(), False),
    StructField("currency", StringType(), False),
    StructField("items_count", IntegerType(), True),
    StructField("created_at", StringType(), True),
])


def run_bronze_ingestion(
    source_path: str,
    target_table_or_path: str,
    run_id: str,
    write_format: str = "parquet",
) -> int:
    """Executes bronze ingestion from raw files.

    Args:
        source_path: GCS or local directory containing input JSON/CSV files.
        target_table_or_path: Destination BigQuery table or parquet staging path.
        run_id: Unique pipeline run identifier for traceability.
        write_format: 'bigquery' or 'parquet'

    Returns:
        Total row count ingested.
    """
    spark = get_spark_session(app_name=f"BronzeIngest-Orders-{run_id}")

    logger.info("Reading source orders from: %s", source_path)
    raw_df = spark.read.schema(SOURCE_ORDERS_SCHEMA).json(source_path)

    ingested_at = datetime.now(timezone.utc).isoformat()

    bronze_df = (
        raw_df
        .withColumn("_source_file", F.input_file_name())
        .withColumn("_ingested_at", F.lit(ingested_at).cast(TimestampType()))
        .withColumn("_run_id", F.lit(run_id))
    )

    row_count = bronze_df.count()
    logger.info("Ingested %d raw records into Bronze (run %s)", row_count, run_id)

    if write_format == "bigquery":
        bronze_df.write.format("bigquery").option(
            "table", target_table_or_path
        ).mode("append").save()
    else:
        bronze_df.write.mode("append").parquet(target_table_or_path)

    return row_count


def main() -> None:
    parser = argparse.ArgumentParser(description="Bronze orders ingestion job.")
    parser.add_argument("--source-path", required=True, help="Input GCS/local path")
    parser.add_argument("--target", required=True, help="Target BigQuery table or storage path")
    parser.add_argument("--run-id", required=True, help="Execution Run ID")
    parser.add_argument("--format", default="parquet", choices=["parquet", "bigquery"])
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    run_bronze_ingestion(args.source_path, args.target, args.run_id, args.format)


if __name__ == "__main__":
    main()
