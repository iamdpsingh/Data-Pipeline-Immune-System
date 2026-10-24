# PySpark PII Crypto Masking Utility
from pyspark.sql import Column
from pyspark.sql.functions import sha2, concat_ws, lit

def mask_pii_column(col_expr: Column, salt: str = "dpis-lakehouse-salt") -> Column:
    return sha2(concat_ws(":", col_expr, lit(salt)), 256)
