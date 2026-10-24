# PySpark Dynamic Partition Pruning Filter
from pyspark.sql import DataFrame
from pyspark.sql.functions import col


def prune_processed_partitions(
    df: DataFrame, partition_col: str, active_date_str: str
) -> DataFrame:
    return df.filter(col(partition_col) == active_date_str)
