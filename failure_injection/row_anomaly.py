# ==============================================================================
# Data Pipeline Immune System — Failure Injection: Row Count Anomaly
# ==============================================================================
"""Simulates an incomplete upstream extraction delivering significantly fewer rows.

WHAT THIS SIMULATES:
  Upstream extraction returns partial response, delivering only a fraction of normal
  volume. Pipeline succeeds mechanically (no task crash), but volume breaches statistical baseline.

EXPECTED IMMUNE RESPONSE:
  1. Detection: ROW_COUNT_ANOMALY, P1
  2. Diagnosis: UPSTREAM_PARTIAL_LOAD (confidence ~0.90)
  3. Risk: LOW (RETRY_SOURCE_EXTRACTION is safe and idempotent)
  4. Remediation: RETRY_SOURCE_EXTRACTION
  5. Verification: Post-repair volume meets expected baseline (PASS)
  6. Resolution: RESOLVED
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import random
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)


def _check_injection_allowed() -> None:
    """Hard environment guard preventing execution in production."""
    env = os.getenv("ENVIRONMENT", "production").lower()
    if env == "production":
        override = os.getenv("DPIS_ALLOW_INJECTION_IN_PRODUCTION")
        if override != "I_UNDERSTAND_THE_RISK":
            raise EnvironmentError(
                "Failure injection is disabled in production. "
                "Set DPIS_ALLOW_INJECTION_IN_PRODUCTION=I_UNDERSTAND_THE_RISK to override."
            )
    logger.info("Environment guard verified: executing injection in environment '%s'", env)


def inject_row_drop(source_file_path: str, drop_percentage: float) -> int:
    """Truncates source dataset to simulate an incomplete extraction."""
    _check_injection_allowed()
    path = Path(source_file_path)
    if not path.exists():
        logger.warning("Target file %s does not exist on local disk. Creating synthetic sample.", path)
        records = [
            {"order_id": f"ORD-20261023-{i:04d}", "customer_id": f"CUST-000001", "total_amount": 100.0}
            for i in range(1000)
        ]
    else:
        with open(path, "r", encoding="utf-8") as f:
            records = [json.loads(line) for line in f if line.strip()]

    total_records = len(records)
    keep_count = int(total_records * (1.0 - drop_percentage))
    truncated = records[:keep_count]

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for rec in truncated:
            f.write(json.dumps(rec) + "\n")

    logger.info(
        "Injected row count drop of %.1f%%: reduced %d records -> %d records in %s",
        drop_percentage * 100.0,
        total_records,
        len(truncated),
        source_file_path,
    )
    return len(truncated)


def main() -> None:
    parser = argparse.ArgumentParser(description="Inject row count drop anomaly.")
    parser.add_argument("--source-file", default="scratch/orders_sample.json", help="Path to JSON file")
    parser.add_argument("--drop-percentage", type=float, default=48.0, help="Drop percentage (e.g. 48.0)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    inject_row_drop(args.source_file, args.drop_percentage / 100.0)


if __name__ == "__main__":
    main()
