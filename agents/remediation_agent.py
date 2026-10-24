# ==============================================================================
# Data Pipeline Immune System — Remediation Agent (Phase 8)
# ==============================================================================
"""Executes approved corrective actions.

Permissions: LIMITED WRITE (strictly to approved action library)
Inputs: RiskAssessment + optional ApprovalRecord (required for HIGH risk)
Outputs: RemediationResult

Architecture:
- ADR-002: Limited write permissions restricted to pre-approved handlers.
- ADR-004: Never executes never-allow actions.
- Least privilege: Cannot run arbitrary SQL or alter unauthorized resources.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from agents.risk_agent import RiskAssessment
from src.config.settings import Settings, load_settings
from src.remediation.actions import ActionLibrary
from src.remediation.exceptions import RemediationNotAuthorisedError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RemediationResult:
    incident_id: str
    action_executed: str
    execution_status: str  # SUCCESS, FAILED, PARTIAL
    started_at: str
    completed_at: str
    details: dict[str, Any]


@dataclass(frozen=True)
class ApprovalRecord:
    incident_id: str
    approved_by: str
    approved_at: str
    approval_id: str


class RemediationAgent:
    """Executes corrective actions from the approved action library."""

    def __init__(
        self,
        settings: Settings | None = None,
        bq_client: Any | None = None,
        action_library: ActionLibrary | None = None,
    ):
        self.settings = settings or load_settings()
        self.bq = bq_client
        self.action_library = action_library or ActionLibrary(bq_client)

    def remediate(
        self,
        risk_assessment: RiskAssessment,
        approval: ApprovalRecord | None = None,
        execution_context: dict[str, Any] | None = None,
    ) -> RemediationResult:
        """Executes the authorized remediation action."""
        started_at = datetime.now(UTC).isoformat()
        action = risk_assessment.approved_action or ""

        # 1. Check if action is blocked by never-allow rules
        if risk_assessment.blocked:
            raise RemediationNotAuthorisedError(
                f"Action '{action}' is BLOCKED by never-allow policy. Reason: {risk_assessment.block_reason}"
            )

        # 2. Check human approval requirement
        if risk_assessment.requires_human_approval and approval is None:
            raise RemediationNotAuthorisedError(
                f"Action '{action}' requires human approval before execution, but no ApprovalRecord was provided."
            )

        # 3. Check if action exists in approved library
        if not self.action_library.is_action_supported(action):
            raise RemediationNotAuthorisedError(
                f"Action '{action}' is not present in approved action library."
            )

        logger.info(
            "RemediationAgent executing '%s' for incident %s (Approval: %s)",
            action,
            risk_assessment.incident_id,
            approval.approval_id if approval else "AUTOMATIC",
        )

        details = dict(execution_context or {})
        details["incident_id"] = risk_assessment.incident_id

        # Execute idempotent action
        exec_outcome = self.action_library.execute(action, details)
        completed_at = datetime.now(UTC).isoformat()

        return RemediationResult(
            incident_id=risk_assessment.incident_id,
            action_executed=action,
            execution_status=exec_outcome.get("status", "SUCCESS"),
            started_at=started_at,
            completed_at=completed_at,
            details=exec_outcome,
        )
