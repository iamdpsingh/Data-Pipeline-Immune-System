---
name: Chaos Drill Scenario
about: Plan a synthetic failure injection drill against staging/dev
title: "[DRILL] "
labels: chaos-drill
---

### Target Component
- [ ] Airflow DAG Task
- [ ] GCS Ingestion Landing
- [ ] PySpark Silver Transformation
- [ ] BigQuery Warehouse Table

### Injected Anomaly
Describe the failure injection script.

### Acceptance Criteria
- [ ] MTTR < 2 minutes
- [ ] Zero unquarantined data corruption
- [ ] Structured audit entry in `dpis_audit.audit_log`
