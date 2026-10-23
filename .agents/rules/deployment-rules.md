# Deployment Rules — Data Pipeline Immune System

Deployment requirements and procedures. The goal is that another developer should be able to reproduce the full environment from scratch using only this documentation and the repository.

---

## Environment overview

| Environment | Purpose | GCP project |
|---|---|---|
| dev | Local development, fast iteration | `dpis-dev` |
| staging | Integration testing, pre-production validation | `dpis-staging` |
| production | Live system | `dpis-prod` |

Each environment has its own GCP project, service accounts, BigQuery datasets, and GCS buckets. Terraform manages all of this.

---

## Infrastructure provisioning (Terraform)

All GCP infrastructure is defined in `terraform/`. Do not create GCP resources manually.

```bash
# Initialise
cd terraform/
terraform init -backend-config=backends/{environment}.tfbackend

# Plan
terraform plan -var-file=vars/{environment}.tfvars

# Apply
terraform apply -var-file=vars/{environment}.tfvars
```

Terraform manages:
- GCS buckets (source, bronze, quarantine)
- BigQuery datasets and tables (DDL is applied via `terraform apply`)
- Service accounts and IAM bindings
- Cloud Run service (agent API)
- Secret Manager secrets (values are set separately, not by Terraform)
- VPC configuration

---

## Secret setup

After `terraform apply`, set secret values manually. Never pass them as Terraform variables or commit them anywhere.

```bash
# Set a secret value
echo -n "your-service-account-key" | \
  gcloud secrets versions add dpis-bq-service-account-{env} --data-file=-
```

Required secrets per environment:
- `dpis-bq-service-account-{env}` — BigQuery service account key
- `dpis-airflow-api-key-{env}` — Airflow REST API key
- `dpis-llm-api-key-{env}` — LLM provider API key

---

## Deployment process

### Agent service (Cloud Run)

```bash
# Build and push container
docker build -t gcr.io/dpis-{env}/immune-service:latest .
docker push gcr.io/dpis-{env}/immune-service:latest

# Deploy to Cloud Run (Terraform handles this on apply, but manual deploy:)
gcloud run deploy immune-service \
  --image gcr.io/dpis-{env}/immune-service:latest \
  --region us-central1 \
  --project dpis-{env} \
  --no-allow-unauthenticated
```

GitHub Actions handles this automatically on merge to `main` (staging) and after manual approval (production).

### Airflow DAGs

DAGs are deployed by syncing the `dags/` directory to the Airflow DAGs GCS bucket:

```bash
gsutil -m rsync -r dags/ gs://dpis-{env}-airflow-dags/dags/
```

### BigQuery schemas

DDL is managed by Terraform. If you need to add a column or table, update `sql/ddl/`, update the Terraform resources, and run `terraform apply`.

---

## CI/CD pipeline

GitHub Actions workflows:

| Workflow | Triggers | What it does |
|---|---|---|
| `tests.yml` | Every push | Lint, format check, unit tests, agent tests |
| `integration.yml` | PR to main | Integration tests against test GCP project |
| `security.yml` | PR to main | bandit, pip-audit, secret scanning |
| `terraform.yml` | PR with infra changes | terraform plan, validate |
| `deploy-staging.yml` | Merge to main | Deploy to staging, smoke tests |
| `deploy-prod.yml` | Manual trigger | Deploy to production, smoke tests, verification |

Production deploy requires a manual approval step in GitHub Actions. It cannot be triggered by a merge alone.

---

## Smoke tests post-deploy

After every deploy, the CI pipeline runs a smoke test suite:

```bash
python scripts/smoke_test.py --environment {env}
```

Smoke tests verify:
- Cloud Run service responds to `/health`
- BigQuery tables are accessible and have expected schema
- Airflow DAGs are present and enabled
- A detection cycle completes successfully on a test pipeline

If any smoke test fails, the deploy is marked failed and the previous version remains active (Cloud Run handles rollback automatically).

---

## Rollback

**Cloud Run:** Rollback to the previous revision in the GCP console or via:
```bash
gcloud run services update-traffic immune-service \
  --to-revisions=REVISION_ID=100 \
  --region=us-central1
```

**Airflow DAGs:** Revert the DAG file change in git and sync back to GCS.

**BigQuery schema:** Schema changes (additive) do not need rollback — new columns can be left in place. For a breaking schema change that somehow made it past review, follow the incident response procedure in `docs/operations/incident-response.md`.

---

## Reproducing from scratch

Complete setup sequence for a new developer:

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Authenticate with GCP: `gcloud auth application-default login`
4. Create GCP project and enable APIs (documented in `terraform/README.md`)
5. Run Terraform: `cd terraform && terraform init && terraform apply -var-file=vars/dev.tfvars`
6. Set secrets in Secret Manager
7. Sync Airflow DAGs to GCS
8. Deploy immune service to Cloud Run
9. Run seed data script: `bash scripts/seed_data.sh`
10. Run smoke tests: `python scripts/smoke_test.py --environment dev`
11. Run a failure injection scenario to verify end-to-end: `python failure_injection/row_anomaly.py --pipeline orders`

If step 11 produces a RESOLVED incident in BigQuery, the environment is working correctly.

---

*Last updated: 2026-10*
