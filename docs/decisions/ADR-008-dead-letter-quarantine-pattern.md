# ADR-008: Medallion Lakehouse Dead-Letter Quarantine Gate
## Status: Accepted
## Context:
Bad records in a batch should neither halt the entire pipeline nor corrupt the clean warehouse.
## Decision:
Split corrupt records into GCS dead-letter storage and BigQuery quarantine table while clean records proceed.
## Consequences:
Maintains 99.9%+ pipeline throughput while preserving full audit trail for backfills.
