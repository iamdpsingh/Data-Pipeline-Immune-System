"""
Verification Agent

Confirms that remediation actually fixed the problem — not just that
the pipeline finished running.

Permissions: READ ONLY
Inputs: DetectionResult (original) + RemediationResult
Outputs: VerificationResult with per-check results

A pipeline finishing successfully is necessary but not sufficient for
declaring an incident resolved. The verification agent re-runs the
same quality checks that originally detected the anomaly, plus any
additional checks relevant to the specific remediation applied.

Only if all checks pass is all_checks_passed = True returned.
The controller then transitions the incident to RESOLVED.

If any check fails, the controller decides whether to:
  - Re-diagnose (the remediation may have partially worked but revealed a deeper issue)
  - Try a different action
  - Escalate to human

The Verification Agent does not make that decision — it only reports.

For the verification check methodology, see docs/flow.md section 7.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from src.config.loader import AgentConfig
from src.observability.bigquery_client import BigQueryClient
from src.validation.quality_checks import QualityCheckRunner
from agents.detection_agent import DetectionResult
from agents.remediation_agent import RemediationResult

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CheckResult:
    check_name: str
    expected: str | float
    actual: str | float
    status: str  # PASS, FAIL, WARN
    details: str


@dataclass(frozen=True)
class VerificationResult:
    incident_id: str
    all_checks_passed: bool
    check_results: list[CheckResult]
    verified_at: str


class VerificationAgent:
    """
    Confirms remediation success through data quality re-checks.

    Permissions: READ ONLY
    """

    def __init__(self, config: AgentConfig, bq_client: BigQueryClient):
        self.config = config
        self.bq = bq_client
        self.quality_runner = QualityCheckRunner(bq_client, config.quality)

    def verify(
        self,
        incident_id: str,
        original_detection: DetectionResult,
        remediation_result: RemediationResult,
    ) -> VerificationResult:
        """
        Re-run quality checks post-remediation and return the result.
        Does not transition any incident state — the controller handles that.
        """
        raise NotImplementedError("Verification agent implementation pending — Phase 9")
