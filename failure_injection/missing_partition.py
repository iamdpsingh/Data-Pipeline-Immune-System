# ==============================================================================
# Data Pipeline Immune System — Failure Injection: Missing Partition
# ==============================================================================
"""Simulates a missing daily partition in the data landing zone.

WHAT THIS SIMULATES:
  A scheduled daily partition was skipped or delayed during overnight landing.

EXPECTED IMMUNE RESPONSE:
  1. Detection: MISSING_PARTITION, P2
  2. Diagnosis: MISSING_PARTITION (confidence 0.90)
  3. Risk: LOW
  4. Remediation: REPROCESS_PARTITION (safe, idempotent backfill)
  5. Verification: Partition exists and row count > 0 (PASS)
  6. Resolution: RESOLVED
"""

from __future__ import annotations

import argparse
import logging
import os
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


def _check_injection_allowed() -> None:
    env = os.getenv("ENVIRONMENT", "production").lower()
    if env == "production":
        override = os.getenv("DPIS_ALLOW_INJECTION_IN_PRODUCTION")
        if override != "I_UNDERSTAND_THE_RISK":
            raise OSError("Failure injection is disabled in production.")


def inject_missing_partition(partition_dir: str) -> None:
    """Removes or moves partition directory to simulate missing data partition."""
    _check_injection_allowed()
    path = Path(partition_dir)
    backup_path = Path(f"{partition_dir}_backup")

    if path.exists():
        shutil.move(str(path), str(backup_path))
        logger.info("Simulated missing partition by moving %s -> %s", path, backup_path)
    else:
        logger.info(
            "Partition directory %s does not exist; ready to test missing partition detection.",
            path,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulate missing partition.")
    parser.add_argument("--partition-dir", default="scratch/landing/2026-10-23")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    inject_missing_partition(args.partition_dir)


if __name__ == "__main__":
    main()
