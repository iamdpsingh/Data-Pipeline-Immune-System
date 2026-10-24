# Zero-Downtime Schema Evolution Playbook
## 1. Additive Column Migrations
Additive columns (e.g. adding `loyalty_tier STRING`) are non-breaking and automatically registered in BigQuery using `schema_update_options = ['ALLOW_FIELD_ADDITION']`.
## 2. Breaking Column Type Migrations
Breaking changes (e.g. changing `amount` from `INT64` to `FLOAT64`):
1. Ingestion routes affected rows to quarantine partition.
2. State machine creates P1 incident awaiting approval.
3. Engineer reviews in dashboard and executes versioned table cutover.
