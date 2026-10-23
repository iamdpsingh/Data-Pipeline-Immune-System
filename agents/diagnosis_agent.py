"""
Diagnosis Agent

Determines the most probable root cause of a detected incident by
investigating pipeline metadata, run history, quality results, and
historical incident memory.

Permissions: READ ONLY
Inputs: DetectionResult + incident_id
Outputs: DiagnosisResult with root_cause, confidence, evidence, recommended_action

The agent first checks the deterministic rule engine (detection_rules.yaml).
Only if no rule matches does it invoke the LLM with a structured context prompt.
The LLM cannot write anything — it only produces a structured JSON response
that the agent validates and returns to the controller.

For the investigation methodology and root cause taxonomy,
see docs/architecture/agent-architecture.md.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from src.config.loader import AgentConfig
from src.observability.bigquery_client import BigQueryClient
from src.diagnosis.rule_engine import RuleEngine
from src.diagnosis.llm_client import LLMClient
from src.memory.incident_memory import IncidentMemory
from agents.detection_agent import DetectionResult

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DiagnosisInput:
    incident_id: str
    detection_result: DetectionResult


@dataclass(frozen=True)
class DiagnosisResult:
    incident_id: str
    root_cause: str
    affected_pipeline: str
    affected_table: str
    confidence: float
    evidence: list[str]
    recommended_action: str
    similar_incidents: list[str]  # incident IDs from memory, for traceability
    diagnosed_at: str
    used_llm: bool  # whether LLM was invoked (False = deterministic rule matched)


class DiagnosisAgent:
    """
    Determines the probable root cause of an incident.

    Permissions: READ ONLY
    """

    def __init__(
        self,
        config: AgentConfig,
        bq_client: BigQueryClient,
        llm_client: LLMClient,
        memory: IncidentMemory,
    ):
        self.config = config
        self.bq = bq_client
        self.rule_engine = RuleEngine(config.diagnosis)
        self.llm = llm_client
        self.memory = memory

    def diagnose(self, input: DiagnosisInput) -> DiagnosisResult:
        """
        Investigate the incident and produce a root cause diagnosis.

        Returns root_cause = UNKNOWN with confidence < 0.5 if evidence
        is insufficient. The controller treats UNKNOWN as requiring human review.
        """
        raise NotImplementedError("Diagnosis agent implementation pending — Phase 6")
