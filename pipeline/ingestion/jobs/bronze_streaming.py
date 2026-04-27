from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    DoubleType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

KAFKA_BOOTSTRAP = "kafka:9092"
KAFKA_TOPIC = "iot.sensors.raw"
BRONZE_PATH = "s3a://iotstream-bronze/sensor_raw/"
CHECKPOINT_LOCATION = "s3a://iotstream-checkpoints/bronze/"

EVENT_SCHEMA = StructType(
    [
        StructField("sensor_id", StringType(), True),
        StructField("timestamp", TimestampType(), True),
        StructField("temperature", DoubleType(), True),
        StructField("humidity", DoubleType(), True),
        StructField("pressure", DoubleType(), True),
        StructField("ph", DoubleType(), True),
        StructField("location", StringType(), True),
        StructField("status", StringType(), True),
    ]
)


def main() -> None:
    spark = SparkSession.builder.appName("iotstream-bronze-ingestion").getOrCreate()
    spark.sparkContext.setLogLevel("WARN")

    raw_stream = (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP)
        .option("subscribe", KAFKA_TOPIC)
        .option("startingOffsets", "earliest")
        .option("failOnDataLoss", "false")
        .load()
    )

    parsed = raw_stream.select(
        F.from_json(F.col("value").cast("string"), EVENT_SCHEMA).alias("data"),
        F.current_timestamp().alias("_ingested_at"),
    ).select("data.*", "_ingested_at")

    query = (
        parsed.writeStream.format("json")
        .outputMode("append")
        .option("path", BRONZE_PATH)
        .option("checkpointLocation", CHECKPOINT_LOCATION)
        .trigger(availableNow=True)
        .start()
    )

    query.awaitTermination()


if __name__ == "__main__":
    main()
