# Architecture Rules — Data Pipeline Immune System

Architectural constraints that must be maintained as the system evolves. These exist to prevent the system from drifting into patterns that would make it less safe, less maintainable, or harder to reason about.

---

## Layer separation

The medallion architecture (Bronze → Silver → Gold) is strictly enforced:

| Layer | What it contains | Who writes to it |
|---|---|---|
| Bronze / Raw | Unmodified source data | Ingestion Engine only |
| Silver | Validated, cleaned, standardised data | Transformation Engine only |
| Gold | Business-ready aggregated data | Gold Load jobs only |

The Remediation Agent may write to Bronze/staging tables in specific approved scenarios (file reload, partition reprocess). It may not write to Silver or Gold directly under any circumstances.

---

## Immune system is external to the pipeline

The immune system observes the pipeline — it is not embedded inside it. This matters for a few reasons:

- Pipeline failures don't cascade into immune system failures
- The immune system can observe multiple pipelines simultaneously
- Pipeline code doesn't need to know the immune system exists

In practice: Airflow DAGs complete their work and emit events. The immune system reacts to those events. The two are coupled only through BigQuery tables and the immune monitor DAG.

---

## Rules engine before LLM

The deterministic rules engine always runs before the AI diagnosis layer. This is not optional and must not be changed without revisiting the full trust model.

If a known pattern is being handled by the AI when it could be handled deterministically, add it to the rules engine.

---

## Configuration over hardcoding

Every threshold, SLA, policy, and environment-specific value lives in `config/`. Application code reads from the config object. If you find a hardcoded value in application code (not in a test), move it to config.

This is especially important for:
- Quality check thresholds
- Anomaly detection sensitivity (z-score thresholds)
- Pipeline health score weights
- Retry counts and backoff parameters
- SLA windows

---

## Agent permission hierarchy

This must be maintained:

```
Detection  → READ ONLY
Diagnosis  → READ ONLY
Risk       → READ ONLY
Verification → READ ONLY
Learning   → WRITE to incident_memory ONLY
Remediation → LIMITED WRITE (approved action library only)
Controller → READ/WRITE to all incident tables
```

Do not expand any agent's permissions without:
1. Updating `.agents/rules/agent-rules.md`
2. Updating the service account permissions in Terraform
3. Adding a test that verifies the new permission is scoped correctly
4. Adding an ADR entry explaining why

---

## Structured agent messages

Agents communicate through typed dataclasses or Pydantic models. No raw dicts passed between agents. No free-form strings. Every field in the message has a clear type and meaning.

If you need to add a new field to an agent's output, add it to the dataclass first, update the consumer, then implement it. Don't add fields as optional dict keys.

---

## Idempotency requirement

Every remediation action must be idempotent. The controller may retry a failed remediation. Running any action twice must produce the same state as running it once.

This is especially important for:
- Partition reprocessing (delete and rebuild must not create duplicates)
- Record quarantine (moving the same record twice must be safe)
- File reload (downloading the same file twice must overwrite, not duplicate)

---

## Incident state machine

The incident state machine is defined in `src/controller/states.py`. Valid transitions:

```
DETECTED → CLASSIFIED → DIAGNOSED → RISK_ASSESSED → ACTION_SELECTED
       → REMEDIATION → VERIFICATION → RESOLVED
       → ESCALATED (from any state)
       → BLOCKED (from RISK_ASSESSED)
```

No other transitions are valid. The controller enforces this. Do not add shortcut transitions without updating the state machine and the flow documentation.

---

## BigQuery as the source of truth

All incident state lives in BigQuery. There is no in-memory state in the controller that isn't backed by BigQuery. If the controller restarts mid-incident, it must be able to recover the incident state entirely from BigQuery.

This means every state transition is written to BigQuery before the next step begins.

---

*Last updated: 2026-10*
