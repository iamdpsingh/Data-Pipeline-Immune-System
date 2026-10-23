# Security Model — Data Pipeline Immune System

The **Data Pipeline Immune System** executes autonomous corrective decisions against production data platforms. Because autonomous agents have the potential to cause catastrophic damage if compromised or misconfigured, security is not an afterthought or an external wrapper—it is embedded as deterministic code invariants in every layer of the architecture.

This document outlines the threat model, least-privilege role boundaries, never-allow code invariants, credential isolation, and PII protection policies enforced across the platform.

---

## 1. Threat Model & Blast Radius Analysis

When deploying autonomous AI agents in data engineering environments, the primary threat vectors include:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        THREAT TAXONOMY & DEFENSE                       │
├────────────────────────────┬───────────────────────────────────────────┤
│ Threat Vector              │ Defense Mechanism                         │
├────────────────────────────┼───────────────────────────────────────────┤
│ LLM Hallucination          │ Deterministic rules engine runs first;    │
│                            │ Never-Allow code bounds override AI score │
├────────────────────────────┼───────────────────────────────────────────┤
│ Prompt Injection in Feeds  │ Structured output parsing; Agents do not  │
│                            │ execute free-form text or dynamic SQL     │
├────────────────────────────┼───────────────────────────────────────────┤
│ Data Exfiltration          │ Private VPC Service Controls; Cloud Run   │
│                            │ internal ingress only; No public egress   │
├────────────────────────────┼───────────────────────────────────────────┤
│ Privilege Escalation       │ Workload Identity; IAM per-agent role     │
│                            │ separation; Service account least privilege│
├────────────────────────────┼───────────────────────────────────────────┤
│ Schema / Data Destruction  │ Hardcoded NEVER_ALLOW_ACTIONS in code;    │
│                            │ BigQuery table deletion API blocked       │
└────────────────────────────┴───────────────────────────────────────────┘
```

---

## 2. Principle of Least Privilege (Agent Permissions)

Permissions are decoupled and strictly segmented across specialized agents. No single agent possesses end-to-end read-write access across the platform.

| Agent | GCP IAM Role / BigQuery Access | Write Scope | Blast Radius |
|---|---|---|---|
| **Detection Agent** | `roles/bigquery.dataViewer` | **NONE** (Read Only) | Zero mutation risk |
| **Diagnosis Agent** | `roles/bigquery.dataViewer` | **NONE** (Read Only) | Zero mutation risk |
| **Risk Agent** | `roles/bigquery.dataViewer` | **NONE** (Read Only) | Zero mutation risk |
| **Remediation Agent** | `roles/bigquery.dataEditor` (Restricted) | **LIMITED WRITE** to pre-approved handlers only | Staging / Bronze / Quarantine tables |
| **Verification Agent** | `roles/bigquery.dataViewer` | **NONE** (Read Only) | Zero mutation risk |
| **Learning Agent** | `roles/bigquery.dataEditor` | **INCIDENT MEMORY ONLY** (`incident_memory`) | Cannot touch data marts |

### Critical Restriction:
The **Remediation Agent** cannot:
- Execute arbitrary SQL queries.
- Grant, alter, or inspect IAM permissions.
- Write directly to Gold reporting marts or Silver conformed tables.
- Drop schemas or truncate tables.

---

## 3. Never-Allow Code Boundaries (Runtime Hard Invariants)

In accordance with **ADR-004**, confidence scores and LLM recommendations **never override hard safety rules**.

The authoritative list of prohibited actions is codified in `src/risk/never_allow.py` as an immutable `frozenset[str]`. Even if the Diagnosis Agent produces a `1.0` confidence score recommending one of these actions, the Risk Agent and Controller block execution immediately with a `NeverAllowViolation`.

```python
NEVER_ALLOW_ACTIONS: frozenset[str] = frozenset({
    "DELETE_PRODUCTION_TABLE",      # Irreversible table destruction
    "DROP_SCHEMA",                  # Schema dropping
    "EXECUTE_ARBITRARY_SQL",        # Unchecked SQL strings
    "MODIFY_IAM_PERMISSION",        # Privilege escalation vector
    "DISABLE_VALIDATION",           # Safety gate bypass
    "BYPASS_QUALITY_GATE",          # Bypassing checks
    "EXPOSE_PII_COLUMN",            # Privacy violation
    "MODIFY_FINANCIAL_RECORD",      # Audit / compliance breach
    "DELETE_QUARANTINE_TABLE",      # Dead-letter audit loss
    "DELETE_INCIDENT_MEMORY",       # Historical loss
    "TRUNCATE_GOLD_TABLE",          # Mart destruction
    "MODIFY_GOLD_TABLE_SCHEMA",     # Breaking downstream BI
    "GRANT_PUBLIC_ACCESS",          # Data leak
    "DISABLE_AUDIT_LOGGING",        # Traceability tampering
})
```

---

## 4. Google Cloud Platform Security & IAM

All cloud resources are provisioned via Terraform in GCP Project `data-pipeline-immune-system`.

### Dedicated Service Accounts
Immune agents operate under a dedicated service account:
`dpis-{environment}-agent-sa@data-pipeline-immune-system.iam.gserviceaccount.com`

### IAM Bindings:
- **Control Dataset (`dpis_{env}`)**: `roles/bigquery.dataEditor` for writing incidents, runs, and audit logs.
- **Silver Conformed (`dpis_silver_{env}`)**: `roles/bigquery.dataViewer` (agents read metrics but cannot mutate conformed records directly).
- **Quarantine Bucket (`gs://dpis-{env}-quarantine`)**: `roles/storage.objectAdmin` for routing rejected rows to dead-letter storage.
- **Cloud Run Service (`dpis-{env}-api`)**: Deployed with ingress set to `INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER` preventing unauthorized public Internet invocation.

---

## 5. Secret Management & Credentials

1. **Zero Git Secrets Policy**: No database passwords, API keys, service account JSON files, or webhooks are committed to git or stored in `.env` files.
2. **GCP Secret Manager**: All sensitive credentials reside in Secret Manager:
   - Slack webhook for incident alerts: `projects/data-pipeline-immune-system/secrets/dpis-{env}-slack-webhook`
   - Upstream API tokens and external database connections.
3. **Automated Secret Scanning**: The CI/CD pipeline runs `bandit` and automated secret scanners on every pull request.

---

## 6. PII Exposure Detection & Immediate P0 Block

Data privacy is enforced at ingestion landing:
- The [SchemaDriftInspector](file:///Volumes/Work/daemons-lab/d.automation/Data%20Pipeline%20Immune%20System/src/validation/schema_drift.py) evaluates all incoming column definitions against sensitive PII regex patterns:
  - Social Security Numbers (`ssn`, `social_security`)
  - Payment Cards (`credit_card`, `card_number`, `cvv`)
  - Passwords and Secrets (`password`, `secret`, `token`)
- **Action**: Detection of any PII token instantly triggers a **P0 Severity** incident, immediately halts the pipeline, and generates a security notification. Automated remediation is prohibited—resolution requires manual investigation and data compliance sign-off.
