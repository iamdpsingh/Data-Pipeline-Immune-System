# Architecture Decision Records — Decision Log

This file tracks the significant architectural and engineering decisions made during the design and build of the Data Pipeline Immune System. Minor implementation choices don't belong here — this is for decisions that shaped the overall structure of the system and that a new developer should understand before making major changes.

Each entry follows the same format: context, decision, reasoning, alternatives considered, and known trade-offs or limitations.

---

## ADR-001 — Use GCP as the cloud platform

**Date:** 2026-10

**Status:** Accepted

**Context:**

The project needs a managed data warehouse, object storage, compute for Spark jobs, and a place to host the agent service. The main options were AWS, Azure, and GCP.

**Decision:**

Use GCP.

**Reasoning:**

BigQuery is the best managed data warehouse for this use case. It handles schema evolution cleanly, supports partitioned tables natively, and the query cost model works well for analytical workloads. Dataproc and Serverless Spark integrate directly with GCS and BigQuery without any extra connectors. Cloud Run is a clean fit for the stateless agent API — no cluster management, scales to zero, and deploys container images directly.

AWS Redshift or Azure Synapse would have worked too, but BigQuery's native JSON support, schema drift detection, and the overall GCP data ecosystem made it the better choice for a data-reliability-focused project.

**Limitations:**

The project is tightly coupled to GCP APIs. Migrating to another cloud later would require rewriting the BigQuery integration, GCS storage layer, and Cloud Run deployment. That's an acceptable trade-off given that this isn't a multi-cloud product.

---

## ADR-002 — Use specialised agents instead of one general agent

**Date:** 2026-10

**Status:** Accepted

**Context:**

The immune system needs to detect anomalies, diagnose root causes, assess risk, execute remediation, and verify outcomes. The simplest implementation would be one LLM agent that does everything. That's also the most dangerous.

**Decision:**

Use specialised agents with clearly separated responsibilities and different permission levels:

- Detection Agent — read-only
- Diagnosis Agent — read-only
- Risk Agent — read-only
- Remediation Agent — limited write
- Verification Agent — read-only
- Learning Agent — read-write to incident memory only

**Reasoning:**

A single general agent with write access creates a wide blast radius. If the LLM hallucinates or makes a poor decision, it could modify or delete production data. Specialised agents limit the damage surface. The Remediation Agent only gets write permissions for a specific set of pre-approved action types — it cannot run arbitrary SQL or modify schemas.

The specialised design also makes testing much easier. Each agent can be tested in isolation against known inputs.

**Alternatives considered:**

A single agent with role-based prompting — rejected because prompt-level restrictions can be bypassed by clever prompt injection or LLM hallucination. Permissions must be enforced in code, not just in the system prompt.

**Limitations:**

More complex to orchestrate. The controller needs to manage the message passing between agents. This is handled by `ImmuneSystemController`, which is the only component that knows the full incident state.

---

## ADR-003 — Rules engine runs before the LLM

**Date:** 2026-10

**Status:** Accepted

**Context:**

For known failure patterns (transient task failures, missing partitions, upstream partial loads), sending the incident to an LLM for diagnosis adds latency and cost without adding value. The correct fix is already known.

**Decision:**

Run the deterministic rules engine first. Only escalate to AI diagnosis if the rules engine cannot classify the incident.

```
Incident → Rules Engine → Known case → Deterministic fix
                       ↓
                   Unknown case → AI Diagnosis → Risk Analysis → Decision
```

**Reasoning:**

This is better engineering. Deterministic rules are fast, free, auditable, and testable. They should handle the majority of common failures. The AI adds value only for novel or ambiguous cases where the pattern isn't in the rules.

It also improves the trust model: the system can explain why it took a specific action without relying on "the AI decided so."

**Alternatives considered:**

LLM-first approach — rejected because it's slower, more expensive, and less auditable.
Rule-only approach — rejected because novel failure patterns won't be in any ruleset, and the system would require constant manual rule updates.

