# PySpark Transformation Job: Customers Bronze -> Silver Conformed
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, current_timestamp, from_json, sha2
from pyspark.sql.types import StringType, StructType


def transform_customers_silver(spark: SparkSession, bronze_path: str, silver_path: str):
    schema = (
        StructType()
        .add("customer_id", StringType())
        .add("email", StringType())
        .add("country", StringType())
        .add("tier", StringType())
    )
    df_bronze = spark.read.parquet(bronze_path)
    df_parsed = df_bronze.select(
        from_json(col("_raw_payload"), schema).alias("data")
    ).select("data.*")
    df_clean = (
        df_parsed.filter(col("customer_id").isNotNull())
        .withColumn("email_hash", sha2(col("email"), 256))
        .drop("email")
        .withColumn("updated_at", current_timestamp())
    )
    df_clean.write.mode("overwrite").parquet(silver_path)


if __name__ == "__main__":
    spark = SparkSession.builder.appName("CustomersSilverTransformation").getOrCreate()
    transform_customers_silver(
        spark,
        "gs://dpis-bronze-data-pipeline-immune-system/customers/",
        "gs://dpis-silver-data-pipeline-immune-system/customers/",
    )
