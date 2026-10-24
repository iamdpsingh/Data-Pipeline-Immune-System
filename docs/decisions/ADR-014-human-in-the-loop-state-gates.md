# ADR-014: Human-in-the-Loop (HITL) State Gates & Risk Tier Boundaries

## Status: Accepted (In Production)

## Context
While autonomous remediation provides sub-minute MTTR for transient failures, granting autonomous systems unchecked authority to execute high-impact mutations (e.g., dropping obsolete tables, executing unverified schema migrations, backfilling millions of financial transactions) introduces severe risks:
1. Irreversible production data loss from misinterpreted edge cases.
2. Inadvertent violation of regulatory data retention rules.
3. Premature automation of ambiguous operational scenarios.

A production-grade immune system must establish a mathematically rigorous boundary between actions that are safe to auto-execute and actions that must halt and await human verification.

## Decision
We enforce a strict **Four-Tier Risk Classification and Human-in-the-Loop Gate** (`src/risk/classifier.py` and `src/risk/never_allow.py`):

1. **Risk Tier Taxonomy**:
   - **LOW (P2/P3)**: Idempotent, non-destructive actions (e.g. `RETRY_TASK`, `APPLY_BACKOFF`, `CLEAR_TASK_INSTANCE`, `REFRESH_METADATA`, `REGISTER_ADDITIVE_COLUMN`).
     *Execution Policy*: **100% Autonomous Remediation**. No human intervention required.
   - **MEDIUM (P2)**: Partition-level isolation (e.g. `QUARANTINE_RECORD`, `SPLIT_DEAD_LETTER`, `HOLD_PARTITION`).
     *Execution Policy*: **Autonomous Execution with Real-Time Notification**. System isolates data immediately to prevent corruption spread and alerts on-call engineers via Telegram/Email.
   - **HIGH (P1)**: Structural alterations (e.g. `BREAKING_SCHEMA_MIGRATION`, `HISTORICAL_PARTITION_BACKFILL`, `DATASET_FAILOVER`).
     *Execution Policy*: **Mandatory Human-in-the-Loop Authorization**. Execution halts; the incident transitions to state `PENDING_APPROVAL`. Remediation cannot proceed until an authorized engineer clicks "Authorize Remediation" in the dashboard or approves via the signed webhook API.
   - **CRITICAL / NEVER-ALLOW (P0)**: Inviolable system bounds (e.g. `DELETE_PRODUCTION_TABLE`, `EXECUTE_ARBITRARY_SQL`, `MODIFY_IAM_ROLE`, `EXPOSE_PII_PLAINTEXT`, `DISABLE_VALIDATION_RULE`).
     *Execution Policy*: **Hard Code-Enforced Block**. Hard-coded in python sets before any LLM or rules layer can run. Execution raises `NeverAllowViolationError` immediately; cannot be bypassed by any prompt, configuration, or administrator override.

2. **HITL State Workflow**:
   ```
   [Incident Flagged P1]
            │
            ▼
   State: PENDING_APPROVAL ──> Dispatch Alert (Telegram / Email / Dashboard Modal)
            │
      ┌─────┴────────────────┐
      ▼                      ▼
   [Engineer Approves]   [Engineer Rejects / Timeout 24h]
      │                      │
      ▼                      ▼
   State: REMEDIATING    State: REJECTED_HALTED
      │                      │
   Execute Idempotent Action  Safe Partition Quarantine
   ```

3. **Cryptographic Sign-off**:
   Approvals require an authenticated bearer token or dashboard session, capturing the approving engineer's email, timestamp, and optional justification comment into the BigQuery audit log.

## Consequences

### Positive
- **Guaranteed Safety Boundaries**: Zero risk of rogue autonomous AI agents deleting production data or violating compliance rules.
- **Operator Trust**: Engineers maintain complete ultimate authority over destructive operations while enjoying full automation for tedious transient issues.
- **Auditable Accountability**: Every manual override is captured with identity and timestamp in the audit trail.

### Negative / Trade-Offs
- Incidents requiring human approval have an MTTR dependent on engineer response time (typically 5 to 30 minutes).
- Requires maintaining an interactive human authorization interface (dashboard modal and secure approval API endpoint).
