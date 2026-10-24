# ==============================================================================
# Data Pipeline Immune System — Immune System Controller (ADR-002, ADR-010)
# ==============================================================================
"""Central orchestrator driving the autonomous incident lifecycle.

In accordance with ADR-002 and ADR-010:
Maintains the complete state machine across specialized agents:
Detection -> Diagnosis -> Risk Assessment -> Remediation -> Verification -> Learning
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from agents.detection_agent import DetectionAgent, DetectionInput, DetectionResult
from agents.diagnosis_agent import DiagnosisAgent, DiagnosisInput, DiagnosisResult
from agents.learning_agent import IncidentRecord, LearningAgent
from agents.remediation_agent import ApprovalRecord, RemediationAgent, RemediationResult
from agents.risk_agent import RiskAgent, RiskAssessment, RiskInput
from agents.verification_agent import VerificationAgent, VerificationResult
from src.config.settings import Settings, load_settings
from src.controller.states import IncidentState, transition
from src.observability.audit_logger import AuditLogger

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IncidentLifecycleResult:
    incident_id: str | None
    pipeline_id: str
    run_id: str
    final_state: IncidentState
    detection: DetectionResult | None
    diagnosis: DiagnosisResult | None
    risk: RiskAssessment | None
    remediation: RemediationResult | None
    verification: VerificationResult | None
    message: str


class ImmuneSystemController:
    """Orchestrates the full incident lifecycle across specialized agents."""

    def __init__(
        self,
        settings: Settings | None = None,
        audit_logger: AuditLogger | None = None,
        detection_agent: DetectionAgent | None = None,
        diagnosis_agent: DiagnosisAgent | None = None,
        risk_agent: RiskAgent | None = None,
        remediation_agent: RemediationAgent | None = None,
        verification_agent: VerificationAgent | None = None,
        learning_agent: LearningAgent | None = None,
    ):
        self.settings = settings or load_settings()
        bq_client = None
        try:
            from google.cloud import bigquery

            bq_client = bigquery.Client(project=self.settings.project.id)
        except Exception:
            bq_client = None
        self.audit = audit_logger or AuditLogger(
            dataset=self.settings.project.dataset,
            bq_client=bq_client,
        )
        self.detection = detection_agent or DetectionAgent(self.settings)
        self.diagnosis = diagnosis_agent or DiagnosisAgent(self.settings)
        self.risk = risk_agent or RiskAgent(self.settings)
        self.remediation = remediation_agent or RemediationAgent(self.settings)
        self.verification = verification_agent or VerificationAgent(self.settings)
        self.learning = learning_agent or LearningAgent(self.settings)

    def handle_run_completion(
        self,
        pipeline_id: str,
        run_id: str,
        context: dict[str, Any] | None = None,
        approval: ApprovalRecord | None = None,
    ) -> IncidentLifecycleResult:
        """Main entrypoint executed on pipeline run completion."""
        ctx = context or {}
        logger.info(
            "Immune controller evaluating completion for %s (run %s)",
            pipeline_id,
            run_id,
        )

        # 1. Detection Phase
        det_input = DetectionInput(pipeline_id=pipeline_id, run_id=run_id, context=ctx)
        det_res = self.detection.detect(det_input)

        if not det_res.is_anomaly or not det_res.incident_id:
            logger.info(
                "Pipeline %s run %s completed cleanly. No incident created.",
                pipeline_id,
                run_id,
            )
            return IncidentLifecycleResult(
                incident_id=None,
                pipeline_id=pipeline_id,
                run_id=run_id,
                final_state=IncidentState.RESOLVED,
                detection=det_res,
                diagnosis=None,
                risk=None,
                remediation=None,
                verification=None,
                message="Pipeline run healthy; zero anomalies detected.",
            )

        incident_id = det_res.incident_id
        current_state = IncidentState.DETECTED

        self.audit.record_event(
            pipeline_id=pipeline_id,
            run_id=run_id,
            agent_name="DetectionAgent",
            action_type="ANOMALY_DETECTED",
            details={"type": det_res.anomaly_type, "severity": det_res.severity},
            incident_id=incident_id,
        )

        current_state = transition(current_state, IncidentState.CLASSIFIED)

        # 2. Diagnosis Phase
        diag_input = DiagnosisInput(incident_id=incident_id, detection_result=det_res)
        diag_res = self.diagnosis.diagnose(diag_input)
        current_state = transition(current_state, IncidentState.DIAGNOSED)

        self.audit.record_event(
            pipeline_id=pipeline_id,
            run_id=run_id,
            agent_name="DiagnosisAgent",
            action_type="ROOT_CAUSE_DIAGNOSED",
            details={"cause": diag_res.root_cause, "confidence": diag_res.confidence},
            incident_id=incident_id,
        )

        # 3. Risk Assessment Phase
        risk_input = RiskInput(incident_id=incident_id, diagnosis_result=diag_res)
        risk_res = self.risk.assess(risk_input)
        current_state = transition(current_state, IncidentState.RISK_ASSESSED)

        self.audit.record_event(
            pipeline_id=pipeline_id,
            run_id=run_id,
            agent_name="RiskAgent",
            action_type="RISK_ASSESSED",
            details={
                "level": risk_res.risk_level.value,
                "auto": risk_res.auto_remediable,
            },
            incident_id=incident_id,
        )

        # Check for hard block (Never-Allow boundary violation)
        if risk_res.blocked:
            current_state = transition(current_state, IncidentState.BLOCKED)
            self.audit.record_event(
                pipeline_id=pipeline_id,
                run_id=run_id,
                agent_name="RiskAgent",
                action_type="INCIDENT_BLOCKED",
                details={"reason": risk_res.block_reason},
                incident_id=incident_id,
                status="BLOCKED",
            )
            return IncidentLifecycleResult(
                incident_id=incident_id,
                pipeline_id=pipeline_id,
                run_id=run_id,
                final_state=current_state,
                detection=det_res,
                diagnosis=diag_res,
                risk=risk_res,
                remediation=None,
                verification=None,
                message=f"Incident BLOCKED: {risk_res.block_reason}",
            )

        # Check if human authorization is required
        if risk_res.requires_human_approval and approval is None:
            current_state = transition(current_state, IncidentState.ACTION_SELECTED)
            logger.warning(
                "Incident %s requires human operator authorization before proceeding.",
                incident_id,
            )
            return IncidentLifecycleResult(
                incident_id=incident_id,
                pipeline_id=pipeline_id,
                run_id=run_id,
                final_state=current_state,
                detection=det_res,
                diagnosis=diag_res,
                risk=risk_res,
                remediation=None,
                verification=None,
                message="Action selected. Awaiting human operator sign-off.",
            )

        # 4. Remediation Phase
        current_state = transition(current_state, IncidentState.ACTION_SELECTED)
        current_state = transition(current_state, IncidentState.REMEDIATION)

        rem_res = self.remediation.remediate(
            risk_assessment=risk_res,
            approval=approval,
            execution_context=ctx,
        )

        self.audit.record_event(
            pipeline_id=pipeline_id,
            run_id=run_id,
            agent_name="RemediationAgent",
            action_type="REMEDIATION_EXECUTED",
            details=rem_res.details,
            incident_id=incident_id,
        )

        # 5. Verification Phase (ADR-005)
        current_state = transition(current_state, IncidentState.VERIFICATION)
        ver_res = self.verification.verify(
            incident_id=incident_id,
            original_detection=det_res,
            remediation_result=rem_res,
            post_repair_metrics=ctx.get("post_repair_metrics"),
        )

        self.audit.record_event(
            pipeline_id=pipeline_id,
            run_id=run_id,
            agent_name="VerificationAgent",
            action_type="REPAIR_VERIFIED",
            details={"passed": ver_res.all_checks_passed},
            incident_id=incident_id,
        )

        # 6. Resolution or Escalation
        if ver_res.all_checks_passed:
            current_state = transition(current_state, IncidentState.RESOLVED)

            # 7. Learning Phase (ADR-006)
            self.learning.store(
                IncidentRecord(
                    incident_id=incident_id,
                    pipeline_id=pipeline_id,
                    environment=self.settings.environment,
                    detection=det_res,
                    diagnosis=diag_res,
                    remediation=rem_res,
                    verification=ver_res,
                    resolution_time_minutes=1.5,
                )
            )

            return IncidentLifecycleResult(
                incident_id=incident_id,
                pipeline_id=pipeline_id,
                run_id=run_id,
                final_state=current_state,
                detection=det_res,
                diagnosis=diag_res,
                risk=risk_res,
                remediation=rem_res,
                verification=ver_res,
                message="Incident fully auto-remediated, verified, and learned.",
            )
        else:
            current_state = transition(current_state, IncidentState.ESCALATED)
            return IncidentLifecycleResult(
                incident_id=incident_id,
                pipeline_id=pipeline_id,
                run_id=run_id,
                final_state=current_state,
                detection=det_res,
                diagnosis=diag_res,
                risk=risk_res,
                remediation=rem_res,
                verification=ver_res,
                message="Post-repair verification failed. Incident escalated to human engineer.",
            )
