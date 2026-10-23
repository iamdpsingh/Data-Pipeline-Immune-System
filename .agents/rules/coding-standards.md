# Coding Standards — Data Pipeline Immune System

Practical coding conventions for this project. These aren't arbitrary style rules — each one has a reason behind it specific to this codebase.

---

## Python conventions

**Python version:** 3.11+. Use modern type hints throughout (`str | None` instead of `Optional[str]`).

**Formatting:** `black` with default settings. Line length 88.

**Linting:** `ruff`. Config in `pyproject.toml`. Do not suppress warnings without a comment explaining why.

**Imports:** Standard library → third-party → internal. Use absolute imports for internal modules.

**Type hints:** Required on all public functions and class methods. Internal helper functions should have them too unless it genuinely makes the code harder to read.

---

## Naming conventions

| What | Convention | Example |
|---|---|---|
| Modules | snake_case | `detection_agent.py` |
| Classes | PascalCase | `DetectionAgent` |
| Functions | snake_case | `detect_anomaly()` |
| Constants | UPPER_SNAKE_CASE | `MAX_RETRY_COUNT` |
| Config keys | snake_case | `null_threshold` |
| BigQuery tables | snake_case | `pipeline_runs` |
| BigQuery columns | snake_case | `detected_at` |
| Incident IDs | INC-YYYY-NNN | `INC-2026-001` |
| Run IDs | run-{uuid4} | `run-8291ab...` |

---

## Comments

Write comments that explain **why**, not what.

Bad:
```python
# check if row count is valid
if actual_rows < expected_rows * threshold:
```

Good:
```python
# Using relative threshold rather than absolute because pipelines
# with natural daily volume variation would generate false positives
# with a fixed row count floor. Threshold is per-pipeline in config.
if actual_rows < expected_rows * threshold:
```

Mandatory comment locations:
- All safety checks in `src/risk/`
- Never-allow rule enforcement
- Any place where an agent's output is overridden by application logic
- Non-obvious SQL query logic
- Adaptive baseline calculation
- Confidence score weighting decisions

---

## Agent implementation pattern

Every agent follows the same structure:

```python
class DetectionAgent:
    """
    Identifies abnormal pipeline behaviour by comparing current run metrics
    against historical baselines and configured thresholds.

    Permissions: READ ONLY
    Inputs: pipeline_id, run_id
    Outputs: list of anomalies with severity and confidence

    This agent never writes to production tables. It only reads from BigQuery
    and writes detection results to the agent_decisions table via the controller.
    """

    def __init__(self, config: AgentConfig, bq_client: BigQueryClient):
        self.config = config
        self.bq = bq_client

    def detect(self, pipeline_id: str, run_id: str) -> DetectionResult:
        ...
```

The docstring on the class must always state the permissions, inputs, and outputs. This is not optional — it's how we enforce the trust model in documentation.

---

## Configuration handling

Never hardcode thresholds or environment-specific values in application code.

Wrong:
```python
if null_percentage > 0.05:
    raise AnomalyDetected("null spike")
```

Right:
```python
threshold = self.config.quality.null_threshold
if null_percentage > threshold:
    raise AnomalyDetected(f"null spike: {null_percentage:.2%} > {threshold:.2%}")
```

The config object is loaded from the environment-specific YAML (`dev.yaml`, `staging.yaml`, `production.yaml`) at startup. See `src/config/` for the loader.

---

## Error handling

For agent operations, prefer explicit error types over generic exceptions:

```python
class DiagnosisError(Exception): ...
class InsufficientDataError(DiagnosisError): ...
class IncidentNotFoundError(DiagnosisError): ...
```

Always log the original exception context when catching and re-raising:

```python
try:
    result = self.bq.query(sql)
except google.cloud.exceptions.GoogleAPIError as e:
    logger.error("BigQuery query failed for incident %s: %s", incident_id, e)
    raise DiagnosisError(f"Failed to fetch run metrics: {e}") from e
```

The `from e` is important — it preserves the original stack trace.

---

## BigQuery query hygiene

- Parameterise all queries. Never use f-strings to build SQL with user-supplied values.
- Always partition-filter queries that run against partitioned tables (use `_PARTITIONDATE` or `run_date` filter).
- For queries that could return large results, use `LIMIT` and log a warning if the limit is reached.
- Store complex multi-stage queries as named SQL files in `sql/` rather than inline Python strings.

---

## Structured logging

Use structured logging everywhere. The log format should be consistent so Cloud Logging can parse and query it.

```python
import logging
import json

logger = logging.getLogger(__name__)

# Good — structured
logger.info(
    "Anomaly detected",
    extra={
        "incident_id": incident_id,
        "pipeline": pipeline_id,
        "anomaly_type": anomaly.type,
        "severity": anomaly.severity,
        "confidence": anomaly.confidence,
    }
)

# Bad — unstructured string
logger.info(f"Anomaly {anomaly.type} detected in {pipeline_id}")
```

---

## Immutability for agent messages

Agent input/output messages should be dataclasses or Pydantic models, not plain dicts. This makes the contract explicit and allows validation.

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class DetectionResult:
    incident_id: str
    anomaly_type: str
    severity: str
    confidence: float
    evidence: list[str]
    pipeline_id: str
    run_id: str
    detected_at: str
```

Frozen dataclasses prevent accidental mutation of agent outputs as they pass through the controller.

---

## Testing

Unit tests live in `tests/unit/`. Integration tests in `tests/integration/`. Agent-specific tests in `tests/agents/`.

Test naming: `test_{function_name}_{scenario}`. Example: `test_detect_row_count_anomaly_below_baseline`.

For safety-critical logic (never-allow rules, risk classification), write explicit tests for the failure case — not just the happy path:

```python
def test_never_allow_blocks_schema_deletion_regardless_of_confidence():
    """
    Even with 0.99 confidence, a schema deletion action must be blocked.
    This is the core safety guarantee — AI confidence cannot override it.
    """
    diagnosis = Diagnosis(
        root_cause="SCHEMA_DELETION",
        recommended_action="DELETE_PRODUCTION_SCHEMA",
        confidence=0.99
    )
    risk_agent = RiskAgent(config=test_config)
    result = risk_agent.assess(diagnosis)
    assert result.risk_level == RiskLevel.NEVER_ALLOW
    assert result.auto_remediable is False
```

---

*Last updated: 2026-10*
