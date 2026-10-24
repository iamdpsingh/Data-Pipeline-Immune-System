"""Unit tests for RiskAgent evaluating risk tiers and never-allow boundaries."""

from agents.diagnosis_agent import DiagnosisResult
from agents.risk_agent import RiskAgent, RiskInput, RiskLevel


class TestRiskAgent:
    def setup_method(self):
        self.agent = RiskAgent()

    def test_never_allow_action_is_blocked(self):
        diag_res = DiagnosisResult(
            incident_id="inc-risk-001",
            root_cause="CORRUPTED_TABLE",
            affected_pipeline="orders",
            affected_table="orders_silver",
            confidence=0.99,  # High confidence cannot bypass never-allow
            evidence=["Table corrupted"],
            recommended_action="DELETE_PRODUCTION_TABLE",
            similar_incidents=[],
            diagnosed_at="2026-10-23T08:00:00Z",
            used_llm=False,
        )

        res = self.agent.assess(
            RiskInput(incident_id="inc-risk-001", diagnosis_result=diag_res)
        )
        assert res.risk_level == RiskLevel.NEVER_ALLOW
        assert res.blocked is True
        assert res.auto_remediable is False
        assert "never-allow" in res.block_reason.lower()

    def test_low_risk_action_is_auto_remediable(self):
        diag_res = DiagnosisResult(
            incident_id="inc-risk-002",
            root_cause="TRANSIENT_TASK_FAILURE",
            affected_pipeline="orders",
            affected_table="orders_silver",
            confidence=0.95,
            evidence=["Timeout error"],
            recommended_action="RETRY_TASK",
            similar_incidents=[],
            diagnosed_at="2026-10-23T08:00:00Z",
            used_llm=False,
        )

        res = self.agent.assess(
            RiskInput(incident_id="inc-risk-002", diagnosis_result=diag_res)
        )
        assert res.risk_level == RiskLevel.LOW
        assert res.auto_remediable is True
        assert res.requires_human_approval is False
        assert res.blocked is False

    def test_high_risk_action_requires_human_approval(self):
        diag_res = DiagnosisResult(
            incident_id="inc-risk-003",
            root_cause="SCHEMA_BREAKING_CHANGE",
            affected_pipeline="orders",
            affected_table="orders_silver",
            confidence=0.99,
            evidence=["Breaking change"],
            recommended_action="SCHEMA_BREAKING_CHANGE",
            similar_incidents=[],
            diagnosed_at="2026-10-23T08:00:00Z",
            used_llm=False,
        )

        res = self.agent.assess(
            RiskInput(incident_id="inc-risk-003", diagnosis_result=diag_res)
        )
        assert res.risk_level == RiskLevel.HIGH
        assert res.auto_remediable is False
        assert res.requires_human_approval is True
        assert res.blocked is False
