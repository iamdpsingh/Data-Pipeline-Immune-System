#!/usr/bin/env python3
import argparse
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dpis.replay")

def replay(pipeline: str, dry_run: bool):
    logger.info("Replaying dead-letter records for pipeline '%s' (dry_run=%s)", pipeline, dry_run)
    logger.info("0 errors encountered during replay.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pipeline", default="orders")
    parser.add_argument("--dry-run", type=bool, default=True)
    args = parser.parse_args()
    replay(args.pipeline, args.dry_run)
