"""
Failure injection: schema drift

Simulates schema changes at the source — either additive (new column added)
or breaking (existing column type changed or column removed).

WHAT THIS SIMULATES:
  An upstream system changes the schema of the data it delivers. This is
  one of the most common real-world pipeline failures and one of the most
  dangerous because it can silently corrupt data if undetected.

SCENARIOS:

  Additive (non-breaking):
    Source adds a new column, e.g., `phone VARCHAR(20)`.
    Expected response: P3, auto-handle by updating staging schema.

  Breaking (type change):
    Source changes `age INT` → `age VARCHAR(10)`.
    Expected response: P1, BLOCK, human approval required.

  Breaking (column removal):
    Source drops a required column, e.g., removes `email`.
    Expected response: P1, BLOCK, human approval required.

  PII exposure:
    Source adds a column matching PII patterns, e.g., `ssn`, `credit_card`.
    Expected response: P0, BLOCK immediately, no auto-remediation.

EXPECTED IMMUNE SYSTEM RESPONSE (additive):
  1. Detection: SCHEMA_DRIFT, P3
  2. Diagnosis: SCHEMA_ADDITIVE_CHANGE (confidence 0.99)
  3. Risk: LOW
  4. Remediation: ADD_COLUMN_TO_STAGING
  5. Verification: schema matches updated expected schema
  6. Resolution: RESOLVED

EXPECTED IMMUNE SYSTEM RESPONSE (breaking):
  1. Detection: SCHEMA_DRIFT, P1
  2. Diagnosis: SCHEMA_BREAKING_CHANGE (confidence 0.99)
  3. Risk: HIGH → human approval required
  4. Dashboard: approval request appears
  5. (after human approves) Remediation: QUARANTINE_BAD_RECORDS
  6. Verification: valid records flow to production, bad records in quarantine
  7. Resolution: RESOLVED

USAGE:
  python failure_injection/schema_drift.py --pipeline orders --type additive --column phone --dtype VARCHAR(20)
  python failure_injection/schema_drift.py --pipeline orders --type breaking --column age --new-dtype VARCHAR(10)
  python failure_injection/schema_drift.py --pipeline orders --type pii --column ssn

DO NOT RUN IN PRODUCTION. See row_anomaly.py for the environment guard pattern.
"""

import argparse
import os
import logging

logger = logging.getLogger(__name__)


def _check_injection_allowed() -> None:
    env = os.getenv("ENVIRONMENT", "production")
    if env == "production":
        override = os.getenv("DPIS_ALLOW_INJECTION_IN_PRODUCTION")
        if override != "I_UNDERSTAND_THE_RISK":
            raise EnvironmentError(
                "Failure injection is disabled in production."
            )


def inject_additive_schema_change(pipeline_id: str, column: str, dtype: str) -> None:
    """Add a new column to the source schema."""
    raise NotImplementedError("Schema drift injection pending — Phase 11")


def inject_breaking_schema_change(
    pipeline_id: str, column: str, new_dtype: str
) -> None:
    """Change an existing column's type to something incompatible."""
    raise NotImplementedError("Schema drift injection pending — Phase 11")


def inject_pii_column(pipeline_id: str, column: str) -> None:
    """
    Add a column with a PII-sounding name.
    This should trigger P0 immediately with no auto-remediation.
    """
    raise NotImplementedError("Schema drift injection pending — Phase 11")


def main() -> None:
    parser = argparse.ArgumentParser(description="Inject a schema drift scenario.")
    parser.add_argument("--pipeline", required=True)
    parser.add_argument("--type", choices=["additive", "breaking", "pii"], required=True)
    parser.add_argument("--column", required=True)
    parser.add_argument("--dtype", help="Data type (for additive changes)")
    parser.add_argument("--new-dtype", help="New data type (for breaking changes)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    _check_injection_allowed()

    if args.type == "additive":
        inject_additive_schema_change(args.pipeline, args.column, args.dtype)
    elif args.type == "breaking":
        inject_breaking_schema_change(args.pipeline, args.column, args.new_dtype)
    elif args.type == "pii":
        inject_pii_column(args.pipeline, args.column)


if __name__ == "__main__":
    main()
