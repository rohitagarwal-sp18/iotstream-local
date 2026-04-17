# IoTStream Local

A fully self-hosted, real-time IoT data platform. Ingests streaming sensor data, processes it through a medallion architecture (Bronze → Silver → Gold), and serves it via SQL dashboards — all on local infrastructure.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Data Flow                                │
│                                                                 │
│  Sensor Simulator  ──►  Kafka  ──►  Spark Streaming             │
│  (services/)           (infra/)     (pipeline/)                 │
│                                          │                      │
│                              ┌───────────▼───────────┐          │
│                              │   MinIO + Iceberg      │         │
│                              │  Bronze / Silver / Gold│         │
│                              └───────────┬───────────┘          │
│                                          │                      │
│                              Metabase Dashboard                 │
│                              (visualization/)                   │
│                                                                 │
│                    Airflow orchestrates pipeline jobs           │
│                    (orchestration/)                             │
└─────────────────────────────────────────────────────────────────┘
```

### Medallion Layers

| Layer  | Location                  | What happens                                |
|--------|---------------------------|---------------------------------------------|
| Bronze | `pipeline/ingestion/`     | Raw Kafka events → Iceberg, no transforms   |
| Silver | `pipeline/processing/`    | Schema validation, null handling, dedup     |
| Gold   | `pipeline/serving/`       | Aggregations, business metrics, enrichment  |

---

## Tech Stack

| Component    | Technology                       | Purpose                          |
|--------------|----------------------------------|----------------------------------|
| Message Bus  | Apache Kafka                     | Event ingestion, buffering       |
| Processing   | Apache Spark (Structured Stream) | Stream transformation            |
| Storage      | MinIO + Apache Iceberg           | S3-compatible, ACID, time travel |
| Orchestration| Apache Airflow                   | Job scheduling, retry, lineage   |
| Serving      | Metabase                         | SQL queries, dashboards          |
| Infra        | Docker Compose                   | Local service orchestration      |

---

## Project Structure

```
iotstream-local/
│
├── infra/                         # Infrastructure-as-code (Docker Compose per service)
│   ├── kafka/
│   ├── spark/
│   ├── minio/
│   ├── airflow/
│   ├── metabase/
│   └── docker-compose.yml         # Full stack — starts everything
│
├── services/
│   └── sensor-simulator/          # Standalone producer service (separate deployable)
│       ├── src/
│       ├── tests/
│       └── Dockerfile
│
├── pipeline/                      # Data pipeline — organized by medallion layer, NOT by tool
│   ├── ingestion/                 # Bronze: Kafka → raw Iceberg tables
│   │   ├── jobs/
│   │   └── tests/
│   ├── processing/                # Silver: clean, validate, deduplicate
│   │   ├── jobs/
│   │   └── tests/
│   └── serving/                   # Gold: aggregate, enrich, business metrics
│       ├── jobs/
│       └── tests/
│
├── schemas/                       # Shared data contracts (single source of truth)
│   ├── events/                    # Kafka message schemas (JSON Schema / Avro)
│   └── tables/                    # Iceberg table DDL
│       ├── bronze/
│       ├── silver/
│       └── gold/
│
├── orchestration/                 # Airflow
│   ├── dags/                      # DAG definitions
│   ├── plugins/                   # Custom operators/hooks
│   └── configs/                   # Airflow connections, variables
│
├── visualization/                 # Metabase
│   ├── dashboards/                # Exported dashboard JSON
│   └── queries/                   # Saved SQL queries
│
├── config/                        # Environment configuration (no secrets)
│   ├── kafka/                     # Topic definitions, retention, partitions
│   ├── spark/                     # spark-defaults.conf, resource tuning
│   └── minio/                     # Bucket policies
│
├── scripts/                       # Developer tooling
│   ├── setup.sh                   # First-time setup
│   ├── teardown.sh                # Destroy all services + volumes
│   └── health-check.sh            # Verify all services are alive
│
└── docs/
    ├── architecture.md            # System design deep-dive
    └── local-setup.md             # How to operate this system
```


## Data Schema (v1)

Kafka event emitted by each sensor:

```json
{
  "sensor_id": "string",
  "timestamp": "datetime (ISO 8601)",
  "temperature": "float",
  "humidity": "float",
  "pressure": "float",
  "ph": "float",
  "location": "string",
  "status": "string"
}
```

Partitioning: `year=YYYY/month=MM/day=DD/hour=HH`

---

## Getting Started

### Prerequisites
- Docker Desktop (with at least 8GB RAM allocated)
- Python 3.11+

### Steps

1. **Clone and enter the project**
   ```bash
   git clone <repo> && cd iotstream-local
   ```

2. **Start the infrastructure**
   ```bash
   # Start Kafka + MinIO first (dependencies)
   docker compose -f infra/docker-compose.yml up kafka minio -d
   ```

3. **Initialize storage** (create MinIO buckets + Iceberg tables)
   ```bash
   ./scripts/setup.sh
   ```

4. **Start the sensor simulator**
   ```bash
   docker compose -f infra/docker-compose.yml up sensor-simulator -d
   ```

5. **Start Spark streaming jobs**
   ```bash
   docker compose -f infra/docker-compose.yml up spark -d
   ```

6. **Start Airflow**
   ```bash
   docker compose -f infra/docker-compose.yml up airflow -d
   ```

7. **Open Metabase** at `http://localhost:3000`

8. **Verify the pipeline**
   ```bash
   ./scripts/health-check.sh
   ```

---

## Non-Functional Targets

| Metric             | Target                          |
|--------------------|---------------------------------|
| End-to-end latency | < 5 seconds                     |
| Throughput         | 10K+ events/sec (simulated)     |
| Sensors            | 1000+ concurrent (simulated)    |
| Delivery guarantee | At-least-once                   |
| Processing         | Idempotent (deduplication)      |

---

## Edge Cases Handled

- Sensor downtime → null-safe processing in Silver layer
- Corrupt payloads → schema validation at ingestion, dead-letter pattern
- Duplicate events → deduplication key on `sensor_id + timestamp`
- Late-arriving data → Spark watermarking
- Out-of-order timestamps → event-time processing (not processing-time)
