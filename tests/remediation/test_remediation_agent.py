"""Unit tests for RemediationAgent and ActionLibrary."""

import pytest
from agents.remediation_agent import ApprovalRecord, RemediationAgent
from agents.risk_agent import RiskAssessment, RiskLevel
from src.remediation.exceptions import RemediationNotAuthorisedError


class TestRemediationAgent:
    def setup_method(self):
        self.agent = RemediationAgent()

    def test_auto_remediate_low_risk_success(self):
        risk = RiskAssessment(
            incident_id="inc-rem-001",
            risk_level=RiskLevel.LOW,
            auto_remediable=True,
            requires_human_approval=False,
            blocked=False,
            block_reason=None,
            approved_action="RETRY_TASK",
            assessed_at="2026-10-23T08:00:00Z",
        )

        res = self.agent.remediate(risk, execution_context={"task_id": "ingest_orders"})
        assert res.incident_id == "inc-rem-001"
        assert res.action_executed == "RETRY_TASK"
        assert res.execution_status == "SUCCESS"

    def test_blocked_action_raises_exception(self):
        risk = RiskAssessment(
            incident_id="inc-rem-002",
            risk_level=RiskLevel.NEVER_ALLOW,
            auto_remediable=False,
            requires_human_approval=False,
            blocked=True,
            block_reason="Never allow violation",
            approved_action="DELETE_PRODUCTION_TABLE",
            assessed_at="2026-10-23T08:00:00Z",
        )

        with pytest.raises(RemediationNotAuthorisedError, match="BLOCKED by never-allow policy"):
            self.agent.remediate(risk)

    def test_high_risk_without_approval_raises_exception(self):
        risk = RiskAssessment(
            incident_id="inc-rem-003",
            risk_level=RiskLevel.HIGH,
            auto_remediable=False,
            requires_human_approval=True,
            blocked=False,
            block_reason=None,
            approved_action="QUARANTINE_BAD_RECORDS",
            assessed_at="2026-10-23T08:00:00Z",
        )

        with pytest.raises(RemediationNotAuthorisedError, match="requires human approval"):
            self.agent.remediate(risk, approval=None)

    def test_high_risk_with_approval_succeeds(self):
        risk = RiskAssessment(
            incident_id="inc-rem-004",
            risk_level=RiskLevel.HIGH,
            auto_remediable=False,
            requires_human_approval=True,
            blocked=False,
            block_reason=None,
            approved_action="QUARANTINE_BAD_RECORDS",
            assessed_at="2026-10-23T08:00:00Z",
        )

        approval = ApprovalRecord(
            incident_id="inc-rem-004",
            approved_by="lead_data_engineer@company.com",
            approved_at="2026-10-23T08:05:00Z",
            approval_id="appr-987",
        )

        res = self.agent.remediate(risk, approval=approval)
        assert res.execution_status == "SUCCESS"
        assert res.action_executed == "QUARANTINE_BAD_RECORDS"
