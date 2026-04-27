CREATE TABLE IF NOT EXISTS iotstream.bronze.sensor_raw (
    sensor_id        STRING,
    timestamp        TIMESTAMP,
    temperature      DOUBLE,
    humidity         DOUBLE,
    pressure         DOUBLE,
    ph               DOUBLE,
    location         STRING,
    status           STRING,
    _ingested_at     TIMESTAMP NOT NULL,
    _kafka_offset    BIGINT,
    _kafka_partition INT,
    _kafka_topic     STRING
)
USING iceberg
PARTITIONED BY (days(timestamp))
TBLPROPERTIES (
    'write.format.default'            = 'parquet',
    'write.parquet.compression-codec' = 'snappy'
);
