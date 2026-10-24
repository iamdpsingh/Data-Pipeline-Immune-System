"""Unit tests for VerificationAgent and LearningAgent."""

from agents.detection_agent import DetectionResult
from agents.diagnosis_agent import DiagnosisResult
from agents.learning_agent import IncidentRecord, LearningAgent
from agents.remediation_agent import RemediationResult
from agents.verification_agent import VerificationAgent
from src.memory.incident_memory import IncidentMemory


class TestVerificationAgent:
    def setup_method(self):
        self.agent = VerificationAgent()
        self.det = DetectionResult(
            incident_id="inc-ver-001",
            anomaly_type="ROW_COUNT_ANOMALY",
            severity="P1",
            confidence=0.95,
            evidence=["Drop in rows"],
            pipeline_id="orders",
            run_id="run-001",
            detected_at="2026-10-23T08:00:00Z",
            is_anomaly=True,
            recommended_action="RETRY_SOURCE_EXTRACTION",
        )

    def test_verification_success_when_all_metrics_pass(self):
        rem = RemediationResult(
            incident_id="inc-ver-001",
            action_executed="RETRY_SOURCE_EXTRACTION",
            execution_status="SUCCESS",
            started_at="2026-10-23T08:05:00Z",
            completed_at="2026-10-23T08:06:00Z",
            details={},
        )

        post_metrics = {
            "rows_written": 1050,
            "min_expected_rows": 900,
            "null_ratio": 0.01,
            "null_threshold": 0.05,
            "duplicate_ratio": 0.005,
            "duplicate_threshold": 0.02,
        }

        res = self.agent.verify(
            "inc-ver-001", self.det, rem, post_repair_metrics=post_metrics
        )
        assert res.all_checks_passed is True
        assert len(res.check_results) == 3
        assert all(c.status == "PASS" for c in res.check_results)

    def test_verification_fails_when_null_threshold_breached(self):
        rem = RemediationResult(
            incident_id="inc-ver-001",
            action_executed="RETRY_SOURCE_EXTRACTION",
            execution_status="SUCCESS",
            started_at="2026-10-23T08:05:00Z",
            completed_at="2026-10-23T08:06:00Z",
            details={},
        )

        # High null ratio after retry
        post_metrics = {
            "rows_written": 1050,
            "min_expected_rows": 900,
            "null_ratio": 0.12,  # 12% nulls exceeds 5% threshold
            "null_threshold": 0.05,
            "duplicate_ratio": 0.005,
            "duplicate_threshold": 0.02,
        }

        res = self.agent.verify(
            "inc-ver-001", self.det, rem, post_repair_metrics=post_metrics
        )
        assert res.all_checks_passed is False
        assert any(
            c.status == "FAIL" and "null" in c.check_name for c in res.check_results
        )

    def test_verification_fails_if_remediation_failed(self):
        rem = RemediationResult(
            incident_id="inc-ver-001",
            action_executed="RETRY_SOURCE_EXTRACTION",
            execution_status="FAILED",
            started_at="2026-10-23T08:05:00Z",
            completed_at="2026-10-23T08:06:00Z",
            details={},
        )

        res = self.agent.verify("inc-ver-001", self.det, rem)
        assert res.all_checks_passed is False
        assert res.check_results[0].status == "FAIL"


class TestLearningAgent:
    def test_store_record_updates_memory(self):
        memory = IncidentMemory()
        agent = LearningAgent(memory=memory)

        det = DetectionResult(
            incident_id="inc-learn-001",
            anomaly_type="ROW_COUNT_ANOMALY",
            severity="P1",
            confidence=0.95,
            evidence=["Drop in rows"],
            pipeline_id="orders",
            run_id="run-001",
            detected_at="2026-10-23T08:00:00Z",
            is_anomaly=True,
            recommended_action="RETRY_SOURCE_EXTRACTION",
        )
        diag = DiagnosisResult(
            incident_id="inc-learn-001",
            root_cause="UPSTREAM_PARTIAL_LOAD",
            affected_pipeline="orders",
            affected_table="orders_silver",
            confidence=0.95,
            evidence=["Source dropped rows"],
            recommended_action="RETRY_SOURCE_EXTRACTION",
            similar_incidents=[],
            diagnosed_at="2026-10-23T08:01:00Z",
            used_llm=False,
        )
        rem = RemediationResult(
            incident_id="inc-learn-001",
            action_executed="RETRY_SOURCE_EXTRACTION",
            execution_status="SUCCESS",
            started_at="2026-10-23T08:02:00Z",
            completed_at="2026-10-23T08:03:00Z",
            details={},
        )

        rec = IncidentRecord(
            incident_id="inc-learn-001",
            pipeline_id="orders",
            environment="dev",
            detection=det,
            diagnosis=diag,
            remediation=rem,
            verification=None,
            resolution_time_minutes=3.5,
        )

        success = agent.store(rec)
        assert success is True

        similar = memory.find_similar("orders", "ROW_COUNT_ANOMALY", ["Drop in rows"])
        assert len(similar) == 1
        assert similar[0].incident_id == "inc-learn-001"
        assert similar[0].root_cause == "UPSTREAM_PARTIAL_LOAD"
