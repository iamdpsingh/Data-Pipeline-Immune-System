# PySpark Transformation Job: Shipments Bronze -> Silver Conformed
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, current_timestamp
from pyspark.sql.types import StructType, StringType

def transform_shipments_silver(spark: SparkSession, bronze_path: str, silver_path: str):
    schema = StructType().add("tracking_number", StringType()).add("order_id", StringType()).add("carrier", StringType()).add("status", StringType())
    df_bronze = spark.read.parquet(bronze_path)
    df_parsed = df_bronze.select(from_json(col("_raw_payload"), schema).alias("s")).select("s.*")
    df_clean = df_parsed.filter(col("tracking_number").isNotNull()).withColumn("updated_at", current_timestamp())
    df_clean.write.mode("append").parquet(silver_path)

if __name__ == "__main__":
    spark = SparkSession.builder.appName("ShipmentsSilverTransformation").getOrCreate()
    transform_shipments_silver(spark, "gs://dpis-bronze-data-pipeline-immune-system/shipments/", "gs://dpis-silver-data-pipeline-immune-system/shipments/")
