#!/usr/bin/env python3
import argparse
import csv
import sys
from datetime import datetime

def export_audit_csv(output_file: str):
    with open(output_file, "w", newline="") as fp:
        writer = csv.writer(fp)
        writer.writerow(["incident_id", "agent_name", "action_type", "status", "timestamp"])
        writer.writerow(["inc-sim-01", "DetectionAgent", "ANOMALY_DETECTED", "SUCCESS", datetime.utcnow().isoformat()])
    print(f"Exported audit trail to {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="audit_export.csv")
    args = parser.parse_args()
    export_audit_csv(args.out)
