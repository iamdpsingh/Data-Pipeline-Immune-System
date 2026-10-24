# PySpark Ingestion Job: Customers Stream -> Bronze Raw Landing
from pyspark.sql import SparkSession
from pyspark.sql.functions import current_timestamp, input_file_name, to_json, struct

def ingest_customers_bronze(spark: SparkSession, source_path: str, bronze_path: str):
    df_raw = spark.read.json(source_path)
    df_bronze = df_raw.select(
        to_json(struct("*")).alias("_raw_payload"),
        current_timestamp().alias("_ingested_at"),
        input_file_name().alias("_source_file")
    )
    df_bronze.write.mode("append").parquet(bronze_path)

if __name__ == "__main__":
    spark = SparkSession.builder.appName("CustomersBronzeIngestion").getOrCreate()
    ingest_customers_bronze(spark, "gs://dpis-source-data-pipeline-immune-system/customers/", "gs://dpis-bronze-data-pipeline-immune-system/customers/")
