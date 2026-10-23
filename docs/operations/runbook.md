# Operational Runbook — Data Pipeline Immune System

Day-to-day operational reference. Use this when setting up a new environment, debugging the system, or following incident response procedures. Not every operation is covered here — for complex incident scenarios, see [`incident-response.md`](incident-response.md).

---

## Environment setup from scratch

### Prerequisites

- GCP account with project creation permissions
- `gcloud` CLI authenticated
- `terraform` >= 1.5
- Python 3.11+
- Docker (for Cloud Run builds)

### Step 1: Clone and install

```bash
git clone https://github.com/your-org/data-pipeline-immune-system.git
cd data-pipeline-immune-system
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Step 2: GCP project setup

```bash
# Create the dev project (or use an existing one)
gcloud projects create dpis-dev --name="DPIS Dev"
gcloud config set project dpis-dev

# Enable required APIs
gcloud services enable \
  bigquery.googleapis.com \
  storage.googleapis.com \
  run.googleapis.com \
  cloudcomposer.googleapis.com \
  secretmanager.googleapis.com \
  artifactregistry.googleapis.com \
  dataproc.googleapis.com \
  logging.googleapis.com \
  monitoring.googleapis.com
```

### Step 3: Terraform

```bash
cd terraform/
terraform init -backend-config=backends/dev.tfbackend
terraform plan -var-file=vars/dev.tfvars
terraform apply -var-file=vars/dev.tfvars
```

This creates all GCS buckets, BigQuery datasets/tables, service accounts, and IAM bindings.

### Step 4: Set secrets

```bash
# Set each required secret
echo -n "YOUR_VALUE" | gcloud secrets versions add dpis-bq-service-account-dev --data-file=-
echo -n "YOUR_VALUE" | gcloud secrets versions add dpis-airflow-api-key-dev --data-file=-
echo -n "YOUR_VALUE" | gcloud secrets versions add dpis-llm-api-key-dev --data-file=-
```

### Step 5: Deploy the immune service

```bash
# Build
docker build -t gcr.io/dpis-dev/immune-service:latest .

# Push
docker push gcr.io/dpis-dev/immune-service:latest

# Deploy
gcloud run deploy immune-service \
  --image gcr.io/dpis-dev/immune-service:latest \
  --region us-central1 \
  --no-allow-unauthenticated
```

### Step 6: Deploy Airflow DAGs

```bash
# Sync DAGs to Cloud Composer GCS bucket
gsutil -m rsync -r dags/ gs://dpis-dev-airflow-dags/dags/
```

### Step 7: Seed test data

```bash
bash scripts/seed_data.sh --environment dev
```

### Step 8: Verify the setup

```bash
python scripts/smoke_test.py --environment dev
```

If the smoke test passes, run a failure injection to test the full loop:

```bash
python failure_injection/row_anomaly.py --pipeline orders --drop-percentage 48
```

Wait ~5 minutes and check BigQuery:

```sql
SELECT incident_id, status, root_cause, confidence
FROM dpis_dev.incidents
ORDER BY detected_at DESC
LIMIT 5;
```

You should see a RESOLVED incident.

---

## Common operational tasks

### Check pipeline health scores

```sql
SELECT
  pipeline_id,
  health_score,
  status,
  last_run_status,
  last_run_at
FROM dpis_prod.pipeline_metrics
WHERE metric_date = CURRENT_DATE()
ORDER BY health_score ASC;
```

### List active incidents

```sql
SELECT
  incident_id,
  pipeline_id,
  incident_type,
  severity,
  status,
  detected_at,
  root_cause,
  confidence
FROM dpis_prod.incidents
WHERE status NOT IN ('RESOLVED', 'ESCALATED')
ORDER BY
  CASE severity WHEN 'P0' THEN 0 WHEN 'P1' THEN 1 WHEN 'P2' THEN 2 ELSE 3 END,
  detected_at DESC;
```

### Manually trigger detection for a run

```bash
curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  https://immune-service-{hash}-uc.a.run.app/detect \
  -H "Content-Type: application/json" \
  -d '{"pipeline_id": "orders", "run_id": "run-XXXX"}'
```

### View agent decisions for an incident

```sql
SELECT
  agent_name,
  decision_type,
  input_summary,
  output_summary,
  confidence,
  timestamp
FROM dpis_prod.agent_decisions
WHERE incident_id = 'INC-2026-042'
ORDER BY timestamp;
```

### Add a new pipeline to the registry

```sql
INSERT INTO dpis_prod.pipeline_registry (
  pipeline_id, pipeline_name, owner, schedule,
  sla_minutes, source, destination, criticality, enabled, created_at
) VALUES (
  'new_pipeline', 'New Pipeline', 'team@company.com',
  '0 6 * * *', 60, 'gs://dpis-prod-source/new/',
  'dpis_prod.silver_new', 'MEDIUM', TRUE, CURRENT_TIMESTAMP()
);
```

---

## Monitoring and alerting

The system publishes metrics to Cloud Monitoring. Key dashboards are in the GCP console under "Data Pipeline Immune System."

Active alerts:
- P0 incident detected → immediate PagerDuty/email
- P1 incident detected → Slack + email
- Health score drops below 70 → Slack
- Agent service error rate > 1% → Cloud Monitoring alert
- Human approval queue > 5 pending → Slack

---

## Maintenance tasks

### Refresh adaptive baselines

Baselines are recalculated automatically after each successful run. If you need to force a refresh (e.g., after a known anomalous period):

```bash
python scripts/refresh_baselines.py --pipeline orders --lookback-days 14
```

### Archive old incidents

Incidents older than 90 days are automatically archived to a separate BigQuery dataset. To manually trigger:

```bash
python scripts/archive_incidents.py --older-than-days 90
```

### Rotate secrets

```bash
# Create a new secret version
echo -n "NEW_VALUE" | gcloud secrets versions add dpis-llm-api-key-prod --data-file=-

# The application reads the latest version automatically
# Old versions are automatically disabled after 24 hours
```

---

## Deployment

### Deploy to staging

Automatic on merge to `main`. Monitor the GitHub Actions workflow.

### Deploy to production

1. Create a release tag: `git tag v1.x.x && git push origin v1.x.x`
2. Go to GitHub Actions → deploy-prod.yml
3. Review the Terraform plan in the workflow output
4. Approve the deploy step
5. Monitor smoke tests
6. Verify in Cloud Run console that the new revision is serving traffic

### Emergency rollback

```bash
# Cloud Run: route all traffic to previous revision
gcloud run services update-traffic immune-service \
  --to-revisions=PREV_REVISION_ID=100 \
  --region us-central1 \
  --project dpis-prod
```

For Airflow DAG rollback, revert the file in git and re-sync to GCS.

---

*Last updated: 2026-10*
