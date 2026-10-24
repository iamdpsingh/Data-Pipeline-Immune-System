# ==============================================================================
# Data Pipeline Immune System — Silver Conformed Transformation Job
# ==============================================================================
"""Transforms Bronze raw orders into validated, deduplicated, standardized Silver data.

Applies:
- Deduplication over order_id selecting latest timestamp.
- Currency normalization to USD.
- ADR-008 Quarantine routing: invalid rows are diverted to the dead-letter quarantine
  store, preventing downstream pollution while permitting clean records to advance.
"""

from __future__ import annotations

import argparse
import logging
from datetime import UTC, datetime

from pyspark.sql import Window
from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType, TimestampType

from spark.utils.quarantine import QualityRule, QuarantineRouter
from spark.utils.spark_session import get_spark_session

logger = logging.getLogger(__name__)


def build_silver_transformation(
    bronze_source: str,
    silver_target: str,
    quarantine_target: str,
    run_id: str,
    pipeline_id: str = "orders",
    write_format: str = "parquet",
) -> dict:
    """Executes silver cleaning, deduplication, and quarantine routing."""
    spark = get_spark_session(app_name=f"SilverTransform-Orders-{run_id}")

    logger.info("Reading bronze records from: %s", bronze_source)
    if write_format == "bigquery":
        df = spark.read.format("bigquery").option("table", bronze_source).load()
    else:
        df = spark.read.parquet(bronze_source)

    # 1. Deduplication on order_id
    window_spec = Window.partitionBy("order_id").orderBy(
        F.col("order_date").desc(), F.col("_ingested_at").desc()
    )
    deduped_df = (
        df.withColumn("_row_num", F.row_number().over(window_spec))
        .filter(F.col("_row_num") == 1)
        .drop("_row_num")
    )

    # 2. Standardization: Currency normalization to USD
    exchange_rates = {
        "USD": 1.0,
        "EUR": 1.08,
        "GBP": 1.28,
        "CAD": 0.74,
        "AUD": 0.65,
    }

    rate_expr = F.lit(1.0)
    for curr, rate in exchange_rates.items():
        rate_expr = F.when(F.col("currency") == curr, F.lit(rate)).otherwise(rate_expr)

    standardized_df = (
        deduped_df.withColumn("order_timestamp", F.to_timestamp("order_date"))
        .withColumn("order_date_partition", F.to_date("order_date"))
        .withColumn("original_currency", F.col("currency"))
        .withColumn(
            "total_amount_usd",
            F.round(F.col("total_amount") * rate_expr, 2).cast(DoubleType()),
        )
        .withColumn(
            "_processed_at",
            F.lit(datetime.now(UTC).isoformat()).cast(TimestampType()),
        )
        .withColumn("_run_id", F.lit(run_id))
    )

    # 3. Quality Rules for Quarantine Routing (ADR-008)
    rules = [
        QualityRule(
            rule_name="NON_NULL_ORDER_ID",
            condition=F.col("order_id").isNotNull()
            & (F.length(F.trim("order_id")) > 0),
            failure_reason="order_id is null or blank",
        ),
        QualityRule(
            rule_name="NON_NULL_CUSTOMER_ID",
            condition=F.col("customer_id").isNotNull()
            & (F.length(F.trim("customer_id")) > 0),
            failure_reason="customer_id is null or blank",
        ),
        QualityRule(
            rule_name="POSITIVE_AMOUNT",
            condition=F.col("total_amount_usd").isNotNull()
            & (F.col("total_amount_usd") > 0.0),
            failure_reason="total_amount_usd is negative or zero",
        ),
        QualityRule(
            rule_name="VALID_STATUS",
            condition=F.col("status").isin(
                "PENDING", "PROCESSING", "COMPLETED", "CANCELLED", "REFUNDED"
            ),
            failure_reason="status is not in allowable lifecycle states",
        ),
    ]

    router = QuarantineRouter(
        pipeline_id=pipeline_id,
        run_id=run_id,
        rules=rules,
        max_quarantine_pct=0.05,
    )

    valid_df, quarantine_df, ratio = router.route(standardized_df)

    valid_count = valid_df.count()
    quarantine_count = quarantine_df.count()

    logger.info("Writing %d valid records to Silver: %s", valid_count, silver_target)
    if write_format == "bigquery":
        valid_df.write.format("bigquery").option("table", silver_target).mode(
            "append"
        ).save()
    else:
        valid_df.write.mode("append").partitionBy("order_date_partition").parquet(
            silver_target
        )

    if quarantine_count > 0:
        logger.warning(
            "Writing %d quarantined records to dead-letter: %s (%.2f%%)",
            quarantine_count,
            quarantine_target,
            ratio * 100,
        )
        if write_format == "bigquery":
            quarantine_df.write.format("bigquery").option(
                "table", quarantine_target
            ).mode("append").save()
        else:
            quarantine_df.write.mode("append").parquet(quarantine_target)

    return {
        "valid_count": valid_count,
        "quarantine_count": quarantine_count,
        "quarantine_ratio": ratio,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Silver transformation with quarantine."
    )
    parser.add_argument("--bronze-source", required=True)
    parser.add_argument("--silver-target", required=True)
    parser.add_argument("--quarantine-target", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--pipeline-id", default="orders")
    parser.add_argument("--format", default="parquet", choices=["parquet", "bigquery"])
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    build_silver_transformation(
        bronze_source=args.bronze_source,
        silver_target=args.silver_target,
        quarantine_target=args.quarantine_target,
        run_id=args.run_id,
        pipeline_id=args.pipeline_id,
        write_format=args.format,
    )


if __name__ == "__main__":
    main()
