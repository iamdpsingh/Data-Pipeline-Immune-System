# ==============================================================================
# Data Pipeline Immune System — Learning Agent (Phase 10)
# ==============================================================================
"""Stores resolved incidents in memory so future diagnoses benefit from historical patterns.

Permissions: WRITE to incident_memory table ONLY
Inputs: Full incident record (detection + diagnosis + remediation + verification)
Outputs: None (side effect: record written to IncidentMemory and BigQuery)

Architecture:
- ADR-002: Least-privilege write restricted strictly to memory tables.
- ADR-006: Builds corpus for similarity-based root cause search.
- Non-blocking: Memory storage failure is logged but never prevents incident resolution.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from agents.detection_agent import DetectionResult
from agents.diagnosis_agent import DiagnosisResult
from agents.remediation_agent import RemediationResult
from agents.verification_agent import VerificationResult
from src.config.settings import Settings, load_settings
from src.memory.incident_memory import IncidentMemory

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IncidentRecord:
    """Full incident record passed to the Learning Agent for storage."""

    incident_id: str
    pipeline_id: str
    environment: str
    detection: DetectionResult
    diagnosis: DiagnosisResult
    remediation: RemediationResult | None
    verification: VerificationResult | None
    resolution_time_minutes: float


class LearningAgent:
    """Stores resolved incidents in memory for future similarity diagnosis."""

    def __init__(
        self,
        settings: Settings | None = None,
        bq_client: Any | None = None,
        memory: IncidentMemory | None = None,
    ):
        self.settings = settings or load_settings()
        self.bq = bq_client
        self.memory = memory or IncidentMemory(
            dataset=self.settings.project.dataset, bq_client=bq_client
        )

    def store(self, record: IncidentRecord) -> bool:
        """Writes a resolved incident to incident memory.

        Non-blocking: any exception is caught and logged to ensure the
        incident lifecycle completes safely.
        """
        try:
            action = (
                record.remediation.action_executed
                if record.remediation
                else "MANUAL_INTERVENTION"
            )
            symptoms = record.detection.evidence + record.diagnosis.evidence

            self.memory.record_resolution(
                incident_id=record.incident_id,
                pipeline_id=record.pipeline_id,
                incident_type=record.detection.anomaly_type or "UNKNOWN",
                symptoms=symptoms,
                root_cause=record.diagnosis.root_cause,
                resolution_action=action,
                outcome=(
                    "SUCCESS"
                    if (record.verification and record.verification.all_checks_passed)
                    else "PARTIAL"
                ),
            )

            logger.info(
                "[LearningAgent] Incident %s successfully committed to incident memory (MTTR: %.1fm)",
                record.incident_id,
                record.resolution_time_minutes,
            )
            return True
        except Exception as exc:
            logger.error(
                "[LearningAgent] Non-blocking failure recording incident %s to memory: %s",
                record.incident_id,
                exc,
            )
            return False
