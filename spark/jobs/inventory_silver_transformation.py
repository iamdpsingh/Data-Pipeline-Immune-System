# PySpark Transformation Job: Inventory Bronze -> Silver Balances
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, current_timestamp
from pyspark.sql.types import StructType, StringType, IntegerType

def transform_inventory_silver(spark: SparkSession, bronze_path: str, silver_path: str):
    schema = StructType().add("sku", StringType()).add("warehouse_id", StringType()).add("quantity_on_hand", IntegerType()).add("quantity_reserved", IntegerType())
    df_bronze = spark.read.parquet(bronze_path)
    df_parsed = df_bronze.select(from_json(col("_raw_payload"), schema).alias("inv")).select("inv.*")
    df_clean = df_parsed.filter(col("quantity_on_hand") >= 0).withColumn("last_audit_time", current_timestamp())
    df_clean.write.mode("overwrite").parquet(silver_path)

if __name__ == "__main__":
    spark = SparkSession.builder.appName("InventorySilverTransformation").getOrCreate()
    transform_inventory_silver(spark, "gs://dpis-bronze-data-pipeline-immune-system/inventory/", "gs://dpis-silver-data-pipeline-immune-system/inventory/")
