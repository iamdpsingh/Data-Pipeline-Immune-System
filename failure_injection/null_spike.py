# ==============================================================================
# Data Pipeline Immune System — Failure Injection: Null Spike
# ==============================================================================
"""Simulates a sudden surge in null values within mandatory data columns.

WHAT THIS SIMULATES:
  Upstream software release introduces a bug causing required fields
  (e.g., customer_id) to be sent as null/empty for 15-25% of records.

EXPECTED IMMUNE RESPONSE:
  1. Detection: DATA_QUALITY_FAILURE (Completeness threshold breached), P1
  2. Diagnosis: UPSTREAM_DATA_QUALITY_DEGRADATION
  3. Risk: MEDIUM
  4. Remediation: QUARANTINE_BAD_RECORDS
  5. Verification: Production silver table clean, bad records routed to dead-letter quarantine
  6. Resolution: RESOLVED
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import random
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)


def _check_injection_allowed() -> None:
    env = os.getenv("ENVIRONMENT", "production").lower()
    if env == "production":
        override = os.getenv("DPIS_ALLOW_INJECTION_IN_PRODUCTION")
        if override != "I_UNDERSTAND_THE_RISK":
            raise EnvironmentError("Failure injection is disabled in production.")


def inject_null_spike(source_file_path: str, column: str = "customer_id", null_percentage: float = 0.20) -> int:
    """Injects null values into designated column across a target percentage of rows."""
    _check_injection_allowed()
    path = Path(source_file_path)

    if not path.exists():
        records = [
            {"order_id": f"ORD-{i:04d}", "customer_id": f"CUST-{i:06d}", "total_amount": 50.0}
            for i in range(100)
        ]
    else:
        with open(path, "r", encoding="utf-8") as f:
            records = [json.loads(line) for line in f if line.strip()]

    null_count = int(len(records) * null_percentage)
    targets = random.sample(range(len(records)), null_count)

    for idx in targets:
        records[idx][column] = None

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    logger.info(
        "Injected null spike into '%s': %d of %d records (%.1f%%)",
        column,
        null_count,
        len(records),
        null_percentage * 100.0,
    )
    return null_count


def main() -> None:
    parser = argparse.ArgumentParser(description="Inject null spike into dataset.")
    parser.add_argument("--source-file", default="scratch/orders_sample.json")
    parser.add_argument("--column", default="customer_id")
    parser.add_argument("--percentage", type=float, default=20.0)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    inject_null_spike(args.source_file, args.column, args.percentage / 100.0)


if __name__ == "__main__":
    main()
