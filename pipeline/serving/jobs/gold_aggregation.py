"""
Gold aggregation job.

Reads the current Iceberg silver snapshot, applies a 1-minute tumbling window
aggregation per sensor + location, and upserts results into the gold table.

This is intentionally batch-style so each Airflow run materializes the current
state instead of waiting for a streaming watermark to close windows.
"""

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

SILVER_TABLE = "iotstream.silver.sensor_clean"
GOLD_TABLE = "iotstream.gold.sensor_metrics_1min"
WINDOW_DURATION = "1 minute"


def ensure_gold_table(spark: SparkSession) -> None:
    spark.sql(
        """
        CREATE TABLE IF NOT EXISTS iotstream.gold.sensor_metrics_1min (
            window_start      TIMESTAMP NOT NULL,
            window_end        TIMESTAMP NOT NULL,
            sensor_id         STRING    NOT NULL,
            location          STRING,
            avg_temperature   DOUBLE,
            min_temperature   DOUBLE,
            max_temperature   DOUBLE,
            avg_humidity      DOUBLE,
            avg_pressure      DOUBLE,
            avg_ph            DOUBLE,
            event_count       BIGINT,
            active_count      BIGINT,
            degraded_count    BIGINT,
            offline_count     BIGINT,
            _processed_at     TIMESTAMP NOT NULL
        )
        USING iceberg
        PARTITIONED BY (days(window_start))
        TBLPROPERTIES (
            'write.format.default' = 'parquet',
            'write.parquet.compression-codec' = 'snappy'
        )
        """
    )


def main() -> None:
    spark = SparkSession.builder.appName("iotstream-gold-aggregation").getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    ensure_gold_table(spark)

    silver_df = spark.read.format("iceberg").load(SILVER_TABLE)

    aggregated = (
        silver_df.groupBy(
            F.window("timestamp", WINDOW_DURATION),
            F.col("sensor_id"),
            F.col("location"),
        )
        .agg(
            F.avg("temperature").alias("avg_temperature"),
            F.min("temperature").alias("min_temperature"),
            F.max("temperature").alias("max_temperature"),
            F.avg("humidity").alias("avg_humidity"),
            F.avg("pressure").alias("avg_pressure"),
            F.avg("ph").alias("avg_ph"),
            F.count("*").alias("event_count"),
            F.sum(F.when(F.col("status") == "active", 1).otherwise(0)).alias(
                "active_count"
            ),
            F.sum(F.when(F.col("status") == "degraded", 1).otherwise(0)).alias(
                "degraded_count"
            ),
            F.sum(F.when(F.col("status") == "offline", 1).otherwise(0)).alias(
                "offline_count"
            ),
        )
        .select(
            F.col("window.start").alias("window_start"),
            F.col("window.end").alias("window_end"),
            F.col("sensor_id"),
            F.col("location"),
            F.round("avg_temperature", 2).alias("avg_temperature"),
            F.round("min_temperature", 2).alias("min_temperature"),
            F.round("max_temperature", 2).alias("max_temperature"),
            F.round("avg_humidity", 2).alias("avg_humidity"),
            F.round("avg_pressure", 2).alias("avg_pressure"),
            F.round("avg_ph", 2).alias("avg_ph"),
            F.col("event_count"),
            F.col("active_count"),
            F.col("degraded_count"),
            F.col("offline_count"),
            F.current_timestamp().alias("_processed_at"),
        )
    )

    aggregated.createOrReplaceTempView("gold_batch")
    spark.sql(
        f"""
        MERGE INTO {GOLD_TABLE} AS target
        USING gold_batch AS source
        ON target.window_start = source.window_start
           AND target.sensor_id = source.sensor_id
           AND COALESCE(target.location, '') = COALESCE(source.location, '')
        WHEN MATCHED THEN UPDATE SET *
        WHEN NOT MATCHED THEN INSERT *
        """
    )


if __name__ == "__main__":
    main()
