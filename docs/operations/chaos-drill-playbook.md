# Autonomous Chaos Engineering & Failure Injection Playbook

## 1. Objectives & Safety Guardrails
Chaos drills validate that the Data Pipeline Immune System autonomously detects, isolates, and remediates operational failures without human intervention, while strictly observing safety boundaries.

> [!CAUTION]
> **Environment Guard:** Chaos failure injection is restricted by code to `dev` and `staging` environments. Running chaos drills in `production` is hard-blocked by `ImmuneSystemController` unless `--force-prod-disaster-drill` is explicitly passed alongside signed security approval.

---

## 2. Standard Chaos Drill Matrix

| Drill ID | Failure Scenario | Target Component | Expected Autonomous Response | Invariant Tested |
| :--- | :--- | :--- | :--- | :--- |
| **DRILL-01** | Transient Airflow Socket Timeout | Silver ETL Task | Detection trips in <50ms -> Diagnosis classifies `TRANSIENT_TASK_FAILURE` -> Low Risk -> Idempotent retry with exponential backoff -> Verified clean. | Auto-retry works without human intervention; MTTR < 1.0m. |
| **DRILL-02** | Corrupted Value Spike (42 bad rows) | Quarantine Gate | Quarantine split routes 42 corrupted rows to GCS DLQ & BQ quarantine table; 4,958 clean rows promoted to Silver. | 100% Data Cleanness Guarantee: Zero corrupt records in Silver. |
| **DRILL-03** | Upstream Feed Volume Drop (320 rows vs 5,000 expected) | Adaptive Baseline | Statistical baseline flags $z = -176.4$; controller holds downstream Gold partition to protect BI dashboards. | Protects executive dashboards from displaying skewed aggregates. |
| **DRILL-04** | PII Plaintext Column Injection (`credit_card_number`) | Never-Allow Engine | Schema inspector identifies PII keywords -> Tripped P0 critical boundary -> Never-Allow hard-blocks pipeline immediately. | Code-enforced safety bound: Zero plaintext PII enters lakehouse. |
| **DRILL-05** | Breaking Schema Mutation (Float to String change) | Human-in-the-Loop | Diagnosis classifies `BREAKING_SCHEMA_DRIFT` -> Evaluated P1 HIGH RISK -> Halts execution, dispatches alert, awaits human sign-off. | ADR-014 HITL State Gate: Destructive changes cannot auto-execute. |

---

## 3. Drill Execution Procedures

### Executing Drill 01 (Transient Timeout)
```bash
python3 scripts/run_chaos_scenario.py --scenario=transient_timeout --pipeline=orders --env=dev
```
- **Verification**: Check terminal logs for `[AuditTrail] Agent=RemediationAgent Action=RETRY_TASK Status=SUCCESS`.

### Executing Drill 02 (Corrupted Records Quarantine Split)
```bash
python3 scripts/run_chaos_scenario.py --scenario=corrupted_quarantine --records=5000 --corrupted=42 --env=dev
```
- **Verification**:
  ```sql
  SELECT COUNT(*) FROM `data-pipeline-immune-system.dpis_silver_dev.orders` WHERE amount <= 0; -- MUST RETURN 0
  SELECT COUNT(*) FROM `data-pipeline-immune-system.dpis_quarantine_dev.orders_quarantine` WHERE DATE(quarantined_at) = CURRENT_DATE(); -- MUST RETURN 42
  ```

### Executing Drill 04 (PII Never-Allow Violation)
```bash
python3 scripts/run_chaos_scenario.py --scenario=pii_exposure --pipeline=orders --env=dev
```
- **Verification**: Ensure system raises `NeverAllowViolationError` and logs event to BigQuery audit stream with `status = 'BLOCKED'`.

---

## 4. Post-Drill Restoration & Cleanup
1. Run the verification script:
   ```bash
   python3 scripts/verify_pipeline_integrity.py --pipeline=orders --env=dev
   ```
2. Replay test quarantine records or purge drill partitions:
   ```bash
   python3 scripts/replay_quarantine.py --pipeline=orders --purge-test-runs --env=dev
   ```
3. Generate and inspect post-drill daily health report:
   ```bash
   python3 scripts/send_daily_report.py --env=dev
   ```
