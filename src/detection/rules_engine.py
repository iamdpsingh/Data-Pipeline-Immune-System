# ==============================================================================
# Data Pipeline Immune System — Deterministic Rules Engine (ADR-003)
# ==============================================================================
"""Deterministic failure classification engine executing before LLM diagnosis.

In accordance with ADR-003:
Evaluates known operational failure signatures deterministically. If a match
is found, root cause and recommended remediation are resolved immediately,
bypassing AI latency, cost, and hallucination risk.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RuleClassification:
    matched_rule: str
    root_cause: str
    confidence: float
    recommended_action: str
    severity: str  # P0, P1, P2, P3
    evidence: list[str]


class DeterministicRulesEngine:
    """Evaluates telemetry payload against deterministic failure rules."""

    def evaluate(self, context: dict[str, Any]) -> RuleClassification | None:
        """Evaluates operational context against known deterministic failure signatures."""

        # 1. PII Exposure Boundary Check (P0)
        if (
            context.get("unexpected_pii_column") is True
            or context.get("schema_change_type") == "PII_EXPOSURE"
        ):
            return RuleClassification(
                matched_rule="pii_column_detected",
                root_cause="PII_EXPOSURE_RISK",
                confidence=1.0,
                recommended_action="BLOCK_PIPELINE",
                severity="P0",
                evidence=[
                    f"Sensitive column '{context.get('pii_column_name', 'UNKNOWN')}' detected in incoming data feed."
                ],
            )

        # 2. Repeated failure pattern (P1)
        failures_24h = context.get("failure_count_last_24h", 0)
        if failures_24h >= 3:
            return RuleClassification(
                matched_rule="repeated_failure",
                root_cause="REPEATED_FAILURE",
                confidence=0.85,
                recommended_action="ESCALATE_TO_HUMAN",
                severity="P1",
                evidence=[
                    f"Pipeline failed {failures_24h} times in the last 24 hours. Exceeded auto-retry safety limits."
                ],
            )

        # 3. Schema Changes (Additive vs Breaking)
        schema_change = context.get("schema_change_type")
        if schema_change == "BREAKING":
            return RuleClassification(
                matched_rule="breaking_schema_change",
                root_cause="SCHEMA_BREAKING_CHANGE",
                confidence=0.99,
                recommended_action="QUARANTINE_BAD_RECORDS",
                severity="P1",
                evidence=[
                    "Breaking schema modification detected (incompatible type change or dropped required column)."
                ],
            )
        elif schema_change == "ADDITIVE":
            return RuleClassification(
                matched_rule="additive_schema_change",
                root_cause="SCHEMA_ADDITIVE_CHANGE",
                confidence=0.99,
                recommended_action="ADD_COLUMN_TO_STAGING",
                severity="P3",
                evidence=[
                    "Non-breaking additive schema expansion detected. Backward-compatible."
                ],
            )

        # 4. Checksum / Corrupted Source File
        if context.get("checksum_valid") is False:
            return RuleClassification(
                matched_rule="corrupted_source_file",
                root_cause="CORRUPTED_FILE",
                confidence=0.95,
                recommended_action="RELOAD_SOURCE_FILE",
                severity="P1",
                evidence=[
                    "Source payload failed checksum verification or parser integrity check."
                ],
            )

        # 5. Missing Partition
        if (
            context.get("partition_exists") is False
            and context.get("source_available") is True
        ):
            return RuleClassification(
                matched_rule="missing_partition",
                root_cause="MISSING_PARTITION",
                confidence=0.90,
                recommended_action="REPROCESS_PARTITION",
                severity="P2",
                evidence=[
                    f"Target partition {context.get('partition_date', '')} is missing but source files are verified available."
                ],
            )

        # 6. API Timeout / HTTP 5xx Gateway errors
        err_msg = str(context.get("error_message", ""))
        api_timeout_tokens = ["ReadTimeout", "ConnectionTimeout", "502", "503", "504"]
        if context.get("task_status") == "FAILED" and any(
            t in err_msg for t in api_timeout_tokens
        ):
            return RuleClassification(
                matched_rule="api_timeout",
                root_cause="API_TIMEOUT",
                confidence=0.95,
                recommended_action="RETRY_SOURCE_EXTRACTION",
                severity="P2",
                evidence=[
                    f"Upstream API extraction encountered gateway error or timeout: {err_msg[:120]}"
                ],
            )

        # 7. Transient Task Failure (OOM, Timeout, Connection Reset)
        err_type = context.get("error_type", "")
        retry_count = context.get("retry_count", 0)
        transient_types = ["TIMEOUT", "CONNECTION_RESET", "OUT_OF_MEMORY"]
        if (
            context.get("task_status") == "FAILED"
            and err_type in transient_types
            and retry_count < 3
        ):
            return RuleClassification(
                matched_rule="transient_task_failure",
                root_cause="TRANSIENT_TASK_FAILURE",
                confidence=0.95,
                recommended_action="RETRY_TASK",
                severity="P2",
                evidence=[
                    f"Task failed with transient error type '{err_type}' (retry count: {retry_count}/3)."
                ],
            )

        # 8. Freshness SLA Breach
        if (
            context.get("freshness_breach") is True
            and context.get("pipeline_running") is False
        ):
            return RuleClassification(
                matched_rule="freshness_sla_breach",
                root_cause="FRESHNESS_FAILURE",
                confidence=0.90,
                recommended_action="RERUN_FAILED_DAG",
                severity="P2",
                evidence=[
                    "Pipeline output breached freshness SLA deadline and no active DAG is running."
                ],
            )

        # No deterministic rule matched -> Escalate to AI diagnosis
        return None
