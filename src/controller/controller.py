"""
ImmuneSystemController

The central orchestrator for the incident lifecycle. This is the only component
that knows the complete state of an incident — agents receive specific inputs
and return specific outputs, but they don't talk to each other.

The controller:
  1. Receives pipeline run completion events
  2. Calls the Detection Agent
  3. If anomaly found, creates an incident in BigQuery
  4. Calls the Diagnosis Agent
  5. Calls the Risk Agent
  6. Routes: auto-proceed or wait for human approval
  7. Calls the Remediation Agent
  8. Calls the Verification Agent
  9. Closes or escalates the incident
  10. Calls the Learning Agent

Every state transition is written to BigQuery before the next step.
If the controller restarts mid-incident (Cloud Run cold start, OOM, etc.),
it reads the current state from BigQuery and continues from where it left off.

The controller fails loudly when agents fail. It does not silently assume
everything is fine if an agent returns an unexpected error. Instead it:
  - Logs the failure with full context
  - Transitions the incident to ESCALATED
  - Sends an alert
  - Returns — it does not retry silently

For the full incident state machine, see src/controller/states.py.
For the complete flow, see docs/flow.md.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from src.config.loader import AppConfig
from src.observability.bigquery_client import BigQueryClient
from src.controller.states import IncidentState, transition
from agents.detection_agent import DetectionAgent, DetectionInput
from agents.diagnosis_agent import DiagnosisAgent
from agents.risk_agent import RiskAgent, RiskLevel
from agents.remediation_agent import RemediationAgent
from agents.verification_agent import VerificationAgent
from agents.learning_agent import LearningAgent

logger = logging.getLogger(__name__)


class ImmuneSystemController:
    """
    Orchestrates the full incident lifecycle from detection to resolution.

    This is a stateless service — all state lives in BigQuery. Instantiate
    it per request in Cloud Run.
    """

    def __init__(
        self,
        config: AppConfig,
        bq: BigQueryClient,
        detection_agent: DetectionAgent,
        diagnosis_agent: DiagnosisAgent,
        risk_agent: RiskAgent,
        remediation_agent: RemediationAgent,
        verification_agent: VerificationAgent,
        learning_agent: LearningAgent,
    ):
        self.config = config
        self.bq = bq
        self.detection = detection_agent
        self.diagnosis = diagnosis_agent
        self.risk = risk_agent
        self.remediation = remediation_agent
        self.verification = verification_agent
        self.learning = learning_agent

    def handle_run_completion(self, pipeline_id: str, run_id: str) -> None:
        """
        Entry point — called after a pipeline run completes.

        Runs detection and, if an anomaly is found, drives the full
        incident lifecycle through to resolution.
        """
        raise NotImplementedError("Controller implementation pending — Phase 5+")

    def resume_incident(self, incident_id: str) -> None:
        """
        Resume an in-progress incident from the current BigQuery state.
        Called when the controller restarts and finds an open incident.
        """
        raise NotImplementedError("Controller implementation pending — Phase 5+")
