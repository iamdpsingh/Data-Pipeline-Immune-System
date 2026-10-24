# ==============================================================================
# Data Pipeline Immune System — Data Quality Validation Engine
# ==============================================================================
"""Data quality validation engine executing deterministic metric checks.

Evaluates incoming batches and conformed tables against completeness,
uniqueness, numerical bounds, and categorical validity constraints.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum


class CheckType(str, Enum):
    COMPLETENESS = "COMPLETENESS"
    UNIQUENESS = "UNIQUENESS"
    VALIDITY = "VALIDITY"
    VOLUME = "VOLUME"
    SCHEMA = "SCHEMA"


class CheckStatus(str, Enum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


@dataclass(frozen=True)
class QualityCheckResult:
    quality_id: str
    pipeline_id: str
    table_name: str
    run_id: str
    check_name: str
    check_type: CheckType
    expected_value: float
    actual_value: float
    threshold: float
    status: CheckStatus
    severity: str  # P0, P1, P2, P3
    is_verification: bool
    timestamp: datetime


class DataQualityValidator:
    """Runs deterministic data quality assertions over table summary metrics."""

    def __init__(self, pipeline_id: str, table_name: str, run_id: str):
        self.pipeline_id = pipeline_id
        self.table_name = table_name
        self.run_id = run_id

    def check_null_ratio(
        self,
        column_name: str,
        null_count: int,
        total_count: int,
        threshold: float = 0.05,
        is_verification: bool = False,
    ) -> QualityCheckResult:
        """Evaluates null proportion against allowed tolerance."""
        ratio = (null_count / total_count) if total_count > 0 else 0.0
        status = CheckStatus.PASS if ratio <= threshold else CheckStatus.FAIL
        severity = (
            "P1"
            if ratio > (threshold * 3)
            else "P2" if status == CheckStatus.FAIL else "P3"
        )

        return QualityCheckResult(
            quality_id=f"chk-{uuid.uuid4().hex[:12]}",
            pipeline_id=self.pipeline_id,
            table_name=self.table_name,
            run_id=self.run_id,
            check_name=f"null_check_{column_name}",
            check_type=CheckType.COMPLETENESS,
            expected_value=0.0,
            actual_value=round(ratio, 4),
            threshold=threshold,
            status=status,
            severity=severity,
            is_verification=is_verification,
            timestamp=datetime.now(UTC),
        )

    def check_duplicate_ratio(
        self,
        key_column: str,
        duplicate_count: int,
        total_count: int,
        threshold: float = 0.02,
        is_verification: bool = False,
    ) -> QualityCheckResult:
        """Evaluates duplicate row proportion against allowed tolerance."""
        ratio = (duplicate_count / total_count) if total_count > 0 else 0.0
        status = CheckStatus.PASS if ratio <= threshold else CheckStatus.FAIL
        severity = (
            "P1" if ratio > 0.05 else "P2" if status == CheckStatus.FAIL else "P3"
        )

        return QualityCheckResult(
            quality_id=f"chk-{uuid.uuid4().hex[:12]}",
            pipeline_id=self.pipeline_id,
            table_name=self.table_name,
            run_id=self.run_id,
            check_name=f"duplicate_check_{key_column}",
            check_type=CheckType.UNIQUENESS,
            expected_value=0.0,
            actual_value=round(ratio, 4),
            threshold=threshold,
            status=status,
            severity=severity,
            is_verification=is_verification,
            timestamp=datetime.now(UTC),
        )

    def check_volume_bounds(
        self,
        actual_rows: int,
        expected_rows: int,
        lower_bound_pct: float = 0.80,
        upper_bound_pct: float = 1.20,
        is_verification: bool = False,
    ) -> QualityCheckResult:
        """Evaluates batch volume against historical baseline expectations."""
        ratio = (actual_rows / expected_rows) if expected_rows > 0 else 1.0
        is_pass = lower_bound_pct <= ratio <= upper_bound_pct
        status = CheckStatus.PASS if is_pass else CheckStatus.FAIL

        # Drops below 50% are critical (P1), minor variance is P2/P3
        severity = (
            "P1" if ratio < 0.50 else "P2" if status == CheckStatus.FAIL else "P3"
        )

        return QualityCheckResult(
            quality_id=f"chk-{uuid.uuid4().hex[:12]}",
            pipeline_id=self.pipeline_id,
            table_name=self.table_name,
            run_id=self.run_id,
            check_name="volume_bounds_check",
            check_type=CheckType.VOLUME,
            expected_value=float(expected_rows),
            actual_value=float(actual_rows),
            threshold=lower_bound_pct,
            status=status,
            severity=severity,
            is_verification=is_verification,
            timestamp=datetime.now(UTC),
        )
