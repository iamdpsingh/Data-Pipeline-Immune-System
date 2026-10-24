# Disaster Recovery & Business Continuity Plan (DR / BCP)

## 1. RTO & RPO Objectives
The Data Pipeline Immune System supports critical enterprise business intelligence and financial reporting. Disaster recovery targets are defined as follows:

| Metric | Target SLA | Concrete Meaning |
| :--- | :--- | :--- |
| **Recovery Time Objective (RTO)** | **< 15 minutes** | Maximum allowable duration between catastrophic service interruption and operational restoration. |
| **Recovery Point Objective (RPO)** | **< 1 hour** | Maximum allowable age of data loss in the event of an unrecoverable regional disaster. |

---

## 2. Disaster Scenarios & Mitigation Strategies

### Scenario 1: Regional Cloud Outage (e.g. `us-central1` degraded)
1. **Cloud Run Failover**:
   - Secondary Cloud Run service is defined via Terraform in `us-east1`.
   - Google Cloud Load Balancing automatically routes webhook traffic to the healthy secondary region.
2. **BigQuery Cross-Region Replication**:
   - Production datasets configure cross-region dataset replication from `us-central1` to `us-east1`.
   - Secondary dataset can be promoted to primary within 5 minutes via `bq update --primary_replica`.
3. **Cloud Storage Dual-Region Buckets**:
   - Landing and quarantine buckets utilize dual-region storage (`nam4` - Iowa/South Carolina) guaranteeing 99.999999999% durability and immediate multi-zone availability.

---

### Scenario 2: Accidental Data Corruption or Erroneous Table Update
1. **BigQuery Time-Travel Point-in-Time Recovery**:
   - All production tables support 7-day snapshot restoration:
     ```bash
     # Restore table state to exactly 2 hours ago
     bq cp 'data-pipeline-immune-system:dpis_silver_prod.orders@-7200000' \
           data-pipeline-immune-system:dpis_silver_prod.orders_recovered
     ```
2. **Quarantine Dead-Letter Re-Extraction**:
   - Raw byte payloads remain stored immutably in GCS (`gs://dpis-source-*` and `gs://dpis-quarantine-*`).
   - Reprocessing jobs can rebuild any historical Silver partition from raw JSON/CSV objects.

---

### Scenario 3: Complete Project Infrastructure Destruction
If the GCP project or resource group is compromised:
1. Re-provision all infrastructure in 10 minutes using automated Terraform scripts:
   ```bash
   cd terraform/environments/production
   terraform init
   terraform apply -auto-approve
   ```
2. Re-deploy container images to Cloud Run from Artifact Registry.
3. Secrets are restored securely from the centralized enterprise vault or backup KMS bucket.
4. Execute `scripts/verify_pipeline_integrity.py` to confirm zero regressions.
