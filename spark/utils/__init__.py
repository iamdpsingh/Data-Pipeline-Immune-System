"""Spark utility modules for the Data Pipeline Immune System."""

try:
    from spark.utils.quarantine import QualityRule, QuarantineRouter
    from spark.utils.spark_session import get_spark_session

    __all__ = ["get_spark_session", "QuarantineRouter", "QualityRule"]
except ImportError:
    __all__ = []
