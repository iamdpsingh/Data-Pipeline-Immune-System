# ==============================================================================
# Data Pipeline Immune System — Adaptive Baseline Engine (ADR-009)
# ==============================================================================
"""Calculates moving historical baselines from pipeline run telemetry.

In accordance with ADR-009:
Avoids brittle static thresholds by learning normal volume and duration
characteristics over a rolling lookback window. Falls back safely to static
percentage bounds when insufficient historical runs (< min_baseline_runs) exist.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from src.detection.statistics import StatisticalDetector

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BaselineEvaluation:
    is_anomaly: bool
    method_used: str  # 'ADAPTIVE_ZSCORE' or 'STATIC_FALLBACK'
    expected_value: float
    actual_value: float
    deviation_metric: float  # z-score or percentage ratio
    threshold: float
    evidence: str


class AdaptiveBaseline:
    """Computes moving metrics and evaluates new pipeline runs against baseline."""

    def __init__(
        self,
        min_baseline_runs: int = 7,
        lookback_days: int = 14,
        zscore_threshold: float = 3.0,
        static_lower_bound: float = 0.70,
        static_upper_bound: float = 1.30,
    ):
        self.min_baseline_runs = min_baseline_runs
        self.lookback_days = lookback_days
        self.zscore_threshold = zscore_threshold
        self.static_lower_bound = static_lower_bound
        self.static_upper_bound = static_upper_bound
        self.detector = StatisticalDetector(zscore_threshold=zscore_threshold)

    def evaluate_row_count(
        self,
        current_rows: int,
        historical_row_counts: list[int],
    ) -> BaselineEvaluation:
        """Evaluates whether current row volume is anomalous."""
        float_history = [float(x) for x in historical_row_counts]
        summary = self.detector.compute_summary(float_history)

        # Check if enough runs exist for statistical baseline
        if (
            summary
            and summary.count >= self.min_baseline_runs
            and summary.std_dev > 0.0
        ):
            is_anom, z_score = self.detector.is_zscore_anomaly(
                float(current_rows), summary.mean, summary.std_dev
            )
            evidence = (
                f"Observed {current_rows} rows vs historical mean {summary.mean} "
                f"(std_dev {summary.std_dev}, z-score {z_score}, threshold {self.zscore_threshold})"
            )
            return BaselineEvaluation(
                is_anomaly=is_anom,
                method_used="ADAPTIVE_ZSCORE",
                expected_value=summary.mean,
                actual_value=float(current_rows),
                deviation_metric=z_score,
                threshold=self.zscore_threshold,
                evidence=evidence,
            )

        # Fallback to static percentage threshold
        expected_ref = (
            summary.mean if summary and summary.count > 0 else float(current_rows)
        )
        ratio = (current_rows / expected_ref) if expected_ref > 0 else 1.0

        is_anom = ratio < self.static_lower_bound or ratio > self.static_upper_bound
        evidence = (
            f"Static baseline check: observed {current_rows} rows (ratio {ratio:.2f} of reference "
            f"{expected_ref:.0f}). Expected range [{self.static_lower_bound:.2f}, {self.static_upper_bound:.2f}]"
        )

        return BaselineEvaluation(
            is_anomaly=is_anom,
            method_used="STATIC_FALLBACK",
            expected_value=expected_ref,
            actual_value=float(current_rows),
            deviation_metric=round(ratio, 2),
            threshold=self.static_lower_bound,
            evidence=evidence,
        )
