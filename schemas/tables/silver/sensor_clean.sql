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
    'write.format.default'            = 'parquet',
    'write.parquet.compression-codec' = 'snappy'
);
