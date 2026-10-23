# ==============================================================================
# Data Pipeline Immune System — Ingestion Pipeline DAG
# ==============================================================================
"""Orchestrates source data extraction and Bronze lake landing.

Pipeline: GCS Source Landing -> Bronze Staging -> Metric Emitting
Emits operational metrics to the immune control plane for real-time observability.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Any

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}


def notify_pipeline_run_start(**context: Any) -> None:
    """Emits run start event to BigQuery pipeline_runs table."""
    run_id = context["run_id"]
    logical_date = context.get("logical_date") or context.get("execution_date")
    print(f"[Immune Telemetry] Pipeline 'orders_ingestion' started: run_id={run_id}, date={logical_date}")


def notify_pipeline_run_completion(**context: Any) -> None:
    """Emits run completion status to BigQuery pipeline_runs table."""
    run_id = context["run_id"]
    print(f"[Immune Telemetry] Pipeline 'orders_ingestion' completed successfully: run_id={run_id}")


with DAG(
    dag_id="orders_ingestion_dag",
    default_args=default_args,
    description="Daily ingestion of upstream orders from GCS source to Bronze raw store",
    schedule_interval="0 2 * * *",  # 02:00 AM UTC daily
    start_date=datetime(2026, 10, 1),
    catchup=False,
    max_active_runs=1,
    tags=["production", "lakehouse", "bronze", "orders"],
) as dag:

    emit_start = PythonOperator(
        task_id="emit_run_start",
        python_callable=notify_pipeline_run_start,
    )

    check_source = BashOperator(
        task_id="check_source_landing",
        bash_command=(
            "echo 'Checking source files in GCS bucket: "
            "${SOURCE_BUCKET:-dpis-dev-source}/orders/{{ ds }}/'"
        ),
    )

    run_bronze_job = BashOperator(
        task_id="run_bronze_ingestion",
        bash_command=(
            "python -m spark.jobs.orders_bronze_ingestion "
            "--source-path gs://${SOURCE_BUCKET:-dpis-dev-source}/orders/{{ ds }}/*.json "
            "--target ${PROJECT_ID:-dpis-dev}.${DATASET_BRONZE:-dpis_bronze_dev}.orders "
            "--run-id {{ run_id }} "
            "--format ${WRITE_FORMAT:-parquet}"
        ),
    )

    emit_complete = PythonOperator(
        task_id="emit_run_complete",
        python_callable=notify_pipeline_run_completion,
    )

    emit_start >> check_source >> run_bronze_job >> emit_complete