**Limitations:**

The rules need to be maintained. If a new common failure pattern emerges, someone needs to add a rule for it. The AI will handle it in the meantime, but the rule should be codified once the pattern is confirmed.

---

## ADR-004 — Confidence score does not override safety rules

**Date:** 2026-10

**Status:** Accepted

**Context:**

The AI agents produce confidence scores with their diagnoses. High confidence could be used to justify more aggressive automatic action. For example, confidence 0.99 on "this schema change is non-breaking" could trigger automatic schema migration.

**Decision:**

Confidence scores influence prioritisation and recommendations but never override hard safety rules. A P0 incident or a rule marked `never-allow` is blocked regardless of AI confidence.

**Reasoning:**

LLMs can be confidently wrong. A 0.99 confidence score means the model's internal probability is high, not that the model is actually correct. For actions with irreversible consequences — schema changes, large data deletions, financial record modifications — the downside of being wrong once outweighs the benefit of occasionally saving a few minutes.

The safety rules exist precisely for cases where the AI might be confidently incorrect.

**Limitations:**

This means some incidents that could theoretically be auto-resolved will be escalated to humans because they fall under a never-allow rule. That's intentional. The system is designed to be conservative.

---

## ADR-005 — Verification is a separate engine, not a pipeline success check

**Date:** 2026-10

**Status:** Accepted

**Context:**

After remediation, the naive check is: did the pipeline finish without error? If yes, mark incident resolved.

**Decision:**

Verification is a full re-check of data quality metrics after remediation, not just a status check on the pipeline run.

**Reasoning:**

A pipeline can finish successfully and still produce wrong data. A partial load can complete without any Airflow task failure — you just get fewer rows. Schema drift can pass through undetected if the validation rules aren't tight enough.

The Verification Agent re-runs the same checks that detected the original anomaly, plus any additional checks relevant to the specific remediation applied. Only if all checks pass is the incident marked RESOLVED.

This is what actually closes the loop — the system doesn't just restart the pipeline, it confirms the output is correct.

**Limitations:**

Verification adds time to the total MTTR. For P3/low incidents, this might be more overhead than it's worth. The verification depth can be configured per severity level.

---

## ADR-006 — Incident memory uses similarity search, not exact matching

**Date:** 2026-10

**Status:** Accepted

**Context:**

Historical incidents can help the Diagnosis Agent make better recommendations. The question is how to search that history.

**Decision:**

