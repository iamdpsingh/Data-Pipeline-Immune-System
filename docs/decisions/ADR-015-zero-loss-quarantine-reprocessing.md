# ADR-015: Zero-Loss Quarantine Reprocessing Framework
## Status: Accepted
## Context:
Quarantined records must eventually be sanitized and backfilled into Silver conformed tables.
## Decision:
Provide idempotent PySpark backfill utilities that replay quarantined rows using updated schema contracts.
## Consequences:
Ensures zero data loss while preventing corrupt records from ever polluting production dashboards.
