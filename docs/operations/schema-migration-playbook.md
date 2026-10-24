# Schema Evolution & Drift Migration Playbook

## 1. Schema Drift Taxonomy & Safety Policies
Upstream microservices and third-party data feeds frequently alter schemas. The Data Pipeline Immune System categorizes every detected change into four deterministic tiers ([`src/validation/schema_drift.py`](file:///Volumes/Work/daemons-lab/d.automation/Data%20Pipeline%20Immune%20System/src/validation/schema_drift.py)):

| Drift Category | Concrete Example | Severity | Automated Action | Approval Required? |
| :--- | :--- | :--- | :--- | :--- |
| **NONE** | Identical column names, data types, nullability | None | Ingestion proceeds normally. | No |
| **ADDITIVE** | New nullable column added (e.g. `loyalty_tier STRING`) | P3 | Auto-updates BigQuery schema via `ALLOW_FIELD_ADDITION`. | No (Autonomous) |
| **BREAKING** | Existing column dropped, renamed, or type cast mutated | P1 | Pipeline pauses; holds partition in Bronze; dispatches high-priority alert. | **Yes (HITL Sign-Off)** |
| **PII_EXPOSURE** | New column matches PII keywords (`ssn`, `card_number`, `password`) | P0 | **Hard Block** via Never-Allow invariant gate; halts ingestion immediately. | Cannot be auto-approved |

---

## 2. Autonomous Handling of Additive Changes
When `SchemaDriftInspector.compare(baseline, observed)` detects a new non-breaking column:
1. Verifies that the new column name contains zero PII patterns (passes regex matching against credit card, SSN, secret, password).
2. Verifies that the column definition is declared `nullable = True`.
3. The Remediation Agent automatically issues a schema update to the destination BigQuery table:
   ```bash
   bq update --schema new_schema_with_loyalty_tier.json data-pipeline-immune-system:dpis_silver_prod.orders
   ```
4. The Verification Agent performs a test query confirming that existing downstream ETL queries and BI marts continue to execute without syntax or type errors.

---

## 3. Resolving Breaking Schema Mutations (P1 Approval Flow)
When an upstream team changes a data type (e.g. `amount FLOAT64` mutated to `amount STRING` with currency symbols `$45.00`):

1. **Detection & Hold**:
   - The Immune System blocks the Bronze-to-Silver promotion and flags incident:
     `INCIDENT: inc-drift-9821 | SEVERITY: P1 | ACTION: REQUIRE_APPROVAL`
2. **Review Options in Dashboard**:
   - Navigate to the **DPIS Industrial Command Center** -> **Active Incident Review**.
   - Review proposed schema diff showing affected fields and candidate transformation fixes.
3. **Option A: Authorize Compatibility View**:
   - If the type change is permanent, generate an adapter view or PySpark type-cast transform:
     ```sql
     CREATE OR REPLACE VIEW `dpis_silver_prod.v_orders` AS
     SELECT
         order_id,
         customer_id,
         SAFE_CAST(REPLACE(amount, '$', '') AS FLOAT64) AS amount,
         status,
         order_date
     FROM `dpis_silver_prod.orders_v2`;
     ```
   - Click **Authorize Remediation** in the dashboard modal or submit signed webhook.
4. **Option B: Reject & Quarantine**:
   - If the upstream deployment was accidental, click **Reject & Halt**.
   - Upstream team rolls back their service; quarantined partition is subsequently re-ingested using [`scripts/replay_quarantine.py`](file:///Volumes/Work/daemons-lab/d.automation/Data%20Pipeline%20Immune%20System/scripts/replay_quarantine.py).

---

## 4. Rollback & Disaster Recovery
If an auto-migrated additive schema column causes unexpected downstream issues:
```bash
# Roll back BigQuery table schema snapshot using time-travel
bq cp 'data-pipeline-immune-system:dpis_silver_prod.orders@-3600000' \
      data-pipeline-immune-system:dpis_silver_prod.orders_recovered
```
