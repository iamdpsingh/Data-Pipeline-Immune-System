"""
Remediation Agent

Executes approved corrective actions. This is the only agent with write
permissions, and those permissions are strictly limited to pre-defined
action handlers.

Permissions: LIMITED WRITE (approved action library only)
Inputs: RiskAssessment + optional ApprovalRecord (required for HIGH risk)
Outputs: RemediationResult

Every action executed by this agent:
  - Must be in the approved action library (src/remediation/actions.py)
  - Must have a corresponding entry in rules/remediation_rules.yaml
  - Must be idempotent (safe to retry if the first attempt fails)
  - Must produce an audit record in remediation_actions table

The agent CANNOT:
  - Execute arbitrary SQL
  - Modify IAM permissions
  - Write to silver or gold tables directly
  - Delete production tables
  - Run any action not in the approved library

If called without a valid RiskAssessment in hand, it raises an exception.
This is intentional — the agent must never run unsanctioned.

For the full list of approved actions, see rules/remediation_rules.yaml.
For the safety boundaries, see src/risk/never_allow.py.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from src.config.loader import AgentConfig
from src.observability.bigquery_client import BigQueryClient
from src.remediation.actions import ActionLibrary
from agents.risk_agent import RiskAssessment

logger = logging.getLogger(__name__)


@dataclass
class RemediationResult:
    incident_id: str
    action_executed: str
    execution_status: str  # SUCCESS, FAILED, PARTIAL
    started_at: str
    completed_at: str
    details: dict


@dataclass(frozen=True)
class ApprovalRecord:
    incident_id: str
    approved_by: str
    approved_at: str
    approval_id: str


class RemediationAgent:
    """
    Executes corrective actions from the approved action library.

    Permissions: LIMITED WRITE
    """

    def __init__(self, config: AgentConfig, bq_client: BigQueryClient):
        self.config = config
        self.bq = bq_client
        self.action_library = ActionLibrary(config, bq_client)

    def remediate(
        self,
        risk_assessment: RiskAssessment,
        approval: ApprovalRecord | None = None,
    ) -> RemediationResult:
        """
        Execute the approved remediation action.

        Raises RemediationNotAuthorisedError if:
          - risk_assessment.blocked is True
          - risk_assessment.requires_human_approval is True and approval is None
          - The action is not in the approved library
        """
        raise NotImplementedError("Remediation agent implementation pending — Phase 8")
