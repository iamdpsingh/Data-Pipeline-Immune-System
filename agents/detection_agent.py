# ==============================================================================
# Data Pipeline Immune System — Detection Agent (Phase 5)
# ==============================================================================
"""Identifies abnormal pipeline behaviour by comparing run telemetry against baselines.

Permissions: READ ONLY
Inputs: pipeline_id, run_id, telemetry_context
Outputs: DetectionResult with anomaly type, severity, confidence, evidence

Architecture:
- ADR-002: Specialised read-only agent.
- ADR-003: Deterministic rules engine evaluated before any AI diagnosis.
- ADR-009: Adaptive baselines for row count / metrics to handle natural variance.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from src.config.settings import Settings, load_settings
from src.detection.baseline import AdaptiveBaseline
from src.detection.rules_engine import DeterministicRulesEngine, RuleClassification
from src.detection.schema_comparator import SchemaComparator

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DetectionInput:
    pipeline_id: str
    run_id: str
    context: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DetectionResult:
    incident_id: str | None
    anomaly_type: str | None
    severity: str | None
    confidence: float
    evidence: list[str]
    pipeline_id: str
    run_id: str
    detected_at: str
    is_anomaly: bool
    recommended_action: str | None = None


class DetectionAgent:
    """Identifies abnormal pipeline behaviour using deterministic rules and adaptive baselines."""

    def __init__(
        self,
        settings: Settings | None = None,
        bq_client: Any | None = None,
    ):
        self.settings = settings or load_settings()
        self.bq = bq_client
        self.rules_engine = DeterministicRulesEngine()
        self.baseline = AdaptiveBaseline(
            min_baseline_runs=self.settings.detection.min_baseline_runs,
            lookback_days=self.settings.detection.baseline_lookback_days,
            zscore_threshold=self.settings.detection.row_count_zscore_threshold,
            static_lower_bound=self.settings.quality.volume_lower_bound,
            static_upper_bound=self.settings.quality.volume_upper_bound,
        )
        self.schema_comparator = SchemaComparator()

    def detect(self, input_data: DetectionInput) -> DetectionResult:
        """Runs all detection checks for a completed pipeline run."""
        now_str = datetime.now(UTC).isoformat()
        ctx = input_data.context

        logger.info(
            "DetectionAgent analyzing pipeline=%s run=%s",
            input_data.pipeline_id,
            input_data.run_id,
        )

        # 1. Evaluate deterministic failure rules (ADR-003)
        rule_match: RuleClassification | None = self.rules_engine.evaluate(ctx)
        if rule_match:
            incident_id = f"inc-{uuid.uuid4().hex[:12]}"
            logger.warning(
                "Deterministic rule matched: %s (Severity: %s, Action: %s)",
                rule_match.matched_rule,
                rule_match.severity,
                rule_match.recommended_action,
            )
            return DetectionResult(
                incident_id=incident_id,
                anomaly_type=rule_match.root_cause,
                severity=rule_match.severity,
                confidence=rule_match.confidence,
                evidence=rule_match.evidence,
                pipeline_id=input_data.pipeline_id,
                run_id=input_data.run_id,
                detected_at=now_str,
                is_anomaly=True,
                recommended_action=rule_match.recommended_action,
            )

        # 2. Evaluate volume metrics against adaptive baseline (ADR-009)
        current_rows = ctx.get("rows_written") or ctx.get("rows_read")
        history = ctx.get("historical_row_counts")

        if current_rows is not None and history is not None:
            eval_res = self.baseline.evaluate_row_count(int(current_rows), history)
            if eval_res.is_anomaly:
                incident_id = f"inc-{uuid.uuid4().hex[:12]}"
                # Drops are severe (P1), spikes are warning (P2)
                severity = "P1" if current_rows < eval_res.expected_value else "P2"
                return DetectionResult(
                    incident_id=incident_id,
                    anomaly_type="ROW_COUNT_ANOMALY",
                    severity=severity,
                    confidence=0.92,
                    evidence=[eval_res.evidence],
                    pipeline_id=input_data.pipeline_id,
                    run_id=input_data.run_id,
                    detected_at=now_str,
                    is_anomaly=True,
                    recommended_action=(
                        "RETRY_SOURCE_EXTRACTION"
                        if severity == "P1"
                        else "INVESTIGATE_VOLUME_SPIKE"
                    ),
                )

        # 3. Data quality check failure evaluation
        failed_checks = ctx.get("failed_quality_checks", [])
        if failed_checks:
            incident_id = f"inc-{uuid.uuid4().hex[:12]}"
            worst_severity = (
                "P1" if any(c.get("severity") == "P1" for c in failed_checks) else "P2"
            )
            evidence = [
                f"Check '{c.get('check_name')}' failed (actual {c.get('actual_value')} > threshold {c.get('threshold')})"
                for c in failed_checks
            ]
            return DetectionResult(
                incident_id=incident_id,
                anomaly_type="DATA_QUALITY_FAILURE",
                severity=worst_severity,
                confidence=0.98,
                evidence=evidence,
                pipeline_id=input_data.pipeline_id,
                run_id=input_data.run_id,
                detected_at=now_str,
                is_anomaly=True,
                recommended_action="QUARANTINE_BAD_RECORDS",
            )

        # No anomaly detected — clean run
        return DetectionResult(
            incident_id=None,
            anomaly_type=None,
            severity=None,
            confidence=1.0,
            evidence=["All telemetry within acceptable thresholds."],
            pipeline_id=input_data.pipeline_id,
            run_id=input_data.run_id,
            detected_at=now_str,
            is_anomaly=False,
        )
