# PySpark Transformation Job: Payments Bronze -> Silver Conformed
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, current_timestamp
from pyspark.sql.types import StructType, StringType, DoubleType

def transform_payments_silver(spark: SparkSession, bronze_path: str, silver_path: str):
    schema = StructType().add("payment_id", StringType()).add("order_id", StringType()).add("amount", DoubleType()).add("currency", StringType()).add("status", StringType())
    df_bronze = spark.read.parquet(bronze_path)
    df_parsed = df_bronze.select(from_json(col("_raw_payload"), schema).alias("p")).select("p.*")
    df_valid = df_parsed.filter((col("amount") > 0) & (col("payment_id").isNotNull())).withColumn("processed_at", current_timestamp())
    df_valid.write.mode("append").parquet(silver_path)

if __name__ == "__main__":
    spark = SparkSession.builder.appName("PaymentsSilverTransformation").getOrCreate()
    transform_payments_silver(spark, "gs://dpis-bronze-data-pipeline-immune-system/payments/", "gs://dpis-silver-data-pipeline-immune-system/payments/")
