"""Unit tests for the sensor simulator."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from simulator import Sensor, SensorReading, make_sensors  # noqa: E402


def test_sensor_reading_types():
    sensor = Sensor(
        sensor_id="sensor-test01",
        location="warehouse-A",
        base_temp=20.0,
        base_humidity=50.0,
        base_pressure=1013.0,
        base_ph=7.0,
    )
    reading = sensor.reading()
    assert isinstance(reading, SensorReading)
    assert isinstance(reading.sensor_id, str)
    assert isinstance(reading.timestamp, str)
    assert isinstance(reading.temperature, float)
    assert isinstance(reading.humidity, float)
    assert isinstance(reading.pressure, float)
    assert isinstance(reading.ph, float)
    assert isinstance(reading.location, str)
    assert isinstance(reading.status, str)


def test_humidity_in_range():
    sensor = Sensor(
        sensor_id="sensor-h",
        location="field-north",
        base_temp=20.0,
        base_humidity=50.0,
        base_pressure=1013.0,
        base_ph=7.0,
    )
    for _ in range(100):
        r = sensor.reading()
        assert 0 <= r.humidity <= 100, f"humidity out of range: {r.humidity}"


def test_pressure_in_range():
    sensor = Sensor(
        sensor_id="sensor-p",
        location="rooftop",
        base_temp=15.0,
        base_humidity=40.0,
        base_pressure=1013.0,
        base_ph=7.0,
    )
    for _ in range(100):
        r = sensor.reading()
        assert 800 <= r.pressure <= 1100, f"pressure out of range: {r.pressure}"


def test_ph_in_range():
    sensor = Sensor(
        sensor_id="sensor-ph",
        location="field-south",
        base_temp=22.0,
        base_humidity=60.0,
        base_pressure=1000.0,
        base_ph=7.0,
    )
    for _ in range(100):
        r = sensor.reading()
        assert 0 <= r.ph <= 14, f"ph out of range: {r.ph}"


def test_status_valid():
    sensor = Sensor(
        sensor_id="sensor-s",
        location="warehouse-B",
        base_temp=20.0,
        base_humidity=50.0,
        base_pressure=1013.0,
        base_ph=7.0,
    )
    valid_statuses = {"active", "degraded", "offline"}
    for _ in range(100):
        r = sensor.reading()
        assert r.status in valid_statuses, f"unexpected status: {r.status}"


def test_make_sensors_count():
    sensors = make_sensors(5)
    assert len(sensors) == 5
    assert all(isinstance(s, Sensor) for s in sensors)


def test_unique_sensor_ids():
    sensors = make_sensors(10)
    ids = [s.sensor_id for s in sensors]
    assert len(ids) == len(set(ids)), "sensor_ids are not unique"
