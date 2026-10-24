# Data Pipeline Immune System — Architecture Frequently Asked Questions (FAQ)

## 1. Safety & Determinism

### Q: Why do deterministic rules execute before the AI diagnosis layer?
**A:** In mission-critical production data platforms, predictability and low latency are paramount. Known failure patterns (e.g. transient network timeouts, standard socket resets, null foreign key spikes, explicit schema evolution) have well-understood deterministic remediation procedures. 
- Deterministic rules evaluate in **under 5 milliseconds** with 100% predictable outcomes.
- The AI diagnosis layer (Google Gemini via Vertex AI) is reserved strictly for complex, ambiguous, novel, or multi-symptom anomalies where deterministic pattern matching finds no exact rule match.
- This hybrid architecture eliminates LLM token costs for routine operational issues and eliminates hallucination risks.

### Q: What prevents an autonomous AI agent from executing a destructive command like `DROP TABLE`?
**A:** The **Never-Allow Invariant Gate** ([`src/risk/never_allow.py`](file:///Volumes/Work/daemons-lab/d.automation/Data%20Pipeline%20Immune%20System/src/risk/never_allow.py)).
- Prohibited actions (`DELETE_PRODUCTION_TABLE`, `EXECUTE_ARBITRARY_SQL`, `MODIFY_IAM_ROLE`, `EXPOSE_PII_PLAINTEXT`, `DISABLE_VALIDATION_RULE`) are hardcoded in an immutable Python `frozenset`.
- The Risk Agent evaluates this set *in code* before any action proposal can reach execution.
- If an agent or model proposes a blocked action, the system raises a hard `NeverAllowViolationError`, halts execution, and logs a P0 audit event. No prompt, configuration flag, or administrative override can bypass this boundary.

---

## 2. Resilience & Failure Modes

### Q: What happens if the LLM API is unavailable, times out, or exceeds rate quotas?
**A:** The Diagnosis Agent incorporates an automated fallback hierarchy:
1. Primary: Deterministic rule engine evaluation.
2. Secondary: If ambiguous, calls LLM diagnosis with a strict 4.0-second timeout.
3. Fallback: If the LLM API fails, times out, or returns invalid JSON, the system falls back to **Historical Incident Memory Matching** (`src/memory/vector_store.py`) in BigQuery, matching symptom vectors against past resolved incidents.
4. Safe Default: If no memory match exists, the incident is safely classified as `UNKNOWN_AMBIGUOUS_ANOMALY` with risk level `HIGH`, triggering a safe partition hold and on-call notification rather than guessing an unverified fix.

### Q: How does the Dead-Letter Quarantine gate guarantee zero data loss?
**A:** Unlike traditional systems that either fail the entire pipeline or silently drop corrupt rows, our Quarantine Gate splits micro-batches:
- Valid rows pass directly to the **Silver Lakehouse Tier** (`dpis_silver_<env>.<table_name>`).
- Corrupted rows are preserved with full raw byte fidelity in **Cloud Storage** (`gs://dpis-quarantine-<project-id>/...`) and indexed in the **BigQuery Quarantine Table** (`dpis_quarantine_<env>.<table_name>_quarantine`).
- Nothing is dropped. Once the upstream bug is resolved, records are idempotently merged into Silver via [`scripts/replay_quarantine.py`](file:///Volumes/Work/daemons-lab/d.automation/Data%20Pipeline%20Immune%20System/scripts/replay_quarantine.py).

---

## 3. Infrastructure & Cost

### Q: Why Cloud Run instead of persistent GCE virtual machines or Kubernetes?
**A:** 
- **Cost**: In development, Cloud Run scales to zero (`min_instances = 0`), incurring **$0.00** compute cost during idle periods. In production, `min_instances = 1` guarantees sub-100ms response with minimal base cost.
- **Maintenance**: Zero OS patching, kernel upgrades, or VM disk management.
- **Elastic Scale**: Automatically handles sudden 10x traffic spikes (up to 25 instances) and concurrency up to 80 requests per container.

### Q: Where are credentials and secrets stored, and how is leakage prevented?
**A:**
- Production secrets reside strictly in **Google Cloud Secret Manager**.
- Services authenticate using **GCP Workload Identity** (no JSON service account keys).
- For local development, `.gitignore` strictly ignores `*.env`, `.env`, and `*credential*.json`.
- Automated pre-commit checks and CI/CD security linters scan git diffs to prevent accidental credential commits.
