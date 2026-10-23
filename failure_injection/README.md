# Failure Injection Scenarios

This directory contains controlled failure injection scripts used to test and demonstrate the immune system's detection, diagnosis, and remediation capabilities.

These scripts are **test and demonstration tools only**. Every script has an environment guard that prevents it from running in production without an explicit override.

---

## Usage pattern

```bash
# Always set the environment first
export ENVIRONMENT=dev

# Then run the injection
python failure_injection/row_anomaly.py --pipeline orders --drop-percentage 48
```

After injection, the pipeline runs normally (or is triggered manually). The immune system should detect the problem and respond within a few minutes.

---

## Scenario catalogue

### 1. Row count anomaly (`row_anomaly.py`)

**What it simulates:** Upstream API delivers partial data — only a fraction of the expected daily records.

**Why this matters:** This is one of the most common real-world pipeline failures. The pipeline itself succeeds, which means the only signal is the row count being wrong.

| Trigger | drop-percentage 20–40% | drop-percentage 40-80% | drop-percentage >80% |
|---|---|---|---|
| Severity | P3 | P1 | P1 |
| Expected root cause | UPSTREAM_PARTIAL_LOAD | UPSTREAM_PARTIAL_LOAD | UPSTREAM_PARTIAL_LOAD |
| Auto-remediated? | Yes | Yes | Yes (P1 but low-risk action) |

```bash
python failure_injection/row_anomaly.py --pipeline orders --drop-percentage 48
```

---

### 2. Schema drift (`schema_drift.py`)

**What it simulates:** Source schema changes — either a new column (additive), a type change (breaking), or a PII column appearing.

| Scenario | Severity | Expected response |
|---|---|---|
| Additive (new column) | P3 | Auto-update staging schema |
| Breaking (type change) | P1 | BLOCK → human approval |
| PII column detected | P0 | BLOCK immediately, no auto-remediation |

```bash
# Additive — new phone column
python failure_injection/schema_drift.py --pipeline orders --type additive --column phone --dtype VARCHAR(20)

# Breaking — age changed from INT to VARCHAR
python failure_injection/schema_drift.py --pipeline orders --type breaking --column age --new-dtype VARCHAR(10)

# PII — SSN column appears
python failure_injection/schema_drift.py --pipeline orders --type pii --column ssn
```

---

### 3. Null spike (`null_spike.py`)

**What it simulates:** A significant proportion of records arrive with nulls in an important field.

| Null percentage | Severity |
|---|---|
| 2–5% above baseline | P3 |
| 5–15% above baseline | P2 |
| > 15% above baseline | P1 |

```bash
python failure_injection/null_spike.py --pipeline orders --column customer_id --null-percentage 12
```

---

### 4. Duplicate spike (`duplicate_spike.py`)

**What it simulates:** Source delivers the same records multiple times (e.g., API pagination bug, double-ingestion).

Expected response: DUPLICATE_SPIKE detected → QUARANTINE_BAD_RECORDS if within threshold, ESCALATE if above 10%.

```bash
python failure_injection/duplicate_spike.py --pipeline orders --duplicate-percentage 8
```

---

### 5. API failure (`api_failure.py`)

**What it simulates:** The source API returns timeouts or 5xx errors during extraction.

Expected response: API_TIMEOUT detected → RETRY_SOURCE_EXTRACTION (up to 3 times with backoff) → RESOLVED if API recovers.

```bash
python failure_injection/api_failure.py --pipeline orders --failure-type timeout --duration-seconds 120
```

---

### 6. Missing partition (`missing_partition.py`)

**What it simulates:** An expected date partition is absent from the source or intermediate table.

Expected response: MISSING_PARTITION detected → REPROCESS_PARTITION → RESOLVED.

```bash
python failure_injection/missing_partition.py --pipeline orders --partition-date 2026-10-20
```

---

## Verifying the immune response

After any injection, check BigQuery for the incident:

```sql
SELECT
  incident_id,
  incident_type,
  severity,
  status,
  root_cause,
  confidence,
  detected_at,
  resolved_at
FROM dpis_dev.incidents
WHERE pipeline_id = 'orders'
ORDER BY detected_at DESC
LIMIT 3;
```

And the full decision trail:

```sql
SELECT
  ad.agent_name,
  ad.decision_type,
  ad.output_summary,
  ad.confidence,
  ad.timestamp
FROM dpis_dev.agent_decisions ad
JOIN dpis_dev.incidents i ON ad.incident_id = i.incident_id
WHERE i.pipeline_id = 'orders'
ORDER BY ad.timestamp;
```

---

## Production safety

Every script calls `_check_injection_allowed()` which raises `EnvironmentError` if `ENVIRONMENT=production` and `DPIS_ALLOW_INJECTION_IN_PRODUCTION` is not set to `I_UNDERSTAND_THE_RISK`. This is intentional and not a soft warning — the script exits hard.

Do not remove this guard.
