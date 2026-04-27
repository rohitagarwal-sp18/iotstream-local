from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    DoubleType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

BRONZE_PATH = "s3a://iotstream-bronze/sensor_raw/"
SILVER_TABLE = "iotstream.silver.sensor_clean"

BRONZE_SCHEMA = StructType(
    [
        StructField("sensor_id", StringType(), True),
        StructField("timestamp", TimestampType(), True),
        StructField("temperature", DoubleType(), True),
        StructField("humidity", DoubleType(), True),
        StructField("pressure", DoubleType(), True),
        StructField("ph", DoubleType(), True),
        StructField("location", StringType(), True),
        StructField("status", StringType(), True),
        StructField("_ingested_at", TimestampType(), True),
    ]
)
DEAD_LETTER_TOPIC = "iot.sensors.dead-letter"
KAFKA_BOOTSTRAP = "kafka:9092"
CHECKPOINT_LOCATION = "s3a://iotstream-checkpoints/silver/"


def ensure_silver_table(spark: SparkSession) -> None:
    spark.sql(
        """
        CREATE TABLE IF NOT EXISTS iotstream.silver.sensor_clean (
            sensor_id     STRING    NOT NULL,
            timestamp     TIMESTAMP NOT NULL,
            temperature   DOUBLE,
            humidity      DOUBLE,
            pressure      DOUBLE,
            ph            DOUBLE,
            location      STRING,
            status        STRING,
            _processed_at TIMESTAMP NOT NULL,
            _dedup_key    STRING    NOT NULL
        )
        USING iceberg
        PARTITIONED BY (days(timestamp))
        TBLPROPERTIES (
            'write.format.default' = 'parquet',
            'write.parquet.compression-codec' = 'snappy'
        )
        """
    )


# ---------------------------------------------------------------------------
# Pure-Python validation (used in unit tests — no Spark dependency)
# ---------------------------------------------------------------------------


def is_valid(row: dict) -> bool:
    """Return True if the row passes all data quality checks."""
    if row.get("sensor_id") is None:
        return False
    if row.get("timestamp") is None:
        return False
    humidity = row.get("humidity")
    if humidity is None or not (0 <= humidity <= 100):
        return False
    pressure = row.get("pressure")
    if pressure is None or not (800 <= pressure <= 1100):
        return False
    ph = row.get("ph")
    if ph is None or not (0 <= ph <= 14):
        return False
    return True


def _valid_expr() -> F.Column:
    """Spark expression for the same validation checks used in is_valid."""
    return (
        F.col("sensor_id").isNotNull()
        & F.col("timestamp").isNotNull()
        & F.col("humidity").isNotNull()
        & (F.col("humidity") >= 0)
        & (F.col("humidity") <= 100)
        & F.col("pressure").isNotNull()
        & (F.col("pressure") >= 800)
        & (F.col("pressure") <= 1100)
        & F.col("ph").isNotNull()
        & (F.col("ph") >= 0)
        & (F.col("ph") <= 14)
    )


# ---------------------------------------------------------------------------
# Batch processing logic
# ---------------------------------------------------------------------------


def process_batch(batch_df: DataFrame, batch_id: int) -> None:
    """foreachBatch handler: route valid records to silver, invalid to dead-letter."""
    valid_expr = _valid_expr()
    valid_df = batch_df.filter(valid_expr)
    invalid_df = batch_df.filter(~valid_expr)

    # Write valid records to silver table
    if not valid_df.isEmpty():
        silver_df = (
            valid_df.withColumn(
                "_dedup_key",
                F.concat_ws("|", F.col("sensor_id"), F.col("timestamp").cast("string")),
            )
            .dropDuplicates(["_dedup_key"])
            .withColumn("_processed_at", F.current_timestamp())
            .select(
                "sensor_id",
                "timestamp",
                "temperature",
                "humidity",
                "pressure",
                "ph",
                "location",
                "status",
                "_processed_at",
                "_dedup_key",
            )
        )
        spark = batch_df.sparkSession
        if spark.catalog.tableExists(SILVER_TABLE):
            existing_keys_df = (
                spark.table(SILVER_TABLE).select("_dedup_key").dropDuplicates()
            )
            silver_df = silver_df.join(
                existing_keys_df, on="_dedup_key", how="left_anti"
            )

        if not silver_df.isEmpty():
            silver_df.writeTo(SILVER_TABLE).append()

    # Send invalid records to dead-letter topic as JSON
    if not invalid_df.isEmpty():
        dead_letter_df = invalid_df.select(F.to_json(F.struct("*")).alias("value"))
        (
            dead_letter_df.write.format("kafka")
            .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP)
            .option("topic", DEAD_LETTER_TOPIC)
            .save()
        )


def main() -> None:
    spark = SparkSession.builder.appName("iotstream-silver-processing").getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    ensure_silver_table(spark)

    bronze_stream = (
        spark.readStream.format("json").schema(BRONZE_SCHEMA).load(BRONZE_PATH)
    )

    query = (
        bronze_stream.writeStream.foreachBatch(process_batch)
        .option("checkpointLocation", CHECKPOINT_LOCATION)
        .trigger(availableNow=True)
        .start()
    )

    query.awaitTermination()


if __name__ == "__main__":
    main()
