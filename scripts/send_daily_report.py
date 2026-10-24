#!/usr/bin/env python3
# ==============================================================================
# Data Pipeline Immune System — Daily Report CLI Automation
# ==============================================================================
"""Command-line script to trigger daily email report generation and dispatch."""

from __future__ import annotations

import argparse
import logging
import os
import sys

# Ensure root directory is on python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.notifications.reporter import DailyReportGenerator, EmailDispatcher

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("dpis.scripts.daily_report")


def main() -> None:
    parser = argparse.ArgumentParser(description="Trigger daily email summary report.")
    parser.add_argument(
        "--recipient",
        default=os.getenv("REPORT_RECIPIENT", "dhruvpratapsingh30.official2.o@gmail.com"),
        help="Target email address for the daily health report.",
    )
    parser.add_argument(
        "--environment",
        default=os.getenv("ENVIRONMENT", "dev"),
        help="Deployment environment (dev, staging, production).",
    )
    args = parser.parse_args()

    logger.info("Starting daily report generation for env=%s recipient=%s", args.environment, args.recipient)

    generator = DailyReportGenerator(environment=args.environment)
    metrics = generator.collect_metrics(
        project_id=os.getenv("PROJECT_ID", "data-pipeline-immune-system"),
        dataset=f"dpis_{args.environment}",
    )

    dispatcher = EmailDispatcher()
    success = dispatcher.send_daily_report(
        recipient=args.recipient,
        metrics=metrics,
        generator=generator,
    )

    if success:
        logger.info("Daily health report process completed successfully.")
    else:
        logger.warning("Daily health report encountered an issue during delivery.")


if __name__ == "__main__":
    main()
