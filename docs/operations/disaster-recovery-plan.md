# Disaster Recovery & Business Continuity Plan
## 1. Recovery Time Objective (RTO) & Recovery Point Objective (RPO)
- RTO (Time to resume ingestion): < 15 minutes
- RPO (Maximum allowable data loss): 0 records (immutable bronze GCS backup)
## 2. Failover Architecture
In the event of a regional GCP outage in `us-central1`:
1. Terraform fails over Cloud Run deployment to `us-east1`.
2. BigQuery multi-region dataset replication handles read/write routing.
3. Airflow DAG triggers dual-write sync.
