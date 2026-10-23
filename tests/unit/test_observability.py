"""Unit tests for pipeline health score calculator and structured audit logger."""

import pytest
from src.observability.audit_logger import AuditLogger
from src.observability.health_score import (
    HealthScoreCalculator,
    HealthStatus,
    PipelineFactors,
)


class TestHealthScoreCalculator:
    def setup_method(self):
        self.calculator = HealthScoreCalculator()

    def test_perfect_health_score(self):
        factors = PipelineFactors(
            reliability=1.0,
            freshness=1.0,
            quality=1.0,
            schema_stability=1.0,
            sla_compliance=1.0,
        )
        res = self.calculator.calculate("orders", factors)
        assert res.composite_score == 100.0
        assert res.status == HealthStatus.HEALTHY

    def test_warning_health_score(self):
        # Degraded quality and freshness
        factors = PipelineFactors(
            reliability=0.90,
            freshness=0.70,
            quality=0.75,
            schema_stability=1.0,
            sla_compliance=0.85,
        )
        res = self.calculator.calculate("orders", factors)
        assert 75.0 <= res.composite_score < 90.0
        assert res.status == HealthStatus.WARNING

    def test_critical_health_score(self):
        # Major pipeline failures
        factors = PipelineFactors(
            reliability=0.20,
            freshness=0.10,
            quality=0.40,
            schema_stability=0.50,
            sla_compliance=0.30,
        )
        res = self.calculator.calculate("orders", factors)
        assert res.composite_score < 50.0
        assert res.status == HealthStatus.CRITICAL


class TestAuditLogger:
    def test_record_event_buffers_locally(self):
        logger = AuditLogger(dataset="dpis_dev")
        evt = logger.record_event(
            pipeline_id="orders",
            run_id="run-123",
            agent_name="DetectionAgent",
            action_type="ANOMALY_DETECTED",
            details={"metric": "row_count", "zscore": 3.4},
            status="SUCCESS",
        )
        assert evt.pipeline_id == "orders"
        assert evt.agent_name == "DetectionAgent"
        assert len(logger.get_events()) == 1
        assert logger.get_events()[0].event_id == evt.event_id

        logger.clear()
        assert len(logger.get_events()) == 0
