-- BigQuery DDL — Core tables for the Data Pipeline Immune System
-- Run via Terraform (not manually) to keep state consistent.
-- Dataset: dpis_{environment}

-- ============================================================
-- pipeline_registry
-- The source of truth for which pipelines the immune system monitors.
-- New pipelines must be registered here before monitoring begins.
-- ============================================================
CREATE TABLE IF NOT EXISTS `{project}.{dataset}.pipeline_registry` (
  pipeline_id       STRING NOT NULL,
  pipeline_name     STRING NOT NULL,
  owner             STRING NOT NULL,      -- team email or individual
  schedule          STRING,               -- cron expression
  sla_minutes       INT64,                -- max acceptable run duration
  source            STRING,               -- GCS path or API endpoint
  destination       STRING,               -- BigQuery table (full path)
  criticality       STRING NOT NULL,      -- LOW, MEDIUM, HIGH, CRITICAL
  enabled           BOOL DEFAULT TRUE NOT NULL,
  created_at        TIMESTAMP NOT NULL,
  updated_at        TIMESTAMP
)
OPTIONS (description = "Registry of all monitored pipelines.");

-- ============================================================
-- pipeline_runs
-- One row per pipeline execution. Partitioned by execution_date
-- so queries against recent runs are fast and cheap.
-- ============================================================
CREATE TABLE IF NOT EXISTS `{project}.{dataset}.pipeline_runs` (
  run_id            STRING NOT NULL,
  pipeline_id       STRING NOT NULL,
  execution_date    DATE NOT NULL,
  start_time        TIMESTAMP NOT NULL,
  end_time          TIMESTAMP,
  duration_seconds  INT64,
  status            STRING NOT NULL,      -- RUNNING, SUCCESS, FAILED, SKIPPED
  rows_read         INT64,
  rows_written      INT64,
  rows_quarantined  INT64,
  error_type        STRING,               -- TIMEOUT, OOM, etc. (null if success)
  error_message     STRING,
  triggered_by      STRING                -- SCHEDULED, MANUAL, REMEDIATION
)
PARTITION BY execution_date
OPTIONS (description = "All pipeline run records. Partitioned by date.");

-- ============================================================
-- pipeline_tasks
-- Task-level detail for each run. Used by the Diagnosis Agent to
-- understand which stage in the pipeline failed.
-- ============================================================
CREATE TABLE IF NOT EXISTS `{project}.{dataset}.pipeline_tasks` (
  task_id           STRING NOT NULL,
  run_id            STRING NOT NULL,
  pipeline_id       STRING NOT NULL,
  task_name         STRING NOT NULL,
  execution_date    DATE NOT NULL,
  status            STRING NOT NULL,      -- SUCCESS, FAILED, SKIPPED, RUNNING
  start_time        TIMESTAMP,
  end_time          TIMESTAMP,
  retry_count       INT64 DEFAULT 0 NOT NULL,
  error_message     STRING,
  operator          STRING                -- Airflow operator type
)
PARTITION BY execution_date
OPTIONS (description = "Task-level results for each pipeline run.");

-- ============================================================
-- data_quality_results
-- Every quality check result. The Detection Agent queries this
-- to find failing checks. The Verification Agent writes post-remediation
-- results here to close the loop.
-- ============================================================
CREATE TABLE IF NOT EXISTS `{project}.{dataset}.data_quality_results` (
  quality_id        STRING NOT NULL,
  pipeline_id       STRING NOT NULL,
  table_name        STRING NOT NULL,
  run_id            STRING NOT NULL,
  check_name        STRING NOT NULL,      -- e.g., null_check_customer_id
  check_type        STRING NOT NULL,      -- COMPLETENESS, UNIQUENESS, VALIDITY, etc.
  expected_value    FLOAT64,
  actual_value      FLOAT64,
  threshold         FLOAT64,
  status            STRING NOT NULL,      -- PASS, FAIL, WARN
  severity          STRING,               -- P0, P1, P2, P3
  is_verification   BOOL DEFAULT FALSE NOT NULL,  -- TRUE if this is a post-remediation check
  timestamp         TIMESTAMP NOT NULL
)
PARTITION BY DATE(timestamp)
OPTIONS (description = "Quality check results, including post-remediation verification checks.");

-- ============================================================
-- schema_versions
-- Schema snapshot after each run. The Diagnosis Agent compares
-- current schema against previous to detect drift.
-- ============================================================
CREATE TABLE IF NOT EXISTS `{project}.{dataset}.schema_versions` (
  version_id        STRING NOT NULL,
  pipeline_id       STRING NOT NULL,
  table_name        STRING NOT NULL,
  run_id            STRING NOT NULL,
  schema_json       JSON NOT NULL,        -- full schema as JSON array of {name, type, nullable}
  change_type       STRING,               -- NONE, ADDITIVE, BREAKING (null for first run)
  changed_columns   JSON,                 -- list of changed column details
  recorded_at       TIMESTAMP NOT NULL
)
PARTITION BY DATE(recorded_at)
OPTIONS (description = "Schema snapshots per run for drift detection.");

