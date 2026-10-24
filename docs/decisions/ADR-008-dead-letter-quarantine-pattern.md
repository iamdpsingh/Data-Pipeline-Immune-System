# ADR-008: Medallion Lakehouse Dead-Letter Quarantine Pattern

## Status: Accepted (In Production)

## Context
In production data platforms, invalid records (e.g., negative financial values, null primary keys, malformed JSON structures, corrupted UTF-8 encodings) frequently enter upstream ingestion feeds. 

Historically, data engineering teams faced an unacceptable dilemma:
- **Strategy A (Fail Fast)**: Abort the entire batch or pipeline run upon encountering bad records. This protects data quality but halts all downstream operational analytics, breaches freshness SLAs, and creates severe on-call fatigue.
- **Strategy B (Silent Drop)**: Drop corrupted records silently and continue loading valid data. This preserves pipeline uptime but causes permanent data loss, unrecorded audit gaps, and skewed financial reconciliations.

Neither strategy meets enterprise standards for high-volume data platforms.

## Decision
We implement an **Autonomous Dead-Letter Quarantine Split Gate** (implemented in `src/validation/quality_engine.py` and PySpark validation transforms):

1. **Dual-Route Micro-Batch Splitting**:
   - As records transition from Bronze to Silver, every batch is validated against deterministic quality assertion contracts (null ratios, duplicate ratios, schema types, range bounds).
   - Records that pass all rules are promoted immediately to the **Silver Lakehouse Tier** (`dpis_silver_<env>.<table_name>`).
   - Records that fail one or more validation contracts are extracted, enriched with metadata, and routed to the **Dead-Letter Quarantine Tier**.

2. **Quarantine Storage Topology**:
   - **GCS Raw Archive**: Corrupted rows are serialized into `gs://dpis-quarantine-<project-id>/<pipeline_id>/<partition_date>/corrupted_<run_id>.jsonl` with full raw byte fidelity.
   - **BigQuery Quarantine Table**: Corrupted rows are loaded into `dpis_quarantine_<env>.<pipeline_id>_quarantine` with columns:
     - `raw_record JSON`: Full original record content.
     - `rejection_rule STRING`: Exact assertion rule violated (e.g. `RULE_ORDER_AMOUNT_POSITIVE`).
     - `rejection_reason STRING`: Diagnostic evidence (e.g. `amount = -45.00 is <= 0.00`).
     - `quarantined_at TIMESTAMP`: Exact UTC timestamp of quarantine action.
     - `reprocess_status STRING`: `PENDING`, `REPROCESSED`, or `REJECTED_PERMANENT`.

3. **Autonomous Verification Guarantee**:
   - Verification Agent validates the destination Silver partition. If even a single corrupted row bypassed the quarantine gate, the run is immediately rolled back and flagged P1.

## Consequences

### Positive
- **100% Data Cleanness Guarantee**: Zero corrupted records contaminate analytics, machine learning models, or executive BI dashboards.
- **Continuous Pipeline Availability**: Pipeline maintains >99.9% uptime; clean records are processed and delivered on schedule without waiting for upstream bug fixes.
- **Zero Data Loss**: Every rejected row is preserved with forensic metadata, enabling clean root-cause debugging and deterministic replay backfills.

### Negative / Trade-Offs
- Storage overhead: Maintaining both conformed tables and quarantine tables increases BigQuery and GCS storage volume.
- Backfill complexity: Upstream bug fixes require executing a targeted quarantine backfill job (`scripts/replay_quarantine.py`) to re-inject repaired records into Silver.
