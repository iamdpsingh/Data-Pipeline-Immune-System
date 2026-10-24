# ==============================================================================
# Data Pipeline Immune System — Statistical Anomaly Detection (ADR-009)
# ==============================================================================
"""Statistical anomaly detection applying z-score and IQR methods.

In accordance with ADR-009:
Uses adaptive statistical distribution analysis over historical metrics to
distinguish natural variance from real operational failures.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class StatisticalSummary:
    count: int
    mean: float
    std_dev: float
    median: float
    q25: float
    q75: float


class StatisticalDetector:
    """Calculates statistical deviation and flags anomalous outliers."""

    def __init__(self, zscore_threshold: float = 3.0):
        self.zscore_threshold = zscore_threshold

    @staticmethod
    def compute_summary(values: list[float]) -> StatisticalSummary | None:
        """Calculates basic parametric and non-parametric summary metrics."""
        if not values:
            return None

        n = len(values)
        mean_val = sum(values) / n

        variance = sum((x - mean_val) ** 2 for x in values) / n if n > 1 else 0.0
        std_val = math.sqrt(variance)

        sorted_vals = sorted(values)
        mid = n // 2
        median_val = (
            (sorted_vals[mid - 1] + sorted_vals[mid]) / 2.0
            if n % 2 == 0
            else float(sorted_vals[mid])
        )

        q25_idx = int(0.25 * n)
        q75_idx = int(0.75 * n)
        q25_val = float(sorted_vals[q25_idx])
        q75_val = float(sorted_vals[q75_idx])

        return StatisticalSummary(
            count=n,
            mean=round(mean_val, 2),
            std_dev=round(std_val, 2),
            median=round(median_val, 2),
            q25=round(q25_val, 2),
            q75=round(q75_val, 2),
        )

    def is_zscore_anomaly(
        self, value: float, mean: float, std_dev: float
    ) -> tuple[bool, float]:
        """Checks if a metric point exceeds the z-score threshold.

        Returns:
            Tuple of (is_anomaly, computed_zscore)
        """
        if std_dev <= 0.0:
            # Zero variance: any deviation is considered anomalous if value != mean
            is_anom = abs(value - mean) > 0.0
            return is_anom, 999.0 if is_anom else 0.0

        z_score = abs(value - mean) / std_dev
        return z_score > self.zscore_threshold, round(z_score, 2)
