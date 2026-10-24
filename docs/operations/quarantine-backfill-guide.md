# Operational Guide: Quarantine Dead-Letter Backfilling
## 1. Overview
When schema drift or transient nulls route corrupted rows into `dpis_dev.quarantine_records`, records must be safely reprocessed after the upstream bug is patched.
## 2. Step-by-Step Backfill Procedure
1. Inspect pending quarantine records:
   ```sql
   SELECT rejection_reason, COUNT(1) FROM `dpis_dev.quarantine_records` WHERE status = 'PENDING' GROUP BY 1;
   ```
2. Trigger PySpark reprocessing script:
   ```bash
   python3 scripts/replay_quarantine_records.py --pipeline orders --dry-run=false
   ```
3. Verify that reprocessed records land in `dpis_silver_dev.orders` and status updates to `RESOLVED`.
