"""Unit tests for DetectionAgent, DeterministicRulesEngine, and AdaptiveBaseline."""

from agents.detection_agent import DetectionAgent, DetectionInput
from src.config.settings import load_settings


class TestDetectionAgent:
    def setup_method(self):
        self.settings = load_settings("dev")
        self.agent = DetectionAgent(settings=self.settings)

    def test_clean_pipeline_run_no_anomaly(self):
        input_data = DetectionInput(
            pipeline_id="orders",
            run_id="run-clean-001",
            context={
                "task_status": "SUCCESS",
                "rows_written": 1000,
                "historical_row_counts": [980, 1020, 1010, 990, 1005, 995, 1015, 1000],
                "failed_quality_checks": [],
            },
        )
        res = self.agent.detect(input_data)
        assert res.is_anomaly is False
        assert res.incident_id is None
        assert res.anomaly_type is None

    def test_deterministic_transient_failure_rule(self):
        input_data = DetectionInput(
            pipeline_id="orders",
            run_id="run-err-001",
            context={
                "task_status": "FAILED",
                "error_type": "TIMEOUT",
                "retry_count": 1,
            },
        )
        res = self.agent.detect(input_data)
        assert res.is_anomaly is True
        assert res.anomaly_type == "TRANSIENT_TASK_FAILURE"
        assert res.severity == "P2"
        assert res.recommended_action == "RETRY_TASK"
        assert res.confidence == 0.95

    def test_deterministic_pii_column_rule(self):
        input_data = DetectionInput(
            pipeline_id="orders",
            run_id="run-pii-001",
            context={
                "unexpected_pii_column": True,
                "pii_column_name": "customer_ssn",
            },
        )
        res = self.agent.detect(input_data)
        assert res.is_anomaly is True
        assert res.anomaly_type == "PII_EXPOSURE_RISK"
        assert res.severity == "P0"
        assert res.recommended_action == "BLOCK_PIPELINE"
        assert res.confidence == 1.0

    def test_adaptive_row_count_anomaly_drop(self):
        # Normal history ~1000 rows. Today only 520 rows (48% drop)
        input_data = DetectionInput(
            pipeline_id="orders",
            run_id="run-drop-001",
            context={
                "rows_written": 520,
                "historical_row_counts": [1000, 1010, 995, 1005, 1000, 1020, 990, 1015],
            },
        )
        res = self.agent.detect(input_data)
        assert res.is_anomaly is True
        assert res.anomaly_type == "ROW_COUNT_ANOMALY"
        assert res.severity == "P1"
        assert res.recommended_action == "RETRY_SOURCE_EXTRACTION"
        assert "z-score" in res.evidence[0]
