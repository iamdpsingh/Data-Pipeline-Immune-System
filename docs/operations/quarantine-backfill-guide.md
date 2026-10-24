# Dead-Letter Quarantine Reprocessing & Backfill Guide

## 1. Overview
When the Dead-Letter Quarantine Gate (ADR-008) isolates corrupted records, those records are preserved with full raw byte fidelity in GCS and BigQuery. Once upstream teams remediate the root bug (e.g. mobile app v2.1.4 fixes negative order pricing), this guide details how to inspect, re-validate, and re-inject the quarantined records into the Silver Lakehouse tier without introducing duplicates.

---

## 2. Inspecting Quarantined Records
Query the BigQuery quarantine table for an affected partition date:

```sql
SELECT
    rejection_rule,
    COUNT(*) AS record_count,
    MIN(quarantined_at) AS first_seen,
    MAX(quarantined_at) AS last_seen,
    ARRAY_AGG(raw_record LIMIT 3) AS sample_records
FROM `data-pipeline-immune-system.dpis_quarantine_prod.orders_quarantine`
WHERE DATE(quarantined_at) = '2026-10-24'
  AND reprocess_status = 'PENDING'
GROUP BY rejection_rule;
```

---

## 3. Reprocessing Workflow via CLI (`scripts/replay_quarantine.py`)

The system provides a dedicated, idempotent reprocessing CLI:

### Step 1: Execute Dry-Run Validation
Always preview candidate records before applying mutations:
```bash
python3 scripts/replay_quarantine.py \
    --pipeline=orders \
    --partition-date=2026-10-24 \
    --dry-run \
    --env=prod
```
- **Output**: Reports total eligible rows, count passing current quality assertions, and count still failing.

### Step 2: Execute Live Idempotent Replay
Once upstream data is corrected, execute the live merge:
```bash
python3 scripts/replay_quarantine.py \
    --pipeline=orders \
    --partition-date=2026-10-24 \
    --env=prod
```
- **Mechanism**:
  1. Reads records marked `reprocess_status = 'PENDING'`.
  2. Evaluates records against current active data quality rules in `src/validation/quality_engine.py`.
  3. Validated records are atomically merged into `dpis_silver_prod.orders` using `MERGE ... ON T.order_id = S.order_id`.
  4. Quarantined records in `orders_quarantine` are updated to `reprocess_status = 'REPROCESSED'`.
  5. Records that continue failing remain marked `PENDING`.

---

## 4. Verification & Audit Trail
Confirm successful backfill via SQL:
```sql
-- 1. Verify rows exist in Silver tier
SELECT COUNT(*) 
FROM `data-pipeline-immune-system.dpis_silver_prod.orders` 
WHERE order_date = '2026-10-24';

-- 2. Verify quarantine table updated
SELECT reprocess_status, COUNT(*) 
FROM `data-pipeline-immune-system.dpis_quarantine_prod.orders_quarantine` 
WHERE DATE(quarantined_at) = '2026-10-24'
GROUP BY reprocess_status;
```
All reprocess operations log structured audit events to `dpis_analytics_prod.incident_audit_log` with `action_type = 'QUARANTINE_REPLAY_EXECUTED'`.