Store incident characteristics (type, symptoms, pipeline, environment, resolution, outcome) in BigQuery. Use embedding-based similarity search (or a weighted feature comparison if full vector search isn't available) to find the most similar historical incidents.

**Reasoning:**

Exact matching would miss related incidents where the failure pattern is similar but not identical. A row count anomaly caused by a partial API response and a row count anomaly caused by a filter change have different root causes but similar symptoms — the diagnosis agent needs to distinguish them using the evidence, not just the incident type.

**Limitations:**

Similarity search quality depends on the quality of the incident representation. Early in the project's lifecycle, the memory won't have enough historical data to be useful. It becomes valuable after 50+ resolved incidents.

---

## ADR-007 — Cloud Run for the agent service

**Date:** 2026-10

**Status:** Accepted

**Context:**

The immune system agents need to be accessible as an API so Airflow DAGs can call them. Options include Cloud Run, Cloud Functions, GKE, and Compute Engine.

**Decision:**

Use Cloud Run.

**Reasoning:**

Cloud Run is stateless, scales to zero when not in use, and deploys container images directly from Artifact Registry. The agent service is inherently request-response in nature — Airflow calls it, it processes an incident, it returns a response. Cloud Run fits this pattern perfectly.

GKE would be overkill for a service that doesn't need persistent state or complex networking. Cloud Functions have a 9-minute timeout limit which could be a problem for complex diagnoses involving multiple BigQuery queries.

**Limitations:**

Cold start latency when the service hasn't received traffic recently. For production, minimum instance count should be set to 1 for P0/P1 incident handlers.

---

## ADR-008 — Quarantine system for partial failures

**Date:** 2026-10

**Status:** Accepted

**Context:**

When a batch contains some valid and some invalid records, the simple options are: fail everything or accept everything. Neither is right.

**Decision:**

Route valid records to the production table and invalid records to a quarantine table. The pipeline continues for valid data. Invalid records are stored with their failure reason, the rule that rejected them, the pipeline, run ID, and timestamp.

**Reasoning:**

Failing the entire batch because 1.5% of records are malformed wastes all the valid data and creates unnecessary downtime. Accepting everything silently corrupts the production table. The quarantine system gives us the middle path.

The invalid records aren't lost — they can be inspected, corrected, and reprocessed once the upstream issue is fixed.

**Limitations:**

The production table will have a gap compared to the source until the quarantined records are reprocessed. Downstream dashboards or reports need to account for this. The incident will show the gap as a known, managed state rather than an undetected anomaly.

---

## ADR-009 — Adaptive baselines for anomaly detection

**Date:** 2026-10

**Status:** Accepted

**Context:**

Static row count thresholds like "alert if rows < 100,000" break immediately for any pipeline with natural volume variation (weekday vs weekend patterns, end-of-month spikes, etc.).

**Decision:**

Use historical baselines calculated from the pipeline's actual run history. The system computes expected range using mean, standard deviation, and IQR from recent runs (configurable lookback window). Deviations beyond a configurable z-score trigger an anomaly.

**Reasoning:**

A pipeline that normally runs 95k–105k rows on weekdays but 40k–60k rows on weekends will generate false positives constantly if the threshold is static. The adaptive baseline knows it's Saturday and adjusts expectations accordingly.

**Limitations:**

The baseline is only as good as the historical data. For a new pipeline with fewer than 14 runs, the baseline is unreliable and static thresholds should be used as a fallback. The lookback window should not be too long (data from 6 months ago may not represent current behaviour).

---

## ADR-010 — BigQuery as the metadata and incident state store

**Date:** 2026-10

**Status:** Accepted

**Context:**

The system generates a lot of metadata: pipeline runs, task results, quality check results, incident events, agent decisions, remediation actions, verification results. This needs to be stored somewhere queryable.

**Decision:**

Use BigQuery for all incident state and metadata storage.

**Reasoning:**

BigQuery is already in the stack for the data warehouse. Using it for metadata as well keeps the infrastructure simple — no additional managed databases. BigQuery's SQL interface makes it easy to query incident history, calculate KPIs, and build dashboard queries. Partitioned tables by date keep query costs controlled.

**Limitations:**

BigQuery has eventual consistency for DML operations (inserts, updates). For high-frequency status updates within a single incident lifecycle, this means the controller needs to be careful about reading back a record immediately after writing it. In practice, the incident lifecycle stages are separated by enough time that this isn't a problem.

---

## ADR-011 — Failure injection is a first-class concern

**Date:** 2026-10

**Status:** Accepted

**Context:**

The immune system is useless if it's never tested against real failures. Waiting for production failures to validate the system is not acceptable.

**Decision:**

Build a failure injection framework as a first-class component, not an afterthought. Each failure type has its own module, is documented with what it simulates and what the expected immune response is, and is covered by integration tests.

**Reasoning:**

The only way to trust the detection → diagnosis → remediation → verification loop is to run it end-to-end against controlled failures. The failure injection framework makes this repeatable and automated.

It also provides a way to demonstrate the system working, which matters for a portfolio project.

**Limitations:**

Failure injection in production environments needs to be gated carefully. The injection framework should have environment checks that prevent it from running in production unless explicitly overridden with a specific flag.

---

*Last updated: 2026-10*
