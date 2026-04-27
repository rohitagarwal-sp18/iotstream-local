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
    'write.format.default'            = 'parquet',
    'write.parquet.compression-codec' = 'snappy'
);
