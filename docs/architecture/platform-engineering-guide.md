# Platform Engineering & Architecture Guide — Data Pipeline Immune System

Welcome to the **Data Pipeline Immune System**! This comprehensive guide provides an end-to-end technical reference for platform engineers, data reliability engineers, and developers working on autonomous data reliability systems.

By reading this guide, you will understand:
1. What problem this system solves and why autonomous self-healing is necessary.
2. Every Google Cloud Platform (GCP) service used and why it was chosen.
3. The algorithms, data architectures, and safety patterns powering the platform.
4. How to navigate the code, run it locally, and safely contribute changes.

---

## 1. The Big Picture: Why Do We Need a "Data Pipeline Immune System"?

In enterprise data platforms, pipelines fail constantly:
- An upstream vendor API times out for 10 seconds.
- A mobile app releases an update that introduces an unexpected column or nulls out a user ID.
- An executor runs out of memory during a heavy batch.

### The Old Way (Manual On-Call):
1. Pipeline breaks at 2:00 AM.
2. An on-call engineer gets paged by PagerDuty.
3. The engineer wakes up, logs into a VPN, inspects Airflow logs, and discovers it was just a transient network glitch.
4. The engineer manually clicks "Clear Task" or triggers a backfill.
5. 45 minutes of downtime have passed, and downstream business dashboards were stale.

### The Immune System Way (Autonomous Self-Healing):
Just like the human immune system uses antibodies and white blood cells to neutralize pathogens without manual intervention:
1. **Detection Agent** catches the failure or statistical anomaly within milliseconds.
2. **Diagnosis Agent** evaluates deterministic rules first; if known, classifies the exact root cause.
3. **Risk Agent** checks strict safety boundaries (Never-Allow invariants).
4. **Remediation Agent** executes an idempotent fix (e.g. restarts the failed task with backoff or routes corrupted records into quarantine).
5. **Verification Agent** re-runs data quality checks on the database to prove the output is 100% correct.
6. **Learning Agent** records the resolution into BigQuery incident memory.
7. Total resolution time: **< 1 minute (MTTR: 0.7m)**. Engineers are not woken up, and data consumers never see corrupted numbers.

---

## 2. Google Cloud Platform (GCP) Services & Technology Stack

The system is designed for Google Cloud Platform. Here is every service utilized and the architectural role it plays:

```
[Cloud Build] ➔ Compiles Dockerfile ➔ Stores in [Artifact Registry]
                                               │
                                               ▼
[Cloud Storage (GCS)] ────► [Dataproc / Spark] ────► [Cloud Run (API)] ────► [BigQuery Lakehouse]
(Source, Bronze,             (Transformation &         (Autonomous            (Conformed Tables,
 Quarantine Buckets)          Quarantine Split)         State Controller)      Audit Trail, Memory)
                                                               │
                                                               ▼
                                                     [Secret Manager]
                                                     (SMTP / WhatsApp / IAM)
```

| GCP Service | What It Does In This Project | Why We Chose It |
|---|---|---|
| **Google Cloud Run** | Hosts our serverless controller API (`dpis-dev-api`). It receives Airflow webhooks, orchestrates the 6 specialized agents, and serves the dashboard API. | Stateless, scales to zero when idle (`min_instances = 0` in dev to minimize cost), deploys containers in seconds without Kubernetes cluster overhead. |
| **Google Cloud BigQuery** | Acts as our Lakehouse warehouse and incident store (`dpis_dev`, `dpis_silver_dev`, `dpis_gold_dev`, `dpis_audit`). | Native JSON column support, date partitioning, automatic clustering, and schema-drift inspection capabilities. |
| **Google Cloud Storage (GCS)** | Object storage for raw source payloads and dead-letter quarantine (`gs://dpis-source-...`, `gs://dpis-quarantine-...`). | High-throughput immutable landing, automatic lifecycle rules (e.g. delete after 90 days), and seamless integration with PySpark. |
| **Google Cloud Build** | Builds the production container image from `Dockerfile` directly on GCP compute without requiring local Docker. | Fast cloud compilation, zero local resource drain, and direct push rights into Artifact Registry. |
| **Google Artifact Registry** | Docker OCI container image repository (`dpis-repo` in `us-central1`). | Modern, secure replacement for Google Container Registry (GCR) with granular IAM access controls. |
| **Google Secret Manager** | Securely stores sensitive tokens: Slack webhooks, SMTP credentials, and WhatsApp API keys. | Zero secrets in git. Credentials are injected at runtime via Workload Identity rather than hardcoded `.env` files. |
| **Google Cloud Pub/Sub** | Asynchronous message broker for high-throughput anomaly events and incident notifications. | Decouples detection sensors from agent reasoning execution with at-least-once delivery guarantees. |
| **Dataproc / Serverless Spark** | Executes distributed PySpark transformation jobs (`orders_bronze_ingestion.py`, `orders_silver_transformation.py`). | Scales dynamically to process millions of transactions while executing dead-letter quarantine splits. |
| **Google Cloud IAM** | Enforces the Principle of Least Privilege across agent service accounts. | Detection, Diagnosis, Risk, and Verification agents have strictly read-only access. Only Remediation Agent has write access. |

