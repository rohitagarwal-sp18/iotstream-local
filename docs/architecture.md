# IoTStream Local — Architecture

IoTStream Local is a fully local, Docker-based IoT data pipeline that ingests sensor readings from Kafka through Bronze/Silver/Gold Iceberg layers into Metabase. All infrastructure runs on a single machine with no cloud dependencies.

## Data Flow

```
[Sensor Simulator]
       │  JSON events @ iot.sensors.raw
       ▼
[Kafka (KRaft)]
       │  readStream (always-on)
       ▼
[Bronze Layer — Iceberg]          ← bronze_streaming.py (standalone container)
  iotstream.bronze.sensor_raw
  Raw events + Kafka metadata, no transformation
       │  readStream (availableNow)
       ▼
[Silver Layer — Iceberg]          ← silver_processing.py (Airflow, every 5 min)
  iotstream.silver.sensor_clean
  Validated, deduplicated records
  Invalid records → iot.sensors.dead-letter (Kafka)
       │  readStream (availableNow)
       ▼
[Gold Layer — Iceberg]            ← gold_aggregation.py (Airflow, after silver)
  iotstream.gold.sensor_metrics_1min
  1-minute window aggregates per sensor + location
       │  SQL queries
       ▼
[Metabase]
  Dashboards: realtime metrics, sensor health, historical trends
```

## Component Decisions

**Kafka over RabbitMQ**: Kafka provides durable, replayable log storage with partition-level parallelism. For sensor data, replay is essential — if the Bronze job crashes mid-stream, it resumes from its checkpointed offset rather than losing events. RabbitMQ's message-deletion-on-ack model makes replay impossible without custom infrastructure.

**Iceberg over plain Parquet files**: Iceberg adds ACID transactions, schema evolution without rewriting files, and time travel (SELECT ... FOR VERSION AS OF). For a multi-layer pipeline where Silver reads from Bronze while Bronze is still writing, Iceberg's snapshot isolation prevents dirty reads that would occur with plain Parquet.

**MinIO over a local filesystem**: Spark and Airflow workers run in separate containers and need a shared, addressable object store. MinIO speaks the S3 protocol, so all S3A paths (`s3a://`) used in Spark configs and checkpoints work without modification against a real AWS bucket when moving to production.

**Airflow over always-on Spark jobs for Silver/Gold**: Bronze runs always-on because it is append-only and latency-sensitive. Silver and Gold are micro-batch with `trigger(availableNow=True)` — they process a bounded chunk of data and terminate. Airflow manages retries, scheduling (every 5 minutes), and dependency ordering (Gold waits for Silver). Running them always-on would hold Spark executors idle between bursts.

**Bronze/Silver/Gold separation**: Each layer has a single responsibility. Bronze is an exact replica of Kafka with provenance metadata — never transform at ingestion, so any bug in downstream logic can be corrected by replaying from Bronze. Silver is the quality gate — validation and dedup happen once and consumers never see duplicates. Gold pre-aggregates common query patterns so Metabase queries scan kilobytes not gigabytes.

## Bronze Layer Design

Bronze ingests raw events without any transformation by design. If a downstream validation rule turns out to be wrong (e.g., the pressure range is too narrow for a new sensor type), the raw event is still in Bronze and Silver can be reprocessed. Kafka metadata columns (`_kafka_offset`, `_kafka_partition`, `_kafka_topic`) are stored for audit trails and for pinpointing exactly which Kafka offset produced a given row.

## Silver Layer Design

**Validation thresholds**: humidity 0–100 (physical constraint), pressure 800–1100 hPa (covers altitude range from sea level to ~2000m), pH 0–14 (standard scale). These are hard physical limits, not sensor-specific — readings outside them indicate sensor malfunction, not extreme conditions.

**Dedup strategy**: `_dedup_key = sensor_id|timestamp` within each micro-batch via `dropDuplicates`. This handles duplicate Kafka deliveries (at-least-once semantics) and simulator restarts that replay the same timestamp. Cross-batch deduplication is not implemented at this stage; Iceberg `MERGE INTO` can be added when exactly-once guarantees are needed.

**Dead-letter pattern**: Invalid records are forwarded to `iot.sensors.dead-letter` as JSON rather than silently dropped. This allows a separate process to inspect failures, alert on sensor malfunctions, or backfill after a calibration fix.

## Gold Layer Design

**1-minute windows**: Short enough to power near-realtime dashboards (Metabase auto-refresh every 60s) while aggregating enough events per window to smooth noise. The simulator produces ~10 events/sec across 10 sensors, so each window captures ~600 events — statistically meaningful.

**5-minute watermark**: Spark's event-time watermark controls how late data is still accepted into a window before it is finalised. 5 minutes accommodates transient Kafka consumer lag and clock skew between sensor containers. Setting it shorter risks dropping events that arrive slightly late; longer delays final window output unnecessarily.

## Operational Notes

**Adding a new sensor type**: Add new fields to `schemas/events/sensor_event.json`. Update `EVENT_SCHEMA` in `bronze_streaming.py` (Iceberg schema evolution handles adding nullable columns with no table rewrite). Update Silver validation in `is_valid` and `_VALID_EXPR` if new fields need quality checks. The Gold aggregation is agnostic to sensor type — no changes needed unless new aggregation metrics are required.

**Reprocessing historical data**: Bronze is the source of truth. To reprocess Silver from a specific point in time:
1. Drop and recreate the Silver Iceberg table (or use `DELETE FROM` with a time filter).
2. Delete the Silver checkpoint at `s3a://iotstream-checkpoints/silver/`.
3. Restart the Silver job — it will read all Bronze data from the beginning.

For partial reprocessing, use Iceberg time travel: `SELECT * FROM iotstream.bronze.sensor_raw FOR SYSTEM_TIME AS OF '2025-01-01 00:00:00'` to inspect what data existed at any point.
