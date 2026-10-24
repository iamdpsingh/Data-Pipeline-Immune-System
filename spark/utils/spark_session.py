# ==============================================================================
# Data Pipeline Immune System — PySpark Session Provider
# ==============================================================================
"""Spark session factory supporting local execution and Dataproc GCP integration.

Configures Google Cloud Storage and BigQuery connectors when running on GCP,
while allowing local mock execution for unit tests and local development.
"""

from __future__ import annotations

import logging
import os

from pyspark.sql import SparkSession

logger = logging.getLogger(__name__)


def get_spark_session(
    app_name: str = "DataPipelineImmuneSystem",
    master: str | None = None,
    enable_bigquery: bool = True,
) -> SparkSession:
    """Builds and returns a configured PySpark session.

    Args:
        app_name: Name of the Spark application.
        master: Spark master URL (e.g., 'local[*]', 'yarn').
        enable_bigquery: If True, adds BigQuery connector configs.
    """
    builder = (
        SparkSession.builder.appName(app_name)
        .config("spark.sql.adaptive.enabled", "true")
        .config("spark.sql.shuffle.partitions", "8")
        .config("spark.sql.session.timeZone", "UTC")
    )

    if master:
        builder = builder.master(master)
    elif "SPARK_MASTER" in os.environ:
        builder = builder.master(os.environ["SPARK_MASTER"])
    else:
        # Default to local for dev/test execution
        builder = builder.master("local[*]")

    if enable_bigquery:
        # BigQuery connector configuration
        builder = builder.config("viewsEnabled", "true").config(
            "materializationDataset",
            os.getenv("BQ_MATERIALIZATION_DATASET", "dpis_dev"),
        )

    spark = builder.getOrCreate()
    logger.info(
        "Initialized SparkSession: %s (master: %s)", app_name, spark.sparkContext.master
    )
    return spark
