"""
Silver and Gold micro-batch pipeline.

Bronze ingestion runs as a standalone container (bronze-ingestion service in
infra/docker-compose.yml). Prerequisites: Airflow worker needs Docker CLI —
see infra/airflow/Dockerfile and docker-compose.override.yml.
"""

from datetime import datetime

from airflow.decorators import dag
from airflow.operators.bash import BashOperator

SPARK_SUBMIT = "/opt/spark/bin/spark-submit --master spark://spark-master:7077"
SPARK_CONTAINER = "iotstream-spark-master"
PIPELINE_BASE = "/opt/spark/pipeline"

DEFAULT_ARGS = {
    "retries": 2,
}


@dag(
    dag_id="iotstream_pipeline",
    schedule="*/5 * * * *",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=["iotstream", "silver", "gold"],
)
def iotstream_pipeline():
    silver_job = BashOperator(
        task_id="silver_job",
        bash_command=(
            f"docker exec {SPARK_CONTAINER} "
            f"{SPARK_SUBMIT} "
            f"{PIPELINE_BASE}/processing/jobs/silver_processing.py"
        ),
    )

    gold_job = BashOperator(
        task_id="gold_job",
        bash_command=(
            f"docker exec {SPARK_CONTAINER} "
            f"{SPARK_SUBMIT} "
            f"{PIPELINE_BASE}/serving/jobs/gold_aggregation.py"
        ),
    )

    silver_job >> gold_job


iotstream_pipeline()
