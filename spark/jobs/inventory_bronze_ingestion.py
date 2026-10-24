# PySpark Ingestion Job: Warehouse Inventory Snapshots -> Bronze
from pyspark.sql import SparkSession
from pyspark.sql.functions import current_date, to_json, struct

def ingest_inventory_bronze(spark: SparkSession, source_path: str, bronze_path: str):
    df_raw = spark.read.json(source_path)
    df_bronze = df_raw.select(
        to_json(struct("*")).alias("_raw_payload"),
        current_date().alias("_snapshot_date")
    )
    df_bronze.write.mode("append").partitionBy("_snapshot_date").parquet(bronze_path)

if __name__ == "__main__":
    spark = SparkSession.builder.appName("InventoryBronzeIngestion").getOrCreate()
    ingest_inventory_bronze(spark, "gs://dpis-source-data-pipeline-immune-system/inventory/", "gs://dpis-bronze-data-pipeline-immune-system/inventory/")
