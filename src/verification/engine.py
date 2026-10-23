# ==============================================================================
# Data Pipeline Immune System — Verification Engine (ADR-005)
# ==============================================================================
"""Post-remediation health assertion engine.

In accordance with ADR-005:
Verification re-executes data quality and volume checks against the repaired
dataset to guarantee data correctness before resolving an incident.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CheckResult:
    check_name: str
    expected: str | float
    actual: str | float
    status: str  # PASS, FAIL, WARN
    details: str


class VerificationEngine:
    """Re-runs quality assertions and asserts health restoration."""

    def __init__(self, bq_client: Any = None):
        self.bq = bq_client

    def run_verification_suite(
        self,
        pipeline_id: str,
        table_name: str,
        remediation_action: str,
        post_metrics: Dict[str, Any],
    ) -> List[CheckResult]:
        """Runs targeted post-repair verification checks."""
        results: List[CheckResult] = []

        # 1. Row volume check
        rows = post_metrics.get("rows_written", 0)
        min_expected = post_metrics.get("min_expected_rows", 1)
        row_status = "PASS" if rows >= min_expected else "FAIL"
        results.append(
            CheckResult(
                check_name="row_count_post_repair",
                expected=f">= {min_expected}",
                actual=rows,
                status=row_status,
                details=f"Observed {rows} rows after applying {remediation_action}.",
            )
        )

        # 2. Null check on primary keys
        null_ratio = post_metrics.get("null_ratio", 0.0)
        null_thresh = post_metrics.get("null_threshold", 0.05)
        null_status = "PASS" if null_ratio <= null_thresh else "FAIL"
        results.append(
            CheckResult(
                check_name="null_ratio_post_repair",
                expected=f"<= {null_thresh}",
                actual=null_ratio,
                status=null_status,
                details=f"Null ratio is {null_ratio:.4f} (threshold: {null_thresh}).",
            )
        )

        # 3. Duplicate check
        dup_ratio = post_metrics.get("duplicate_ratio", 0.0)
        dup_thresh = post_metrics.get("duplicate_threshold", 0.02)
        dup_status = "PASS" if dup_ratio <= dup_thresh else "FAIL"
        results.append(
            CheckResult(
                check_name="duplicate_ratio_post_repair",
                expected=f"<= {dup_thresh}",
                actual=dup_ratio,
                status=dup_status,
                details=f"Duplicate ratio is {dup_ratio:.4f} (threshold: {dup_thresh}).",
            )
        )

        return results
