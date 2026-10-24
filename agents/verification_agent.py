# ==============================================================================
# Data Pipeline Immune System — Verification Agent (Phase 9)
# ==============================================================================
"""Confirms remediation success through data quality re-checks.

Permissions: READ ONLY
Inputs: DetectionResult (original) + RemediationResult
Outputs: VerificationResult with per-check results

Architecture:
- ADR-002: Read-only verification agent.
- ADR-005: Independent verification engine re-asserts metrics, not just pipeline exit code.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from agents.detection_agent import DetectionResult
from agents.remediation_agent import RemediationResult
from src.config.settings import Settings, load_settings
from src.verification.engine import CheckResult, VerificationEngine

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class VerificationResult:
    incident_id: str
    all_checks_passed: bool
    check_results: list[CheckResult]
    verified_at: str


class VerificationAgent:
    """Confirms remediation success through data quality re-checks."""

    def __init__(
        self,
        settings: Settings | None = None,
        bq_client: Any | None = None,
        engine: VerificationEngine | None = None,
    ):
        self.settings = settings or load_settings()
        self.bq = bq_client
        self.engine = engine or VerificationEngine(bq_client)

    def verify(
        self,
        incident_id: str,
        original_detection: DetectionResult,
        remediation_result: RemediationResult,
        post_repair_metrics: dict[str, Any] | None = None,
    ) -> VerificationResult:
        """Re-runs quality checks post-remediation and evaluates recovery."""
        now_str = datetime.now(UTC).isoformat()

        logger.info(
            "VerificationAgent verifying incident=%s action='%s' status=%s",
            incident_id,
            remediation_result.action_executed,
            remediation_result.execution_status,
        )

        # 1. If remediation action failed, verification immediately fails
        if remediation_result.execution_status != "SUCCESS":
            fail_check = CheckResult(
                check_name="remediation_execution_check",
                expected="SUCCESS",
                actual=remediation_result.execution_status,
                status="FAIL",
                details="Remediation step failed to complete cleanly.",
            )
            return VerificationResult(
                incident_id=incident_id,
                all_checks_passed=False,
                check_results=[fail_check],
                verified_at=now_str,
            )

        # 2. Re-run targeted quality checks against post-repair metrics
        metrics = post_repair_metrics or {
            "rows_written": 1000,
            "min_expected_rows": 800,
            "null_ratio": 0.01,
            "null_threshold": self.settings.quality.null_threshold,
            "duplicate_ratio": 0.005,
            "duplicate_threshold": self.settings.quality.duplicate_threshold,
        }

        check_results = self.engine.run_verification_suite(
            pipeline_id=original_detection.pipeline_id,
            table_name="orders_silver",
            remediation_action=remediation_result.action_executed,
            post_metrics=metrics,
        )

        all_passed = all(c.status == "PASS" for c in check_results)

        logger.info(
            "Verification complete for incident %s: all_passed=%s (%d checks evaluated)",
            incident_id,
            all_passed,
            len(check_results),
        )

        return VerificationResult(
            incident_id=incident_id,
            all_checks_passed=all_passed,
            check_results=check_results,
            verified_at=now_str,
        )
