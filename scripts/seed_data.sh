#!/usr/bin/env bash
# ==============================================================================
# Data Pipeline Immune System — Seed Synthetic Data Script
# ==============================================================================
set -euo pipefail

ENV="${ENVIRONMENT:-dev}"
PROJECT_ID="${PROJECT_ID:-dpis-dev}"
SOURCE_BUCKET="${SOURCE_BUCKET:-dpis-${ENV}-source}"
TARGET_DATE="${1:-$(date -u +%Y-%m-%d)}"
RECORD_COUNT="${2:-1000}"

echo "============================================================"
echo " Seeding synthetic orders data for date: ${TARGET_DATE}"
echo " Environment: ${ENV} | Target Records: ${RECORD_COUNT}"
echo "============================================================"

OUTPUT_DIR="scratch/landing/${TARGET_DATE}"
mkdir -p "${OUTPUT_DIR}"
OUTPUT_FILE="${OUTPUT_DIR}/orders_${TARGET_DATE}.json"

echo "Generating synthetic JSON records into ${OUTPUT_FILE}..."

python3 - <<EOF
import json
import random
from datetime import datetime, timezone

date_str = "${TARGET_DATE}"
count = int("${RECORD_COUNT}")
statuses = ["COMPLETED", "COMPLETED", "COMPLETED", "PROCESSING", "CANCELLED", "REFUNDED"]
currencies = ["USD", "USD", "USD", "EUR", "GBP"]

records = []
for i in range(1, count + 1):
    rec = {
        "order_id": f"ORD-{date_str.replace('-', '')}-{i:04d}",
        "customer_id": f"CUST-{random.randint(100000, 999999)}",
        "order_date": f"{date_str}T{random.randint(0, 23):02d}:{random.randint(0, 59):02d}:00Z",
        "status": random.choice(statuses),
        "total_amount": round(random.uniform(10.0, 500.0), 2),
        "currency": random.choice(currencies),
        "items_count": random.randint(1, 10),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    records.append(rec)

with open("${OUTPUT_FILE}", "w", encoding="utf-8") as f:
    for r in records:
        f.write(json.dumps(r) + "\n")

print(f"Successfully generated {len(records)} orders records.")
EOF

# If gsutil or gcloud storage is available and bucket exists, upload
if command -v gcloud &>/dev/null && gcloud storage ls "gs://${SOURCE_BUCKET}" &>/dev/null; then
    echo "Uploading to gs://${SOURCE_BUCKET}/orders/${TARGET_DATE}/..."
    gcloud storage cp "${OUTPUT_FILE}" "gs://${SOURCE_BUCKET}/orders/${TARGET_DATE}/"
    echo "Upload complete."
else
    echo "Note: Cloud storage skipped (local mode active). File stored at ${OUTPUT_FILE}"
fi

echo "Data seeding complete."
