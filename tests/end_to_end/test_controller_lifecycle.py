"""End-to-end integration tests for ImmuneSystemController incident lifecycle."""

from agents.remediation_agent import ApprovalRecord
from src.controller.controller import ImmuneSystemController, IncidentState


class TestImmuneSystemControllerLifecycle:
    def setup_method(self):
        self.controller = ImmuneSystemController()

    def test_clean_pipeline_run_produces_resolved_without_incident(self):
        res = self.controller.handle_run_completion(
            pipeline_id="orders",
            run_id="run-clean-999",
            context={
                "task_status": "SUCCESS",
                "rows_written": 1000,
                "historical_row_counts": [1000, 1020, 990, 1005, 995, 1010, 1000],
            },
        )
        assert res.incident_id is None
        assert res.final_state == IncidentState.RESOLVED
        assert "zero anomalies" in res.message

    def test_full_autonomous_repair_flow(self):
        # Transient timeout scenario -> RETRY_TASK (Low Risk -> Auto-remediated -> Verified -> Learned)
        res = self.controller.handle_run_completion(
            pipeline_id="orders",
            run_id="run-transient-001",
            context={
                "task_status": "FAILED",
                "error_type": "TIMEOUT",
                "retry_count": 1,
                "post_repair_metrics": {
                    "rows_written": 1000,
                    "min_expected_rows": 900,
                    "null_ratio": 0.01,
                    "null_threshold": 0.05,
                    "duplicate_ratio": 0.005,
                    "duplicate_threshold": 0.02,
                },
            },
        )

        assert res.incident_id is not None
        assert res.final_state == IncidentState.RESOLVED
        assert res.detection.anomaly_type == "TRANSIENT_TASK_FAILURE"
        assert res.diagnosis.root_cause == "TRANSIENT_TASK_FAILURE"
        assert res.remediation.action_executed == "RETRY_TASK"
        assert res.verification.all_checks_passed is True

    def test_never_allow_action_is_hard_blocked(self):
        # PII exposure scenario -> Never-allow boundary violation
        res = self.controller.handle_run_completion(
            pipeline_id="orders",
            run_id="run-pii-999",
            context={
                "unexpected_pii_column": True,
                "pii_column_name": "credit_card_number",
            },
        )

        assert res.incident_id is not None
        assert res.final_state == IncidentState.BLOCKED
        assert res.risk.blocked is True
        assert res.remediation is None
        assert "BLOCKED" in res.message

    def test_high_risk_awaits_approval_then_remediates(self):
        # Breaking schema change scenario -> Requires human approval
        res_pending = self.controller.handle_run_completion(
            pipeline_id="orders",
            run_id="run-schema-drift",
            context={
                "schema_change_type": "BREAKING",
            },
            approval=None,
        )

        assert res_pending.final_state == IncidentState.ACTION_SELECTED
        assert res_pending.risk.requires_human_approval is True
        assert res_pending.remediation is None

        # Human operator signs off via dashboard
        approval = ApprovalRecord(
            incident_id=res_pending.incident_id,
            approved_by="data_lead@company.com",
            approved_at="2026-10-23T08:15:00Z",
            approval_id="appr-1234",
        )

        res_approved = self.controller.handle_run_completion(
            pipeline_id="orders",
            run_id="run-schema-drift",
            context={
                "schema_change_type": "BREAKING",
                "post_repair_metrics": {
                    "rows_written": 950,
                    "min_expected_rows": 900,
                    "null_ratio": 0.01,
                    "null_threshold": 0.05,
                    "duplicate_ratio": 0.005,
                    "duplicate_threshold": 0.02,
                },
            },
            approval=approval,
        )

        assert res_approved.final_state == IncidentState.RESOLVED
        assert res_approved.remediation.action_executed == "QUARANTINE_BAD_RECORDS"
        assert res_approved.verification.all_checks_passed is True
