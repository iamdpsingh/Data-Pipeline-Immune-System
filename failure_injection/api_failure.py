# ==============================================================================
# Data Pipeline Immune System — Failure Injection: API Failure
# ==============================================================================
"""Simulates an upstream API 502/503/504 gateway timeout or connection reset.

WHAT THIS SIMULATES:
  The third-party extraction endpoint experiences intermittent 5xx gateway timeouts.

EXPECTED IMMUNE RESPONSE:
  1. Detection: API_TIMEOUT, P2
  2. Diagnosis: API_TIMEOUT (confidence 0.95)
  3. Risk: LOW
  4. Remediation: RETRY_SOURCE_EXTRACTION with exponential backoff
  5. Verification: Data extraction successful (PASS)
  6. Resolution: RESOLVED
"""

from __future__ import annotations

import argparse
import logging
import os

logger = logging.getLogger(__name__)


def _check_injection_allowed() -> None:
    env = os.getenv("ENVIRONMENT", "production").lower()
    if env == "production":
        override = os.getenv("DPIS_ALLOW_INJECTION_IN_PRODUCTION")
        if override != "I_UNDERSTAND_THE_RISK":
            raise OSError("Failure injection is disabled in production.")


def simulate_api_failure(error_type: str = "504_GATEWAY_TIMEOUT") -> dict:
    """Generates synthetic task context simulating an upstream API extraction fault."""
    _check_injection_allowed()
    logger.info("Simulating API extraction fault: %s", error_type)

    return {
        "task_id": "extract_orders_source_api",
        "task_status": "FAILED",
        "error_type": "TIMEOUT",
        "error_message": f"HTTPError: {error_type} Upstream gateway did not respond within 30000ms.",
        "retry_count": 1,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulate upstream API failure.")
    parser.add_argument("--error-type", default="504_GATEWAY_TIMEOUT")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    payload = simulate_api_failure(args.error_type)
    print("Simulated Task Context:\n", payload)


if __name__ == "__main__":
    main()
