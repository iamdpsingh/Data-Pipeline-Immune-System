# ==============================================================================
# Data Pipeline Immune System — Failure Injection: Duplicate Spike
# ==============================================================================
"""Simulates an upstream replay or dual-delivery event producing duplicate primary keys.

WHAT THIS SIMULATES:
  Message queue retry or dual publish delivers duplicated order records.

EXPECTED IMMUNE RESPONSE:
  1. Detection: DATA_QUALITY_FAILURE (Uniqueness threshold breached), P2
  2. Diagnosis: UPSTREAM_DUPLICATE_DELIVERY
  3. Risk: LOW
  4. Remediation: Deduplication via Window ranking in Silver transformation
  5. Verification: Silver table zero duplicates (PASS)
  6. Resolution: RESOLVED
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import random
from pathlib import Path

logger = logging.getLogger(__name__)


def _check_injection_allowed() -> None:
    env = os.getenv("ENVIRONMENT", "production").lower()
    if env == "production":
        override = os.getenv("DPIS_ALLOW_INJECTION_IN_PRODUCTION")
        if override != "I_UNDERSTAND_THE_RISK":
            raise OSError("Failure injection is disabled in production.")


def inject_duplicate_spike(
    source_file_path: str, duplicate_percentage: float = 0.15
) -> int:
    """Clones random records to simulate upstream duplicate broadcast."""
    _check_injection_allowed()
    path = Path(source_file_path)

    if not path.exists():
        records = [
            {
                "order_id": f"ORD-{i:04d}",
                "customer_id": f"CUST-{i:06d}",
                "total_amount": 50.0,
            }
            for i in range(100)
        ]
    else:
        with open(path, encoding="utf-8") as f:
            records = [json.loads(line) for line in f if line.strip()]

    dup_count = int(len(records) * duplicate_percentage)
    sampled = random.sample(records, dup_count)
    combined = records + sampled

    random.shuffle(combined)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in combined:
            f.write(json.dumps(r) + "\n")

    logger.info(
        "Injected duplicate spike: added %d duplicated rows to %s (total %d)",
        dup_count,
        source_file_path,
        len(combined),
    )
    return dup_count


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inject duplicate rows into source file."
    )
    parser.add_argument("--source-file", default="scratch/orders_sample.json")
    parser.add_argument("--percentage", type=float, default=15.0)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    inject_duplicate_spike(args.source_file, args.percentage / 100.0)


if __name__ == "__main__":
    main()