-- ============================================================
-- pipeline_metrics
-- Time-series metrics for health score calculation.
-- One row per pipeline per day.
-- ============================================================
CREATE TABLE IF NOT EXISTS `{project}.{dataset}.pipeline_metrics` (
  metric_id           STRING NOT NULL,
  pipeline_id         STRING NOT NULL,
  metric_date         DATE NOT NULL,
  success_rate        FLOAT64,            -- % of runs that succeeded
  avg_duration_seconds FLOAT64,
  sla_compliance_rate FLOAT64,            -- % of runs within SLA
  quality_score       FLOAT64,            -- % of quality checks passing
  schema_stability    FLOAT64,            -- 1.0 = no changes, decreases per change
  freshness_score     FLOAT64,            -- 1.0 = always fresh, decreases per breach
  health_score        FLOAT64,            -- composite, 0–100
  health_status       STRING,             -- HEALTHY, WARNING, DEGRADED, CRITICAL
  calculated_at       TIMESTAMP NOT NULL
)
PARTITION BY metric_date
OPTIONS (description = "Daily pipeline health metrics and scores.");

-- ============================================================
-- incidents
-- One row per incident. The lifecycle state machine is enforced
-- in src/controller/states.py. Valid states:
-- DETECTED → CLASSIFIED → DIAGNOSED → RISK_ASSESSED →
-- ACTION_SELECTED → REMEDIATION → VERIFICATION → RESOLVED
-- → ESCALATED (from any state)
-- → BLOCKED (from RISK_ASSESSED)
-- ============================================================
CREATE TABLE IF NOT EXISTS `{project}.{dataset}.incidents` (
  incident_id       STRING NOT NULL,
  pipeline_id       STRING NOT NULL,
  incident_type     STRING NOT NULL,
  severity          STRING NOT NULL,      -- P0, P1, P2, P3
  status            STRING NOT NULL,
  detected_at       TIMESTAMP NOT NULL,
  classified_at     TIMESTAMP,
  diagnosed_at      TIMESTAMP,
  risk_assessed_at  TIMESTAMP,
  remediation_at    TIMESTAMP,
  verified_at       TIMESTAMP,
  resolved_at       TIMESTAMP,
  root_cause        STRING,
  confidence        FLOAT64,
  impact            STRING                -- human-readable impact description
)
PARTITION BY DATE(detected_at)
OPTIONS (description = "Incident lifecycle records. One row per incident.");

-- ============================================================
-- incident_events
-- State transition audit trail. Every state change is recorded
-- here so the full incident history is reconstructable.
-- ============================================================
CREATE TABLE IF NOT EXISTS `{project}.{dataset}.incident_events` (
  event_id          STRING NOT NULL,
  incident_id       STRING NOT NULL,
  from_state        STRING,
  to_state          STRING NOT NULL,
  reason            STRING,
  triggered_by      STRING NOT NULL,      -- agent name or "human:{user_id}"
  timestamp         TIMESTAMP NOT NULL
)
PARTITION BY DATE(timestamp)
OPTIONS (description = "Full audit trail of incident state transitions.");

-- ============================================================
-- diagnoses
-- Root cause analysis results from the Diagnosis Agent.
-- Linked to incidents via incident_id.
-- ============================================================
CREATE TABLE IF NOT EXISTS `{project}.{dataset}.diagnoses` (
  diagnosis_id        STRING NOT NULL,
  incident_id         STRING NOT NULL,
  root_cause          STRING NOT NULL,
  affected_pipeline   STRING NOT NULL,
  affected_table      STRING,
  confidence          FLOAT64 NOT NULL,
  evidence            JSON NOT NULL,          -- list of evidence strings
  recommended_action  STRING NOT NULL,
  similar_incidents   JSON,                   -- list of similar incident IDs from memory
  used_llm            BOOL DEFAULT FALSE NOT NULL,
  diagnosed_at        TIMESTAMP NOT NULL
)
PARTITION BY DATE(diagnosed_at)
OPTIONS (description = "Diagnosis results per incident.");

