"""
Learning Agent

Stores resolved incidents in incident_memory so future diagnoses can
benefit from historical patterns.

Permissions: WRITE to incident_memory table ONLY
Inputs: Full incident record (detection + diagnosis + remediation + verification)
Outputs: None (side effect: record written to BigQuery)

The Learning Agent is the last step in the incident lifecycle. It runs
after the Verification Agent confirms success and before the incident
is marked RESOLVED.

If the Learning Agent fails to write, the incident can still be closed.
A memory write failure is logged and alerted but is non-blocking. We
don't want a memory system failure to prevent incident closure.

The memory this agent builds is used by the Diagnosis Agent for
similarity-based root cause recommendations. It becomes meaningful
after ~50 resolved incidents.

For how memory is queried during diagnosis, see src/memory/incident_memory.py.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from src.config.loader import AgentConfig
from src.observability.bigquery_client import BigQueryClient
from agents.detection_agent import DetectionResult
from agents.diagnosis_agent import DiagnosisResult
from agents.remediation_agent import RemediationResult
from agents.verification_agent import VerificationResult

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
    """
    Stores resolved incidents in memory for future diagnosis.

    Permissions: WRITE to incident_memory only.
    """

    def __init__(self, config: AgentConfig, bq_client: BigQueryClient):
        self.config = config
        self.bq = bq_client

    def store(self, record: IncidentRecord) -> None:
        """
        Write a resolved incident to incident_memory.

        Non-blocking — failures are logged but do not raise.
        The caller (controller) should not depend on this succeeding.
        """
        raise NotImplementedError("Learning agent implementation pending — Phase 10")
