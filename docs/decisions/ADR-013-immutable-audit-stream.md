# ADR-013: Immutable Audit Trail and Memory Store
## Status: Accepted
## Context:
Autonomous decisions must be 100% traceable for compliance and post-mortems.
## Decision:
Every agent decision writes an append-only structured audit record to BigQuery `dpis_dev.audit_log`.
## Consequences:
Guarantees zero silent mutations and enables retrospective MTTR learning.
