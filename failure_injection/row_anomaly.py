"""
Failure injection: row count anomaly

Simulates an incomplete source extraction — the pipeline receives
significantly fewer records than expected.

WHAT THIS SIMULATES:
  The upstream API returns a partial response, delivering only a fraction
  of the expected daily records. The pipeline itself succeeds (no task failure),
  but the output row count is far below the historical baseline.

EXPECTED IMMUNE SYSTEM RESPONSE:
  1. Detection: ROW_COUNT_ANOMALY, P1
  2. Diagnosis: UPSTREAM_PARTIAL_LOAD (confidence ~0.90)
  3. Risk: LOW (RETRY_SOURCE_EXTRACTION is a low-risk action)
  4. Remediation: RETRY_SOURCE_EXTRACTION
  5. Verification: all checks pass after reprocessing
  6. Resolution: RESOLVED

DO NOT RUN IN PRODUCTION:
  This script has a hard environment guard. Set ENVIRONMENT=dev or ENVIRONMENT=staging.

USAGE:
  python failure_injection/row_anomaly.py --pipeline orders --drop-percentage 48
  python failure_injection/row_anomaly.py --pipeline orders --drop-percentage 20 --severity P3

VERIFYING THE RESPONSE:
  After running, check:
    SELECT incident_id, status, root_cause, confidence
    FROM dpis_dev.incidents
    WHERE pipeline_id = 'orders'
    ORDER BY detected_at DESC
    LIMIT 1;

  Expected: status = RESOLVED, root_cause = UPSTREAM_PARTIAL_LOAD
"""

import argparse
import os
import sys
import logging
import random
from pathlib import Path

logger = logging.getLogger(__name__)


def _check_injection_allowed() -> None:
    """
    Hard environment guard. Failure injection must never run in production
    unless someone has explicitly set the override variable, knows what they're
    doing, and has accepted the risk in writing (metaphorically).
    """
    env = os.getenv("ENVIRONMENT", "production")
    if env == "production":
        override = os.getenv("DPIS_ALLOW_INJECTION_IN_PRODUCTION")
        if override != "I_UNDERSTAND_THE_RISK":
            raise EnvironmentError(
                "Failure injection is disabled in production. "
                "Set DPIS_ALLOW_INJECTION_IN_PRODUCTION=I_UNDERSTAND_THE_RISK to override. "
                "Think carefully before doing that."
            )
    logger.info("Environment check passed: running in %s", env)


def inject_row_drop(pipeline_id: str, drop_percentage: float) -> None:
    """
    Truncate the source dataset to simulate a partial extraction.

    Writes a modified source file to GCS with only (1 - drop_percentage)
    of the normal record count. The file is otherwise valid — no schema
    changes, no corrupted records.

    The immune system should detect this as a row count anomaly and diagnose
    UPSTREAM_PARTIAL_LOAD based on the source file record count vs expected.
    """
    raise NotImplementedError("Row anomaly injection pending — Phase 11")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inject a row count anomaly into a pipeline source."
    )
    parser.add_argument("--pipeline", required=True, help="Pipeline ID (e.g., orders)")
    parser.add_argument(
        "--drop-percentage",
        type=float,
        required=True,
        help="Percentage of rows to drop (0-100). 48 = drop 48% of rows.",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    _check_injection_allowed()
    inject_row_drop(args.pipeline, args.drop_percentage / 100)


if __name__ == "__main__":
    main()
