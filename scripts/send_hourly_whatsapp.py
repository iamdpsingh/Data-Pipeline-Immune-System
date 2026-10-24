#!/usr/bin/env python3
# ==============================================================================
# Data Pipeline Immune System — Hourly WhatsApp Dispatch CLI
# ==============================================================================
"""Command-line script to trigger hourly WhatsApp pulse broadcast."""

from __future__ import annotations

import argparse
import logging
import os
import sys

# Ensure root directory is on python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.notifications.whatsapp import WhatsAppAlertDispatcher

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("dpis.scripts.whatsapp")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Trigger hourly WhatsApp pipeline pulse."
    )
    parser.add_argument(
        "--phone",
        default=os.getenv("WHATSAPP_RECIPIENT", "+1234567890"),
        help="Recipient phone number with country code.",
    )
    parser.add_argument(
        "--status",
        default="HEALTHY",
        choices=["HEALTHY", "WARNING", "DEGRADED", "CRITICAL"],
        help="Current pipeline cluster status.",
    )
    parser.add_argument(
        "--score",
        type=float,
        default=98.5,
        help="Current composite health score.",
    )
    args = parser.parse_args()

    logger.info(
        "Triggering hourly WhatsApp update to %s (Status=%s)", args.phone, args.status
    )

    dispatcher = WhatsAppAlertDispatcher()
    success = dispatcher.send_hourly_alert(
        recipient_phone=args.phone,
        health_status=args.status,
        health_score=args.score,
    )

    if success:
        logger.info("Hourly WhatsApp notification processed successfully.")
    else:
        logger.warning("WhatsApp notification encountered an issue during dispatch.")


if __name__ == "__main__":
    main()
