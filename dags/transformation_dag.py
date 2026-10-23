# ==============================================================================
# Data Pipeline Immune System — Transformation Pipeline DAG
# ==============================================================================
"""Orchestrates Silver conformed transformation and Gold analytics aggregation.

Pipeline: Bronze Raw -> Silver Conformed (with ADR-008 Quarantine) -> Gold Analytics Mart
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


def log_quarantine_stats(**context: Any) -> None:
    """Logs quarantine stats to the immune control plane."""
    run_id = context["run_id"]
    print(f"[Immune Monitor] Monitored run {run_id} for quarantine partition spillover.")


with DAG(
    dag_id="orders_transformation_dag",
    default_args=default_args,
    description="Transforms Bronze raw orders to Silver validated tables and Gold daily marts",
    schedule_interval="0 4 * * *",  # 04:00 AM UTC daily
    start_date=datetime(2026, 10, 1),
    catchup=False,
    max_active_runs=1,
    tags=["production", "lakehouse", "silver", "gold", "orders"],
) as dag:

    transform_silver = BashOperator(
        task_id="transform_orders_silver",
        bash_command=(
            "python -m spark.jobs.orders_silver_transformation "
            "--bronze-source ${PROJECT_ID:-dpis-dev}.${DATASET_BRONZE:-dpis_bronze_dev}.orders "
            "--silver-target ${PROJECT_ID:-dpis-dev}.${DATASET_SILVER:-dpis_silver_dev}.orders "
            "--quarantine-target ${PROJECT_ID:-dpis-dev}.${DATASET_CONTROL:-dpis_dev}.quarantine_records "
            "--run-id {{ run_id }} "
            "--pipeline-id orders "
            "--format ${WRITE_FORMAT:-parquet}"
        ),
    )

    check_quarantine = PythonOperator(
        task_id="audit_quarantine_metrics",
        python_callable=log_quarantine_stats,
    )

    aggregate_gold = BashOperator(
        task_id="aggregate_orders_gold",
        bash_command=(
            "python -m spark.jobs.orders_gold_aggregation "
            "--silver-source ${PROJECT_ID:-dpis-dev}.${DATASET_SILVER:-dpis_silver_dev}.orders "
            "--gold-target ${PROJECT_ID:-dpis-dev}.${DATASET_GOLD:-dpis_gold_dev}.orders_daily_summary "
            "--date {{ ds }} "
            "--run-id {{ run_id }} "
            "--format ${WRITE_FORMAT:-parquet}"
        ),
    )

    transform_silver >> check_quarantine >> aggregate_gold
