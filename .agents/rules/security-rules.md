# Security Rules — Data Pipeline Immune System

Security requirements specific to this project. These aren't general security guidelines — they're the specific decisions and requirements for this system.

---

## Secrets management

**GCP Secret Manager is the only approved secrets store.** No credentials, API keys, service account JSON files, or tokens go into git. Not in `.env` files, not in config YAMLs, not in test fixtures.

Local development setup:

```bash
# Authenticate with gcloud
gcloud auth application-default login

# The application reads secrets at runtime from Secret Manager
# GOOGLE_CLOUD_PROJECT must be set to your dev project
export GOOGLE_CLOUD_PROJECT=your-dev-project-id
export ENVIRONMENT=dev
```

The `src/config/secrets.py` module loads secrets from Secret Manager at startup. The secret names follow the pattern `dpis-{secret_name}-{environment}`. For example: `dpis-bq-service-account-dev`.

---

## Service account permissions

Each service account has the minimum permissions required:

| Service account | Permissions |
|---|---|
| `dpis-pipeline-sa` | BigQuery Data Editor (specific datasets), GCS Object Viewer/Creator |
| `dpis-immune-sa` | BigQuery Data Viewer (all datasets), BigQuery Data Editor (incident tables only) |
| `dpis-remediation-sa` | Airflow REST API caller, GCS Object Admin (source bucket), BigQuery Data Editor (staging tables only) |
| `dpis-dashboard-sa` | BigQuery Data Viewer (incident and metrics tables) |

The Remediation Agent's service account (`dpis-remediation-sa`) is specifically scoped to only the staging/bronze layer tables. It cannot write to silver or gold tables.

---

## Never-allow enforcement

The never-allow rules in `rules/safety_rules.yaml` are the policy definition. The enforcement happens in `src/risk/never_allow.py` in application code. The LLM cannot bypass this.

The enforcement code is simple and deterministic:

```python
NEVER_ALLOW_ACTIONS = {
    "DELETE_PRODUCTION_TABLE",
    "DROP_SCHEMA",
    "MODIFY_IAM_PERMISSION",
    "EXECUTE_ARBITRARY_SQL",
    "DISABLE_VALIDATION",
    # ... full list in never_allow.py
}

def check_never_allow(action: str) -> bool:
    """Returns True if the action is blocked unconditionally."""
    return action in NEVER_ALLOW_ACTIONS
```

This list is only modified by code review, not by the LLM or any runtime configuration.

---

## Data sensitivity

The system handles customer data (orders, customers, payments). PII fields are documented in `schemas/` for each table. The Diagnosis Agent is forbidden from logging the contents of PII fields, even in debug mode.

If the detection system finds an unexpected PII column in a source (e.g., a new `ssn` or `credit_card` field), this is automatically a `P0` incident, blocked immediately, and escalated to a human. No auto-remediation is attempted.

---

## Audit trail

Every autonomous decision must be recoverable from BigQuery tables. The `agent_decisions` table stores:

```
decision_id
incident_id
agent_name
decision_type
input_summary      (not raw data — just metadata)
output_summary
confidence
timestamp
```

The `incident_events` table stores every state transition:

```
event_id
incident_id
from_state
to_state
reason
triggered_by       (agent name or "human:{user_id}")
timestamp
```

If an auditor asks "why did the system automatically fix incident INC-2026-042?", the answer must be derivable from these tables alone.

---

## Network security

The Cloud Run service is not publicly accessible. It is only reachable from within the VPC, from Airflow (which runs in the same network), or from authenticated GCP services.

All BigQuery queries use the project's default VPC Service Controls where enabled.

---

## Failure injection security

The failure injection framework has a hard environment check:

```python
import os

def _check_injection_allowed():
    env = os.getenv("ENVIRONMENT", "production")
    if env == "production":
        override = os.getenv("DPIS_ALLOW_INJECTION_IN_PRODUCTION")
        if override != "I_UNDERSTAND_THE_RISK":
            raise EnvironmentError(
                "Failure injection is disabled in production. "
                "Set DPIS_ALLOW_INJECTION_IN_PRODUCTION=I_UNDERSTAND_THE_RISK to override."
            )
```

This check is not removed for any reason, including testing.

---

## Dependency security

Dependencies are pinned in `requirements.txt`. Run `pip-audit` as part of CI to detect known vulnerabilities. Do not update dependencies without reviewing the changelog.

`bandit` runs in CI to catch common Python security issues (hardcoded passwords, SQL injection patterns, unsafe deserialization).

---

*Last updated: 2026-10*
