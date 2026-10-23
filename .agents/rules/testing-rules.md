# Testing Rules — Data Pipeline Immune System

Testing conventions and expectations for this project. Read this before writing or modifying tests.

---

## Test organisation

```
tests/
├── unit/           Fast, isolated tests with no external dependencies
├── integration/    Tests against real GCP services (or emulators in CI)
├── agents/         Agent-specific tests with controlled inputs
├── data_quality/   Quality check tests against known-good and known-bad datasets
├── remediation/    Remediation action tests (staged environment)
└── end_to_end/     Full failure → detect → diagnose → remediate → verify flow
```

Unit tests run on every commit. Integration and end-to-end tests run on every PR. End-to-end tests against a real GCP test project run pre-deploy.

---

## What must be tested

### Safety-critical paths (never skip these)

Every never-allow rule must have an explicit test that verifies it cannot be bypassed:

```python
class TestNeverAllowRules:
    """
    These tests exist because the never-allow list is the hardest safety boundary
    in the system. If any of these fail, something has gone seriously wrong.
    """

    def test_schema_deletion_blocked_regardless_of_confidence(self):
        ...

    def test_pii_exposure_blocked_regardless_of_confidence(self):
        ...

    def test_production_table_deletion_blocked(self):
        ...

    def test_arbitrary_sql_blocked(self):
        ...
```

### Risk classification

Test that each root cause maps to the expected risk level. Test boundary conditions — a diagnosis with confidence just below `0.75` should escalate even if the root cause alone would be LOW risk.

### Verification

Test that verification correctly rejects a "successful" pipeline run that produced wrong data. The point of verification is to catch exactly this case.

### Adaptive baseline

Test that the baseline calculation handles:
- New pipelines with < 14 historical runs (should fall back to static threshold)
- Day-of-week patterns (Saturday baseline should not be compared against weekday average)
- Outlier runs not distorting the baseline

### Failure injection → detection

For each failure injection type, there should be a test that:
1. Injects the failure
2. Runs the detection agent
3. Asserts the correct anomaly type and severity were detected

---

## Test naming convention

`test_{function_or_component}_{scenario}_{expected_outcome}`

Examples:
- `test_detect_row_count_anomaly_below_baseline_raises_p1`
- `test_risk_agent_unknown_root_cause_requires_human_approval`
- `test_verification_fails_when_null_rate_exceeds_threshold`
- `test_never_allow_blocks_schema_deletion_at_high_confidence`

---

## Mocking and dependencies

For unit tests, inject mock BigQuery clients. Do not make real GCP calls in unit tests — they are slow and require credentials.

```python
from unittest.mock import MagicMock, patch

def test_detection_row_count_anomaly():
    mock_bq = MagicMock()
    mock_bq.query.return_value = [
        {"run_id": "run-001", "row_count": 51203},
        {"run_id": "run-002", "row_count": 98000},  # historical
        ...
    ]
    agent = DetectionAgent(config=test_config, bq_client=mock_bq)
    result = agent.detect(pipeline_id="orders", run_id="run-001")
    assert result.anomaly_type == "ROW_COUNT_ANOMALY"
    assert result.severity == "P1"
```

For integration tests, use a dedicated BigQuery test dataset (`dpis_test`) that is separate from dev/staging/production.

---

## Failure injection tests

Each failure scenario in `failure_injection/` must have a corresponding end-to-end test in `tests/end_to_end/`. The test documents what was injected, what the expected response is, and validates the full loop:

```python
class TestRowDropScenario:
    """
    Simulates: 48% row count drop due to incomplete source file.

    Expected immune response:
      1. Detection: ROW_COUNT_ANOMALY, P1
      2. Diagnosis: UPSTREAM_PARTIAL_LOAD
      3. Risk: LOW
      4. Remediation: RETRY_SOURCE_EXTRACTION
      5. Verification: all checks pass
      6. Resolution: RESOLVED
    """

    def test_row_drop_full_recovery_cycle(self, test_pipeline, gcs_client):
        ...
```

---

## Data quality tests

Tests in `tests/data_quality/` use fixture datasets:

- `fixtures/valid_orders.csv` — clean data, all checks should pass
- `fixtures/null_spike_orders.csv` — 15% nulls in `customer_id`
- `fixtures/duplicate_orders.csv` — 8% duplicates
- `fixtures/schema_drift_orders.csv` — extra `phone` column added
- `fixtures/invalid_amounts_orders.csv` — negative `amount` values

Each fixture has a corresponding test that asserts the correct check result (PASS/FAIL/WARN) and the correct severity.

---

## CI/CD test gates

The CI pipeline enforces:

- All unit tests must pass (blocking)
- All agent tests must pass (blocking)
- All safety-critical tests must pass (blocking — separate job, failures are loud)
- Integration tests run against test GCP project (blocking for PRs to main)
- End-to-end tests run pre-deploy (blocking)

A test marked as safety-critical (via a pytest marker `@pytest.mark.safety_critical`) cannot be skipped in CI.

---

*Last updated: 2026-10*
