# ==============================================================================
# Data Pipeline Immune System — Failure Injection: Schema Drift
# ==============================================================================
"""Simulates schema mutations at the source feed (additive, breaking, or PII).

WHAT THIS SIMULATES:
  Upstream source alters schema:
  - Additive: New non-breaking field (e.g. phone VARCHAR(20))
  - Breaking: Mutating column types or dropping mandatory fields
  - PII: Injecting sensitive fields (SSN, credit card)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict

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


def inject_additive_schema_change(source_file_path: str, column: str, default_val: Any = "N/A") -> None:
    """Adds a new non-breaking column to the landing dataset."""
    _check_injection_allowed()
    path = Path(source_file_path)
    records = _load_or_create_records(path)

    for rec in records:
        rec[column] = default_val

    _write_records(path, records)
    logger.info("Injected additive column '%s' into %s (%d records)", column, source_file_path, len(records))


def inject_breaking_schema_change(source_file_path: str, column: str, new_val_type: str = "string") -> None:
    """Mutates an existing column's data type to create an incompatible schema."""
    _check_injection_allowed()
    path = Path(source_file_path)
    records = _load_or_create_records(path)

    for rec in records:
        if column in rec:
            rec[column] = "CORRUPTED_TYPE_VAL" if new_val_type == "string" else None

    _write_records(path, records)
    logger.info("Injected breaking type change on column '%s' into %s", column, source_file_path)


def inject_pii_column(source_file_path: str, column: str = "customer_ssn") -> None:
    """Adds a sensitive PII column triggering immediate P0 never-allow block."""
    _check_injection_allowed()
    path = Path(source_file_path)
    records = _load_or_create_records(path)

    for rec in records:
        rec[column] = "000-12-3456"

    _write_records(path, records)
    logger.critical("Injected sensitive PII column '%s' into %s (P0 TRIGGER)", column, source_file_path)


def _load_or_create_records(path: Path) -> list[Dict[str, Any]]:
    if not path.exists():
        return [
            {"order_id": f"ORD-20261023-{i:04d}", "customer_id": f"CUST-{i:06d}", "total_amount": 99.5}
            for i in range(100)
        ]
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _write_records(path: Path, records: list[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Inject schema drift anomaly.")
    parser.add_argument("--source-file", default="scratch/orders_sample.json")
    parser.add_argument("--type", choices=["additive", "breaking", "pii"], required=True)
    parser.add_argument("--column", default="phone")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    if args.type == "additive":
        inject_additive_schema_change(args.source_file, args.column)
    elif args.type == "breaking":
        inject_breaking_schema_change(args.source_file, args.column)
    elif args.type == "pii":
        inject_pii_column(args.source_file, args.column)


if __name__ == "__main__":
    main()
