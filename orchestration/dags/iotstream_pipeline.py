from datetime import datetime

from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import dag
from core.constants import PIPELINE_BASE, SPARK_CONTAINER, SPARK_SUBMIT

DAG_ARGS = {
    "dag_id": "iotstream_pipeline",
    "schedule": "*/5 * * * *",
    "start_date": datetime(2026, 1, 1),
    "catchup": False,
    "max_active_runs": 1,
}


@dag(
    **DAG_ARGS,
)
def iotstream_pipeline():
    bronze_job = BashOperator(
        task_id="bronze_job",
        bash_command=(
            f"docker exec {SPARK_CONTAINER} "
            f"{SPARK_SUBMIT} "
            f"{PIPELINE_BASE}/ingestion/jobs/bronze_streaming.py"
        ),
    )

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

    bronze_job >> silver_job >> gold_job


iotstream_pipeline()
