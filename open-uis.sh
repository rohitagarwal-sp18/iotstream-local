#!/usr/bin/env bash
set -euo pipefail

open_url() {
  if command -v open &>/dev/null; then
    open "$1"
  elif command -v xdg-open &>/dev/null; then
    xdg-open "$1"
  else
    echo "Cannot open browser — visit: $1"
  fi
}

echo "Opening IoTStream Local UIs..."

open_url "http://localhost:3000"   # Metabase
open_url "http://localhost:8080"   # Airflow
open_url "http://localhost:8088"   # Trino
open_url "http://localhost:8081"   # Spark Master UI
open_url "http://localhost:4040"   # Spark Job UI
open_url "http://localhost:8082"   # Spark Worker UI
open_url "http://localhost:9001"   # MinIO Console
open_url "http://localhost:9090"   # Kafka UI

echo "Done — 8 tabs opened."
