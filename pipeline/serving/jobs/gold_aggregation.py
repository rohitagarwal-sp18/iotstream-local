"""
Gold aggregation job.

Reads from the Iceberg silver table, applies a 1-minute tumbling window
aggregation per sensor + location, and writes results to the gold table.

Uses trigger(availableNow=True) so the job processes all available silver
data and terminates — suitable for Airflow scheduling.
"""

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

SILVER_TABLE = "iotstream.silver.sensor_clean"
GOLD_TABLE = "iotstream.gold.sensor_metrics_1min"
CHECKPOINT_LOCATION = "s3a://iotstream-checkpoints/gold/"

WINDOW_DURATION = "1 minute"
WATERMARK_DELAY = "5 minutes"


def main() -> None:
    spark = (
        SparkSession.builder.appName("iotstream-gold-aggregation")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")

    silver_stream = (
        spark.readStream.format("iceberg")
        .load(SILVER_TABLE)
        .withWatermark("timestamp", WATERMARK_DELAY)
    )

    aggregated = (
        silver_stream.groupBy(
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

    query = (
        aggregated.writeStream.format("iceberg")
        .outputMode("append")
        .option("checkpointLocation", CHECKPOINT_LOCATION)
        .trigger(availableNow=True)
        .toTable(GOLD_TABLE)
    )

    query.awaitTermination()


if __name__ == "__main__":
    main()
