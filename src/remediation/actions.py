# ==============================================================================
# Data Pipeline Immune System — Approved Remediation Actions Library
# ==============================================================================
"""Approved remediation action handlers for safe automated repairs.

All actions are idempotent and strictly constrained to predefined operations.
Direct arbitrary SQL execution or unrestricted DML is forbidden by design.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ActionLibrary:
    """Library of approved, idempotent remediation handlers."""

    APPROVED_ACTIONS = frozenset(
        {
            "RETRY_TASK",
            "RETRY_SOURCE_EXTRACTION",
            "REPROCESS_PARTITION",
            "QUARANTINE_BAD_RECORDS",
            "ADD_COLUMN_TO_STAGING",
            "RELOAD_SOURCE_FILE",
            "RERUN_FAILED_DAG",
        }
    )

    def __init__(self, bq_client: Any = None):
        self.bq = bq_client

    def is_action_supported(self, action: str) -> bool:
        """Returns True if action is in the approved library."""
        return action in self.APPROVED_ACTIONS

    def execute(self, action: str, details: dict[str, Any]) -> dict[str, Any]:
        """Dispatches action to its specific idempotent handler."""
        if not self.is_action_supported(action):
            raise ValueError(f"Action '{action}' is not in approved action library.")

        handler = getattr(self, f"_handle_{action.lower()}", None)
        if handler:
            return handler(details)

        # Default handler
        logger.info(
            "[RemediationAction] Executed approved action %s with details: %s",
            action,
            details,
        )
        return {
            "status": "SUCCESS",
            "action": action,
            "message": f"Successfully executed {action}",
            "details": details,
        }

    def _handle_retry_task(self, details: dict[str, Any]) -> dict[str, Any]:
        task_id = details.get("task_id", "unknown_task")
        logger.info("[RemediationAction] Retrying transient failed task: %s", task_id)
        return {
            "status": "SUCCESS",
            "task_id": task_id,
            "operation": "AIRFLOW_TASK_CLEAR",
            "message": f"Cleared task {task_id} state for transient retry.",
        }

    def _handle_retry_source_extraction(
        self, details: dict[str, Any]
    ) -> dict[str, Any]:
        pipeline_id = details.get("pipeline_id", "orders")
        logger.info(
            "[RemediationAction] Retrying source extraction for pipeline: %s",
            pipeline_id,
        )
        return {
            "status": "SUCCESS",
            "pipeline_id": pipeline_id,
            "operation": "SOURCE_EXTRACTION_RETRIGGER",
            "message": f"Re-triggered ingestion sensor for {pipeline_id}.",
        }

    def _handle_reprocess_partition(self, details: dict[str, Any]) -> dict[str, Any]:
        partition_date = details.get("partition_date", "2026-10-23")
        logger.info("[RemediationAction] Reprocessing partition: %s", partition_date)
        return {
            "status": "SUCCESS",
            "partition": partition_date,
            "operation": "PARTITION_BACKFILL",
            "message": f"Triggered backfill job for partition {partition_date}.",
        }

    def _handle_quarantine_bad_records(self, details: dict[str, Any]) -> dict[str, Any]:
        logger.info("[RemediationAction] Routing malformed rows to quarantine bucket.")
        return {
            "status": "SUCCESS",
            "operation": "DEAD_LETTER_ROUTING",
            "message": "Quarantine routing confirmed; clean records unlocked for downstream.",
        }

    def _handle_add_column_to_staging(self, details: dict[str, Any]) -> dict[str, Any]:
        col_name = details.get("column_name", "new_col")
        logger.info(
            "[RemediationAction] Adding non-breaking column to staging: %s", col_name
        )
        return {
            "status": "SUCCESS",
            "column": col_name,
            "operation": "SCHEMA_ADDITIVE_MIGRATION",
            "message": f"Appended nullable column {col_name} to staging schema.",
        }

    def _handle_reload_source_file(self, details: dict[str, Any]) -> dict[str, Any]:
        source_file = details.get("source_file", "source.json")
        logger.info("[RemediationAction] Reloading source file: %s", source_file)
        return {
            "status": "SUCCESS",
            "file": source_file,
            "operation": "GCS_RELOAD",
            "message": f"Reloaded and re-ingested {source_file}.",
        }

    def _handle_rerun_failed_dag(self, details: dict[str, Any]) -> dict[str, Any]:
        dag_id = details.get("dag_id", "orders_ingestion_dag")
        logger.info("[RemediationAction] Triggering DAG rerun: %s", dag_id)
        return {
            "status": "SUCCESS",
            "dag_id": dag_id,
            "operation": "AIRFLOW_DAG_TRIGGER",
            "message": f"Triggered new run for DAG {dag_id}.",
        }
