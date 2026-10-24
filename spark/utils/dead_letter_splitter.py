# PySpark Dead-Letter Quarantine Splitter
from pyspark.sql import DataFrame
from pyspark.sql.functions import col

def split_valid_and_quarantine(df: DataFrame, condition_expr) -> tuple[DataFrame, DataFrame]:
    df_valid = df.filter(condition_expr)
    df_quarantine = df.filter(~condition_expr)
    return df_valid, df_quarantine
