# ==============================================================================
# Data Pipeline Immune System — Diagnosis Agent (Phase 6)
# ==============================================================================
"""Determines the most probable root cause of a detected pipeline incident.

Permissions: READ ONLY
Inputs: DetectionResult + incident_id
Outputs: DiagnosisResult with root_cause, confidence, evidence, recommended_action

Architecture:
- ADR-002: Read-only specialized agent.
- ADR-003: Rules engine runs before LLM.
- ADR-006: Incident memory similarity lookup for historical context.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from agents.detection_agent import DetectionResult
from src.config.settings import Settings, load_settings
from src.diagnosis.llm_client import LLMClient
from src.memory.incident_memory import HistoricalIncident, IncidentMemory

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DiagnosisInput:
    incident_id: str
    detection_result: DetectionResult
    affected_table: str = "orders_silver"


@dataclass(frozen=True)
class DiagnosisResult:
    incident_id: str
    root_cause: str
    affected_pipeline: str
    affected_table: str
    confidence: float
    evidence: List[str]
    recommended_action: str
    similar_incidents: List[str]
    diagnosed_at: str
    used_llm: bool


class DiagnosisAgent:
    """Determines the probable root cause of an incident."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        llm_client: Optional[LLMClient] = None,
        memory: Optional[IncidentMemory] = None,
    ):
        self.settings = settings or load_settings()
        self.llm = llm_client or LLMClient(
            model_name=self.settings.agents.llm_model,
            temperature=self.settings.agents.llm_temperature,
            max_tokens=self.settings.agents.llm_max_tokens,
        )
        self.memory = memory or IncidentMemory(dataset=self.settings.project.dataset)

    def diagnose(self, input_data: DiagnosisInput) -> DiagnosisResult:
        """Investigates incident symptoms and returns a diagnostic conclusion."""
        now_str = datetime.now(timezone.utc).isoformat()
        det = input_data.detection_result

        logger.info(
            "DiagnosisAgent evaluating incident %s for pipeline '%s'",
            input_data.incident_id,
            det.pipeline_id,
        )

        # 1. Query memory for past similar incidents (ADR-006)
        similar_past = self.memory.find_similar(
            pipeline_id=det.pipeline_id,
            incident_type=det.anomaly_type or "UNKNOWN",
            symptoms=det.evidence,
            limit=3,
        )
        similar_ids = [inc.incident_id for inc in similar_past]

        # 2. Check if Detection already resolved root cause deterministically (ADR-003)
        if det.recommended_action and det.confidence >= 0.90:
            logger.info("Using deterministic diagnosis for incident %s", input_data.incident_id)
            return DiagnosisResult(
                incident_id=input_data.incident_id,
                root_cause=det.anomaly_type or "DETERMINISTIC_FAILURE",
                affected_pipeline=det.pipeline_id,
                affected_table=input_data.affected_table,
                confidence=det.confidence,
                evidence=det.evidence,
                recommended_action=det.recommended_action,
                similar_incidents=similar_ids,
                diagnosed_at=now_str,
                used_llm=False,
            )

        # 3. Escalate to LLM reasoning if unknown / ambiguous pattern
        logger.info("Deterministic rule was ambiguous. Invoking LLM reasoning...")
        llm_res = self.llm.diagnose_failure(
            pipeline_id=det.pipeline_id,
            anomaly_type=det.anomaly_type or "UNKNOWN",
            evidence=det.evidence,
            similar_incidents=[{"id": s.incident_id, "cause": s.root_cause} for s in similar_past],
        )

        return DiagnosisResult(
            incident_id=input_data.incident_id,
            root_cause=llm_res.root_cause,
            affected_pipeline=det.pipeline_id,
            affected_table=input_data.affected_table,
            confidence=llm_res.confidence,
            evidence=llm_res.evidence,
            recommended_action=llm_res.recommended_action,
            similar_incidents=similar_ids,
            diagnosed_at=now_str,
            used_llm=True,
        )