-- ============================================================
-- remediation_actions
-- What was done to fix the incident and the outcome.
-- ============================================================
CREATE TABLE IF NOT EXISTS `{project}.{dataset}.remediation_actions` (
  remediation_id    STRING NOT NULL,
  incident_id       STRING NOT NULL,
  action            STRING NOT NULL,
  reason            STRING,
  risk_level        STRING NOT NULL,
  approved_by       STRING,               -- NULL if auto-approved, email if human approved
  approval_id       STRING,
  execution_status  STRING NOT NULL,      -- SUCCESS, FAILED, PARTIAL
  details           JSON,
  started_at        TIMESTAMP NOT NULL,
  completed_at      TIMESTAMP
)
PARTITION BY DATE(started_at)
OPTIONS (description = "Remediation actions taken per incident.");

-- ============================================================
-- verification_results
-- Post-remediation quality check results. Each check is a row.
-- The Verification Agent writes these; the controller reads the
-- aggregate to determine if verification passed.
-- ============================================================
CREATE TABLE IF NOT EXISTS `{project}.{dataset}.verification_results` (
  verification_id   STRING NOT NULL,
  incident_id       STRING NOT NULL,
  check_name        STRING NOT NULL,
  expected          STRING,
  actual            STRING,
  status            STRING NOT NULL,      -- PASS, FAIL, WARN
  details           STRING,
  verified_at       TIMESTAMP NOT NULL
)
PARTITION BY DATE(verified_at)
OPTIONS (description = "Post-remediation verification check results.");

-- ============================================================
-- agent_decisions
-- Every decision made by any agent, with its reasoning.
-- This is the primary audit trail for autonomous decisions.
-- ============================================================
CREATE TABLE IF NOT EXISTS `{project}.{dataset}.agent_decisions` (
  decision_id       STRING NOT NULL,
  incident_id       STRING NOT NULL,
  agent_name        STRING NOT NULL,
  decision_type     STRING NOT NULL,
  input_summary     STRING,               -- metadata only, never raw data
  output_summary    STRING,
  confidence        FLOAT64,
  timestamp         TIMESTAMP NOT NULL
)
PARTITION BY DATE(timestamp)
OPTIONS (description = "Complete agent decision audit trail.");

-- ============================================================
-- approval_requests
-- Human approval requests for HIGH risk incidents.
-- The dashboard polls this table for pending requests.
-- ============================================================
CREATE TABLE IF NOT EXISTS `{project}.{dataset}.approval_requests` (
  approval_id       STRING NOT NULL,
  incident_id       STRING NOT NULL,
  diagnosis_summary STRING NOT NULL,
  proposed_action   STRING NOT NULL,
  risk_level        STRING NOT NULL,
  confidence        FLOAT64,
  evidence          JSON,
  status            STRING DEFAULT 'PENDING' NOT NULL,  -- PENDING, APPROVED, REJECTED
  requested_at      TIMESTAMP NOT NULL,
  responded_at      TIMESTAMP,
  responded_by      STRING
)
PARTITION BY DATE(requested_at)
OPTIONS (description = "Human approval queue for high-risk remediation actions.");

-- ============================================================
-- incident_memory
-- Historical incident knowledge used by the Diagnosis Agent
-- for similarity-based recommendations. Written by the Learning Agent.
-- ============================================================
CREATE TABLE IF NOT EXISTS `{project}.{dataset}.incident_memory` (
  memory_id             STRING NOT NULL,
  incident_id           STRING NOT NULL,
  incident_type         STRING NOT NULL,
  symptoms              JSON NOT NULL,          -- list of observed symptoms
  root_cause            STRING NOT NULL,
  successful_action     STRING,
  failed_actions        JSON,                   -- list of actions that didn't work
  pipeline_id           STRING,
  environment           STRING,
  diagnosis_confidence  FLOAT64,
  resolution_minutes    FLOAT64,
  verification_passed   BOOL,
  stored_at             TIMESTAMP NOT NULL
)
PARTITION BY DATE(stored_at)
OPTIONS (description = "Historical incident memory for similarity-based diagnosis.");

-- ============================================================
-- quarantine_records
-- Bad records that were quarantined rather than loaded to production.
-- These can be inspected, corrected, and reprocessed.
-- ============================================================
CREATE TABLE IF NOT EXISTS `{project}.{dataset}.quarantine_records` (
  quarantine_id     STRING NOT NULL,
  run_id            STRING NOT NULL,
  pipeline_id       STRING NOT NULL,
  record_data       JSON NOT NULL,
  failure_reason    STRING NOT NULL,
  rule_violated     STRING,
  quarantined_at    TIMESTAMP NOT NULL,
  reprocessed       BOOL DEFAULT FALSE NOT NULL,
  reprocessed_at    TIMESTAMP
)
PARTITION BY DATE(quarantined_at)
OPTIONS (description = "Bad records quarantined instead of rejected outright. Can be reprocessed.");