---

## 3. Core Methods, Algorithms & Architectural Patterns

### 3.1. Adaptive Z-Score Anomaly Detection (ADR-009)
Why static thresholds fail:
A static rule like `"alert if daily rows < 80,000"` will generate false alarms every weekend if your platform normally processes 100,000 rows on weekdays and 50,000 on weekends.

Instead, [src/detection/baseline.py](file:///Volumes/Work/daemons-lab/d.automation/Data%20Pipeline%20Immune%20System/src/detection/baseline.py) calculates adaptive baselines:
$$\mu = \text{mean of historical runs over 14-day lookback window}$$
$$\sigma = \text{standard deviation of historical runs}$$
$$z = \frac{\text{actual rows} - \mu}{\sigma}$$
If $|z| > 2.0$ (configurable in `config/dev.yaml`), the system flags a statistical volume anomaly.

### 3.2. Deterministic Rules Before LLM (ADR-003)
Deterministic problems require deterministic solutions:
```
Pipeline Event ➔ Rules Engine ➔ Known Signature? ➔ Idempotent Fix (50ms, $0)
                                      │
                                     No (Novel Anomaly)
                                      ▼
                               LLM Diagnosis (Gemini 1.5)
```
If an Airflow task times out on its first attempt, we don't spend 3 seconds and LLM API tokens asking an AI what happened. The rule in `rules/detection_rules.yaml` immediately maps it to `TRANSIENT_TASK_FAILURE` with action `RETRY_TASK`.

### 3.3. Code-Enforced Never-Allow Bounds (ADR-004)
Prompt-level instructions to an LLM like `"please don't drop tables"` are unsafe because adversarial inputs or hallucinations can bypass them.

Our safety boundary lives in Python code in [src/risk/never_allow.py](file:///Volumes/Work/daemons-lab/d.automation/Data%20Pipeline%20Immune%20System/src/risk/never_allow.py):
- Even if an LLM returns a confidence of 0.99 recommending `DROP TABLE` or `TRUNCATE`, the Risk Agent intercepts it.
- An uncatchable `CriticalSafetyViolation` is raised, execution is aborted, and the action is blocked.

### 3.4. Medallion Lakehouse with Dead-Letter Quarantine (ADR-008)
When 25 corrupt records with negative prices arrive in a 100,000-row batch, you have two bad choices:
- Reject the entire batch: 99,975 valid customers don't get their orders processed.
- Load the whole batch: Your database is silently corrupted.

**The Quarantine Solution**:
Our [QuarantineHandler](file:///Volumes/Work/daemons-lab/d.automation/Data%20Pipeline%20Immune%20System/spark/utils/quarantine.py) splits the stream:
- 99,975 valid records write immediately to `dpis_silver_dev.orders`.
- 25 bad records write to `gs://dpis-quarantine-...` and `dpis_dev.quarantine_records` with the rejection rule and timestamp.

### 3.5. Automated Daily Reports & Hourly WhatsApp Pulses
- **Daily Email Digest**: Aggregates 24-hour BigQuery run counts, success rates, and quarantine tallies into an executive HTML email sent to configured stakeholder recipients.
- **Hourly WhatsApp Pulse**: Pushes a concise operational status message directly to mobile with current health score and active incident count.

---

## 4. Codebase Navigation Tour

| Directory / File | What Lives Here |
|---|---|
| [agents/](file:///Volumes/Work/daemons-lab/d.automation/Data%20Pipeline%20Immune%20System/agents/) | The 6 specialized agents: `detection_agent.py`, `diagnosis_agent.py`, `risk_agent.py`, `remediation_agent.py`, `verification_agent.py`, `learning_agent.py`. |
| [src/controller/](file:///Volumes/Work/daemons-lab/d.automation/Data%20Pipeline%20Immune%20System/src/controller/) | `controller.py` orchestrates the multi-agent lifecycle; `states.py` defines the state machine. |
| [src/validation/](file:///Volumes/Work/daemons-lab/d.automation/Data%20Pipeline%20Immune%20System/src/validation/) | `quality_engine.py` (nulls, duplicates, bounds) and `schema_drift.py` (PII leaks, type changes). |
| [src/notifications/](file:///Volumes/Work/daemons-lab/d.automation/Data%20Pipeline%20Immune%20System/src/notifications/) | `reporter.py` (daily executive email generator) and `whatsapp.py` (hourly mobile alerts). |
| [spark/](file:///Volumes/Work/daemons-lab/d.automation/Data%20Pipeline%20Immune%20System/spark/) | PySpark ingestion, transformation, and quarantine split utilities. |
| [sql/](file:///Volumes/Work/daemons-lab/d.automation/Data%20Pipeline%20Immune%20System/sql/) | DDL schemas (`create_tables.sql`), quality queries, health score rollups, and MTTR analytics. |
| [dashboard/](file:///Volumes/Work/daemons-lab/d.automation/Data%20Pipeline%20Immune%20System/dashboard/) | The interactive industrial command center (`index.html`, `styles.css`, `app.js`). |
| [tests/](file:///Volumes/Work/daemons-lab/d.automation/Data%20Pipeline%20Immune%20System/tests/) | Comprehensive unit, agent, data quality, and end-to-end self-healing tests. |

---

## 5. Developer Hands-On Quickstart

### Step 1: Run the Test Suite
Verify that your local environment is configured properly:
```bash
pytest -v
```

### Step 2: Trigger an Autonomous Healing Cycle
Send an incident payload to the controller endpoint:
```bash
curl -s -X POST "${CLOUD_RUN_URL:-http://localhost:8080}/api/v1/runs/complete" \
  -H "Content-Type: application/json" \
  -d '{"pipeline_id": "orders", "run_id": "test-run-001", "context": {"task_status": "FAILED", "error_type": "TIMEOUT", "retry_count": 0}}'
```
You will receive:
```json
{
  "incident_id": "inc-xxx",
  "final_state": "RESOLVED",
  "message": "Incident fully auto-remediated, verified, and learned.",
  "auto_remediated": true
}
```

### Step 3: View the BigQuery Audit Trail
Check the audit log written by the controller directly in BigQuery:
```bash
bq query --use_legacy_sql=false \
  "SELECT event_id, incident_id, agent_name, action_type, status, timestamp FROM \`dpis_dev.audit_log\` ORDER BY timestamp DESC LIMIT 5"
```

### Step 4: Run the Daily Email & WhatsApp CLI Dispatchers
```bash
# Test Daily Report generation (runs in safe dry-run mode if credentials not set)
python3 scripts/send_daily_report.py --environment dev

# Test Hourly WhatsApp alert dispatch
python3 scripts/send_hourly_whatsapp.py --status HEALTHY --score 98.5
```

---

## 6. How to Contribute Safely

1. **Never weaken never-allow rules**: Any modification to `rules/safety_rules.yaml` or `src/risk/never_allow.py` requires an Architecture Decision Record (ADR) and review.
2. **Always test failure cases**: When writing tests, test the negative / malicious cases (e.g. attempting to run `DROP TABLE`), not just happy paths.
3. **Keep secrets out of git**: Never commit `.env` or service account JSON files. Use GCP Secret Manager.
4. **Follow conventional commits**: Keep commits atomic and use standard prefixes (`feat:`, `fix:`, `docs:`, `test:`).
