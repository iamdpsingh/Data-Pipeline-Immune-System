# ADR-015: Zero-Loss Quarantine Reprocessing & Backfill Architecture

## Status: Accepted (In Production)

## Context
When corrupted records are isolated by the Dead-Letter Quarantine gate (ADR-008), the root cause is frequently remediated in upstream systems shortly thereafter (e.g., an upstream mobile app bug fix is deployed, a partner updates their currency formatting, or a missing customer master record is populated).

Once the upstream source issue is resolved, data engineering teams must reprocess the quarantined records into the Silver Lakehouse tier without:
1. Creating duplicate records in Silver.
2. Disrupting live streaming ingestion or concurrently scheduled DAGs.
3. Losing the historical record of the original quarantine event.

## Decision
We implement a **Zero-Loss Idempotent Quarantine Reprocessing Engine** (`scripts/replay_quarantine.py`):

1. **Stateful Quarantine Lifecycle**:
   Records in the BigQuery quarantine table (`dpis_quarantine_<env>.<pipeline_id>_quarantine`) progress through strict state transitions:
   - `PENDING`: Awaiting upstream bug fix or manual inspection.
   - `REPROCESSING`: Actively undergoing validation and transformation.
   - `REPROCESSED`: Successfully validated, transformed, and merged into Silver tier.
   - `REJECTED_PERMANENT`: Confirmed non-recoverable junk (e.g. malformed test packets).

2. **Idempotent Merge Mechanism**:
   - Replay jobs read `PENDING` records for a designated partition date or incident ID.
   - Records pass through the same deterministic validation rules enforced by the live pipeline.
   - Cleaned records are written to Silver using a BigQuery atomic `MERGE` statement:
     ```sql
     MERGE INTO `dpis_silver_prod.orders` T
     USING cleaned_quarantine_batch S
     ON T.order_id = S.order_id AND T.order_date = S.order_date
     WHEN MATCHED THEN
       UPDATE SET T.amount = S.amount, T.status = S.status, T._updated_at = CURRENT_TIMESTAMP()
     WHEN NOT MATCHED THEN
       INSERT ROW;
     ```
   - Guarantees zero duplicate rows in Silver even if the replay job is executed multiple times.

3. **Atomic Quarantine Audit Update**:
   - Upon successful merge verification by the `VerificationAgent`, the reprocessed records in the quarantine table are marked:
     `UPDATE ... SET reprocess_status = 'REPROCESSED', reprocessed_at = CURRENT_TIMESTAMP(), replay_run_id = '<run_id>'`
   - Preserves complete data lineage showing that the row originated in quarantine and was subsequently repaired.

4. **Dry-Run & Verification Flags**:
   - The replay CLI (`scripts/replay_quarantine.py`) supports `--dry-run` to preview candidate records and calculate validation pass ratios before executing database mutations.

## Consequences

### Positive
- **Zero Data Loss**: Guarantees that valid business revenue or transaction history is never permanently discarded due to temporary validation failures.
- **Idempotent Execution**: Reprocessing operations can fail, retry, or resume safely without risk of double-counting.
- **Automated Verification**: The Verification Agent confirms record counts match expected quantities before declaring the incident closed.

### Negative / Trade-Offs
- Reprocessing large historical backfills requires BigQuery query slots and compute time.
- If upstream schema has evolved between the time of quarantine and the time of replay, transformation logic must apply schema adaptation before merging.
