# ==============================================================================
# Data Pipeline Immune System — Pipeline Health Score Calculator
# ==============================================================================
"""Calculates daily multi-factor health scores for monitored data pipelines.

Aggregates operational telemetry into a composite score (0-100) based on:
- Reliability (run success rate)
- Freshness (data arrival timeliness vs SLA)
- Quality (data quality assertion pass rate)
- Schema Stability (rate of schema drift / alterations)
- SLA Compliance (execution duration vs budget)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class HealthStatus(str, Enum):
    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    DEGRADED = "DEGRADED"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class PipelineFactors:
    reliability: float  # 0.0 - 1.0 (success rate)
    freshness: float  # 0.0 - 1.0 (freshness SLA score)
    quality: float  # 0.0 - 1.0 (quality checks pass rate)
    schema_stability: float  # 0.0 - 1.0 (1.0 = stable, decreases per breaking change)
    sla_compliance: float  # 0.0 - 1.0 (duration SLA compliance)


@dataclass(frozen=True)
class HealthScoreResult:
    pipeline_id: str
    composite_score: float  # 0.0 - 100.0
    status: HealthStatus
    factors: PipelineFactors
    weights: dict[str, float]


class HealthScoreCalculator:
    """Calculates weighted composite health scores using environment configurations."""

    DEFAULT_WEIGHTS = {
        "reliability": 0.30,
        "freshness": 0.20,
        "quality": 0.20,
        "schema_stability": 0.15,
        "sla_compliance": 0.15,
    }

    DEFAULT_THRESHOLDS = {
        "healthy": 90,
        "warning": 75,
        "degraded": 50,
    }

    def __init__(
        self,
        weights: dict[str, float] | None = None,
        thresholds: dict[str, int] | None = None,
    ):
        self.weights = weights or self.DEFAULT_WEIGHTS
        self.thresholds = thresholds or self.DEFAULT_THRESHOLDS

    def calculate(
        self, pipeline_id: str, factors: PipelineFactors
    ) -> HealthScoreResult:
        """Computes composite score and health status tier."""
        score = (
            factors.reliability * self.weights.get("reliability", 0.30)
            + factors.freshness * self.weights.get("freshness", 0.20)
            + factors.quality * self.weights.get("quality", 0.20)
            + factors.schema_stability * self.weights.get("schema_stability", 0.15)
            + factors.sla_compliance * self.weights.get("sla_compliance", 0.15)
        ) * 100.0

        rounded_score = round(max(0.0, min(100.0, score)), 2)

        if rounded_score >= self.thresholds.get("healthy", 90):
            status = HealthStatus.HEALTHY
        elif rounded_score >= self.thresholds.get("warning", 75):
            status = HealthStatus.WARNING
        elif rounded_score >= self.thresholds.get("degraded", 50):
            status = HealthStatus.DEGRADED
        else:
            status = HealthStatus.CRITICAL

        return HealthScoreResult(
            pipeline_id=pipeline_id,
            composite_score=rounded_score,
            status=status,
            factors=factors,
            weights=dict(self.weights),
        )
