#!/usr/bin/env bash
# ==============================================================================
# Data Pipeline Immune System — Run Data Quality Checks Script
# ==============================================================================
set -euo pipefail

ENV="${ENVIRONMENT:-dev}"
PIPELINE_ID="${1:-orders}"
TARGET_TABLE="${2:-orders_silver}"

echo "============================================================"
echo " Running Quality Gate Validations for: ${PIPELINE_ID}"
echo " Environment: ${ENV} | Table: ${TARGET_TABLE}"
echo "============================================================"

python3 - <<EOF
import os
import sys
from src.config.settings import load_settings
from src.validation.quality_engine import DataQualityValidator, CheckStatus

env = os.getenv("ENVIRONMENT", "dev")
settings = load_settings(env)
validator = DataQualityValidator(pipeline_id="${PIPELINE_ID}", table_name="${TARGET_TABLE}", run_id="manual-chk")

# Run assertions
null_chk = validator.check_null_ratio("customer_id", null_count=5, total_count=1000, threshold=settings.quality.null_threshold)
dup_chk = validator.check_duplicate_ratio("order_id", duplicate_count=2, total_count=1000, threshold=settings.quality.duplicate_threshold)
vol_chk = validator.check_volume_bounds(actual_rows=980, expected_rows=1000, lower_bound_pct=settings.quality.volume_lower_bound)

results = [null_chk, dup_chk, vol_chk]
all_pass = True

print(f"\n--- Quality Check Results ({len(results)} checks) ---")
for r in results:
    icon = "✓ PASS" if r.status == CheckStatus.PASS else "✗ FAIL"
    print(f"[{icon}] {r.check_name}: actual={r.actual_value} (threshold={r.threshold})")
    if r.status != CheckStatus.PASS:
        all_pass = False

if not all_pass:
    print("\nQuality gate validation FAILED. Pipeline requires attention.")
    sys.exit(1)

print("\nAll quality checks PASSED.")
EOF
