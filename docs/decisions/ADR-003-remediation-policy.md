# ADR-003: Deterministic Rules Priority and Automated Remediation Policy

- **Status**: Accepted
- **Deciders**: Architecture Team, Data Reliability Lead, Core Platform Team
- **Date**: 2026-10
- **Technical Context**: Autonomous Self-Healing and Safety Boundaries

---

## 1. Context and Problem Statement

When production data pipelines encounter failures—such as transient executor crashes, schema deviations, null spikes, or missing daily partitions—the immune system must decide whether and how to automatically remediate without human intervention.

Two competing architectural approaches were evaluated:
1. **LLM-First Remediation**: Prompting an LLM with incident telemetry and allowing it to generate repair scripts, SQL patches, or workflow restart calls dynamically.
2. **Deterministic Rules with Bounded Action Handlers**: Running deterministic rule-matching engines first, mapping known failure signatures directly to vetted, idempotent remediation functions in [src/remediation/actions.py](file:///Volumes/Work/daemons-lab/d.automation/Data%20Pipeline%20Immune%20System/src/remediation/actions.py), and reserving LLM analysis solely for novel diagnostic classification under strict safety boundaries.

---

## 2. Decision Outcome

We adopted **Deterministic Rules Priority with Bounded Remediation Policies**:

```
                              +----------------------------+
                              | Detected Incident Payload  |
                              +--------------+-------------+
                                             |
                                             v
                              +----------------------------+
                              | Deterministic Rules Engine |
                              +--------------+-------------+
                                      /              \
                          Match Found/                \No Match (Novel)
                                    /                  \
                                   v                    v
                  +-----------------------+   +-------------------+
                  | Deterministic Action  |   | AI Diagnosis      |
                  | Signature Identified  |   | (Gemini / Claude) |
                  +-----------+-----------+   +---------+---------+
                              |                         |
                              +------------+------------+
                                           |
                                           v
                             +---------------------------+
                             |   Risk Evaluation Engine  |
                             |   (Never-Allow Invariants)|
                             +-------------+-------------+
                                           |
                    +----------------------+----------------------+
                    |                      |                      |
             [LOW RISK]             [MEDIUM RISK]          [HIGH / NEVER_ALLOW]
                    |                      |                      |
                    v                      v                      v
             +--------------+      +---------------+      +-------------------+
             |  Autonomous  |      | Conditioned   |      | Require Human     |
             |  Execution   |      | Auto-Remedy   |      | Approval (HITL) / |
             |  (Immediate) |      | or Escalate   |      | Hard Rejection    |
             +--------------+      +---------------+      +-------------------+
```

### Core Tenets of the Remediation Policy:

1. **Deterministic Rules Run First**:
   Deterministic signatures (e.g. `UPSTREAM_API_TIMEOUT`, `SCHEMA_NEW_COLUMN_ADDITIVE`, `QUARANTINE_NULL_SPIKE`) execute without calling an LLM. This provides sub-second latency (<50ms vs 2–5s for LLM API calls) and zero inference cost.

2. **Remediation Action Registry**:
   The Remediation Agent cannot execute arbitrary bash commands or raw SQL strings. All remediations must dispatch to explicit, pre-tested Python callables registered in the action registry:
   - `restart_task(dag_id, task_id, execution_date)`
   - `trigger_backfill(dag_id, start_date, end_date)`
   - `quarantine_corrupt_records(dataset, table, condition)`
   - `apply_additive_schema_update(dataset, table, new_columns)`
   - `reprocess_quarantined_partition(dataset, table, partition_id)`

3. **Risk Tier Stratification**:
   - **LOW Risk**: Purely idempotent, zero data-loss risk (e.g. restarting a failed transient Airflow task, routing corrupt records to quarantine). Autonomous execution is permitted immediately.
   - **MEDIUM Risk**: Non-destructive transformations affecting bounded time windows (< 24 hours backfill). Autonomous execution permitted only if environmental preconditions pass.
   - **HIGH Risk**: Multi-day partition reprocessing or table restatement. Autonomous execution is disabled; interactive Slack / PagerDuty confirmation is required.
   - **NEVER_ALLOW**: Any action containing `DROP TABLE`, `TRUNCATE`, `ALTER TABLE DROP COLUMN`, or destructive overwrite of historical partitions without backup. The system rejects these with an immediate `CriticalSafetyViolation` exception.

4. **Idempotency Guarantee**:
   Every remediation handler must be safely retryable. Executing `restart_task` or `trigger_backfill` three times consecutively must leave the target table and Airflow state identical to executing it once.

---

## 3. Justification and Rationale

- **Safety and Auditability**: In regulated enterprise data platforms, autonomous agents executing unvetted, dynamically-generated code introduce catastrophic operational risk. Fixed handler registries eliminate code injection and hallucinated SQL queries.
- **Explainability**: Every action record logged to BigQuery `dpis_audit.remediation_audit` contains the explicit rule ID or diagnosis rationale that triggered it, making every self-healing action fully defensible to data governance teams.
- **Fail-Safe Defaults**: If any component of the diagnosis or risk classification fails, the controller defaults to blocking execution and notifying the data on-call engineer.

---

## 4. Consequences and Trade-offs

### Positive:
- 100% immune to prompt injection attacks against database operations.
- Ultra-low execution latency for high-frequency transient infrastructure glitches.
- Deterministic test coverage: Unit tests can verify every remediation branch without LLM mocks.

### Limitations:
- Unforeseen novel failures cannot be healed automatically on their first occurrence; they must fall back to human intervention until codified into rules or validated action templates.
