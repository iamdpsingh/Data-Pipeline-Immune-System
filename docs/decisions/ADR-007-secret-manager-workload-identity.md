# ADR-007: GCP Secret Manager & Workload Identity Security Architecture

## Status: Accepted (In Production)

## Context
The Data Pipeline Immune System integrates with numerous external and cloud services:
- Google Cloud Platform APIs (BigQuery, Cloud Storage, Cloud Pub/Sub, Cloud Run)
- LLM Diagnosis Providers (Google Gemini API via Vertex AI)
- Notification Dispatchers (SMTP servers, Telegram Bot API)
- Airflow Orchestrator REST APIs

Storing credentials, API tokens, or service account keys in code repositories, unencrypted `.env` files, or container image layers introduces severe supply-chain risks, credential leakage vectors, and compliance audit failures.

## Decision
We enforce a zero-trust credential architecture combining **Google Cloud Secret Manager** with **GCP Workload Identity Federation**:

1. **Centralized Secret Storage**:
   - Google Secret Manager is the sole authoritative source of truth for runtime secrets (`GEMINI_API_KEY`, `SMTP_PASSWORD`, `TELEGRAM_BOT_TOKEN`, `ALERT_WEBHOOK_URL`).
   - Secrets are versioned and access-controlled via IAM role bindings (`roles/secretmanager.secretAccessor`).

2. **Keyless Cloud Authentication (Workload Identity)**:
   - No long-lived service account key files (`.json`) are downloaded or stored in persistent filesystems.
   - Cloud Run, Cloud Composer (Airflow), and Dataproc tasks assume designated GCP Service Accounts through Workload Identity and metadata server token exchange.

3. **Local Development Isolation**:
   - For local CLI development and tests, a gitignored `.env` file is used.
   - `.gitignore` strictly blocks all variations of `*.env`, `.env`, and `*credential*.json`.
   - A sanitized template ([`.env.example`](file:///.env.example)) provides dummy placeholders and links to setup documentation without storing real credentials.

4. **Runtime Retrieval & Caching**:
   - Application configuration (`src/config/settings.py`) loads secrets dynamically at startup via GCP Secret Manager client SDK, falling back gracefully to sanitized local environment variables in local dev mode.
   - Whitespace stripping and input sanitation prevent common credential formatting errors (e.g. spaces in Gmail App Passwords).

## Consequences

### Positive
- **Zero Git Leakage**: Zero plain-text credentials or API tokens are checked into version control.
- **Audit Logging**: Every secret access operation is logged to GCP Cloud Audit Logs, enabling real-time compliance tracking.
- **Seamless Secret Rotation**: Secrets can be rotated in Secret Manager without requiring code changes or application rebuilds.

### Negative / Trade-Offs
- Local developers must have GCP IAM permissions or a correctly configured local `.env` file to test live service integrations.
- Increased startup time (approx. 50ms-120ms) during container initialization to fetch secret payloads from Secret Manager API.
