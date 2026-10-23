"""Unit tests for DiagnosisAgent and IncidentMemory."""

import pytest
from agents.detection_agent import DetectionResult
from agents.diagnosis_agent import DiagnosisAgent, DiagnosisInput
from src.memory.incident_memory import IncidentMemory


class TestDiagnosisAgent:
    def setup_method(self):
        self.memory = IncidentMemory()
        # Seed memory with a past incident
        self.memory.record_resolution(
            incident_id="inc-past-001",
            pipeline_id="orders",
            incident_type="ROW_COUNT_ANOMALY",
            symptoms=["z-score drop", "incomplete records"],
            root_cause="UPSTREAM_PARTIAL_LOAD",
            resolution_action="RETRY_SOURCE_EXTRACTION",
            outcome="SUCCESS",
        )
        self.agent = DiagnosisAgent(memory=self.memory)

    def test_deterministic_diagnosis_passthrough(self):
        det_res = DetectionResult(
            incident_id="inc-det-001",
            anomaly_type="TRANSIENT_TASK_FAILURE",
            severity="P2",
            confidence=0.95,
            evidence=["Task failed with TIMEOUT."],
            pipeline_id="orders",
            run_id="run-101",
            detected_at="2026-10-23T08:00:00Z",
            is_anomaly=True,
            recommended_action="RETRY_TASK",
        )

        diag_input = DiagnosisInput(incident_id="inc-det-001", detection_result=det_res)
        res = self.agent.diagnose(diag_input)

        assert res.incident_id == "inc-det-001"
        assert res.root_cause == "TRANSIENT_TASK_FAILURE"
        assert res.confidence == 0.95
        assert res.used_llm is False
        assert res.recommended_action == "RETRY_TASK"

    def test_llm_diagnosis_when_ambiguous(self):
        # Ambiguous detection with low confidence
        det_res = DetectionResult(
            incident_id="inc-amb-002",
            anomaly_type="ROW_COUNT_ANOMALY",
            severity="P1",
            confidence=0.60,  # Below 0.90 threshold
            evidence=["Observed 500 rows vs historical mean 1000 with sudden z-score drop."],
            pipeline_id="orders",
            run_id="run-102",
            detected_at="2026-10-23T08:00:00Z",
            is_anomaly=True,
            recommended_action="RETRY_SOURCE_EXTRACTION",
        )

        diag_input = DiagnosisInput(incident_id="inc-amb-002", detection_result=det_res)
        res = self.agent.diagnose(diag_input)

        assert res.used_llm is True
        assert res.root_cause == "UPSTREAM_PARTIAL_LOAD"
        assert "inc-past-001" in res.similar_incidents
