"""
IoT Sensor Simulator — Kafka Producer

Simulates N sensors continuously publishing weather/environmental readings
to a Kafka topic. Each sensor has a stable base value with Gaussian noise
to mimic real sensor variance.

Config via env vars:
  KAFKA_BOOTSTRAP_SERVERS   default: localhost:29092
  KAFKA_TOPIC               default: iot.sensors.raw
  NUM_SENSORS               default: 10
  EVENTS_PER_SECOND         default: 10
"""

import json
import os
import random
import signal
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from confluent_kafka import Producer

BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:29092")
TOPIC = os.getenv("KAFKA_TOPIC", "iot.sensors.raw")
NUM_SENSORS = int(os.getenv("NUM_SENSORS", "10"))
EVENTS_PER_SECOND = float(os.getenv("EVENTS_PER_SECOND", "2"))

LOCATIONS = ["warehouse-A", "warehouse-B", "field-north", "field-south", "rooftop"]


@dataclass
class SensorReading:
    sensor_id: str
    timestamp: str
    temperature: float
    humidity: float
    pressure: float
    ph: float
    location: str
    status: str


@dataclass
class Sensor:
    sensor_id: str
    location: str
    base_temp: float
    base_humidity: float
    base_pressure: float
    base_ph: float

    def reading(self) -> SensorReading:
        r = random.random()
        status = "active" if r > 0.02 else ("degraded" if r > 0.005 else "offline")

        return SensorReading(
            sensor_id=self.sensor_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            temperature=round(self.base_temp + random.gauss(0, 0.5), 2),
            humidity=round(
                min(100.0, max(0.0, self.base_humidity + random.gauss(0, 1.0))), 2
            ),
            pressure=round(self.base_pressure + random.gauss(0, 0.3), 2),
            ph=round(min(14.0, max(0.0, self.base_ph + random.gauss(0, 0.05))), 2),
            location=self.location,
            status=status,
        )


def make_sensors(n: int) -> list[Sensor]:
    return [
        Sensor(
            sensor_id=f"sensor-{str(uuid.uuid4())[:8]}",
            location=random.choice(LOCATIONS),
            base_temp=random.uniform(-10.0, 45.0),
            base_humidity=random.uniform(20.0, 90.0),
            base_pressure=random.uniform(980.0, 1030.0),
            base_ph=random.uniform(5.5, 8.5),
        )
        for _ in range(n)
    ]


def delivery_report(err, msg):
    if err:
        print(f"[ERROR] Delivery failed for {msg.key()}: {err}")


def run():
    producer = Producer(
        {
            "bootstrap.servers": BOOTSTRAP_SERVERS,
            "message.timeout.ms": 5000,
            "socket.timeout.ms": 5000,
        }
    )
    sensors = make_sensors(NUM_SENSORS)
    interval = 1.0 / EVENTS_PER_SECOND

    print(
        f"Simulator started — {NUM_SENSORS} sensors → topic '{TOPIC}' @ {EVENTS_PER_SECOND} events/sec"
    )

    running = True
    force_exit = False

    def shutdown(signum, frame):
        nonlocal running, force_exit
        if running:
            print("Shutdown signal received. Stopping producer loop...")
            running = False
            return

        if not force_exit:
            force_exit = True
            print("Second shutdown signal received. Forcing immediate exit...")
            raise SystemExit(130)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    while running:
        sensor = random.choice(sensors)
        reading = sensor.reading()
        payload = json.dumps(asdict(reading)).encode("utf-8")

        try:
            producer.produce(
                topic=TOPIC,
                key=reading.sensor_id.encode("utf-8"),
                value=payload,
                on_delivery=delivery_report,
            )
        except BufferError:
            # If broker is unavailable for a while, let librdkafka drain callbacks.
            producer.poll(0.1)
            continue
        producer.poll(0)
        time.sleep(interval)

    remaining = producer.flush(5)
    if remaining > 0:
        print(f"Shutdown completed with {remaining} undelivered message(s).")
    else:
        print("Producer flushed. Bye.")


if __name__ == "__main__":
    run()
