"""Unit tests for the is_valid function in silver_processing.py."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "jobs"))

from silver_processing import is_valid  # noqa: E402

_BASE = {
    "sensor_id": "sensor-abc123",
    "timestamp": "2025-01-01T00:00:00+00:00",
    "temperature": 22.5,
    "humidity": 55.0,
    "pressure": 1013.0,
    "ph": 7.0,
    "location": "warehouse-A",
    "status": "active",
}


def _row(**overrides) -> dict:
    return {**_BASE, **overrides}


def test_valid_full_record():
    assert is_valid(_BASE) is True


def test_null_sensor_id():
    assert is_valid(_row(sensor_id=None)) is False


def test_null_timestamp():
    assert is_valid(_row(timestamp=None)) is False


def test_humidity_above_100():
    assert is_valid(_row(humidity=100.1)) is False


def test_humidity_below_0():
    assert is_valid(_row(humidity=-0.1)) is False


def test_pressure_out_of_range_high():
    assert is_valid(_row(pressure=1100.1)) is False


def test_pressure_out_of_range_low():
    assert is_valid(_row(pressure=799.9)) is False


def test_ph_out_of_range():
    assert is_valid(_row(ph=14.1)) is False


def test_null_humidity():
    assert is_valid(_row(humidity=None)) is False
