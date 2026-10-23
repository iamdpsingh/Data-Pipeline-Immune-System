# Development Guidelines — Data Pipeline Immune System

Comprehensive engineering guidelines for developers, data engineers, and AI agents contributing to the **Data Pipeline Immune System**.

---

## 1. Core Development Philosophy

1. **Safety is Inviolable**:
   Autonomous actions operate on production data pipelines. Any contribution that weakens never-allow invariants, degrades risk classification accuracy, or bypasses verification gates will be rejected immediately.
2. **Rules First, LLM Second**:
   Deterministic problems demand deterministic solutions. If a failure pattern can be resolved with a rules-based signature or regex matching, implement it in [rules/](file:///Volumes/Work/daemons-lab/d.automation/Data%20Pipeline%20Immune%20System/rules/). Reserve generative AI reasoning solely for novel, unclassified anomalies.
3. **Idempotency Everywhere**:
   Every data transformation, PySpark backfill, and remediation handler must be safe to execute multiple times against the same partition without side effects or record duplication.
4. **Auditability by Construction**:
   No agent decision, rule evaluation, or remediation action may execute without writing a structured audit log entry to the `dpis_audit` dataset.

---

## 2. Environment & Tooling Setup

- **Python Runtime**: Python 3.11+.
- **Active GCP Project**: `data-pipeline-immune-system`.
- **Package Management**: Dependencies are pinned in [pyproject.toml](file:///Volumes/Work/daemons-lab/d.automation/Data%20Pipeline%20Immune%20System/pyproject.toml) and [requirements.txt](file:///Volumes/Work/daemons-lab/d.automation/Data%20Pipeline%20Immune%20System/requirements.txt).
- **Code Style & Linters**:
  - Code formatter: `black --line-length 88`
  - Linter: `ruff check .`
  - Security scanner: `bandit -r src/ agents/`
  - Test runner: `pytest -v`

---

## 3. Git Workflow & Commit Discipline

### 3.1. Branching Model
- `main`: Protected production branch. All merges must pass CI checks.
- `feat/<feature-name>`: New pipeline stages, agent capabilities, or dashboard features.
- `fix/<bug-description>`: Bug fixes and regression repairs.
- `docs/<topic>`: Documentation enhancements and Architecture Decision Records (ADRs).
- `test/<suite>`: Test harness additions, failure injection scenarios, and benchmarks.

### 3.2. Commit Standards
- **Atomic Commits**: Keep commits focused on a single logical change. Split broad refactors into clean, reviewable units.
- **Conventional Commits**: Format commit messages using standard prefixes:
  - `feat(detection)`: Add rolling z-score baseline detector
  - `fix(remediation)`: Prevent duplicate execution of Airflow backfill task
  - `docs(adr)`: Document ADR-003 remediation policy
  - `test(risk)`: Add unit test asserting never-allow block on DROP TABLE
- **Author Identity**: Ensure commits match the repository owner identity (`dpsingh <dhruvpratapsingh30.official2.o@gmail.com>`) for proper GitHub attribution.

---

## 4. Code Quality & Architecture Rules

1. **Explicit Type Hints**: All function signatures in `src/` and `agents/` must include explicit type annotations.
2. **Configuration Separation**:
   - Never hardcode dataset names, bucket URIs, thresholds, or API endpoints in Python code.
   - All settings must be sourced from [config/dev.yaml](file:///Volumes/Work/daemons-lab/d.automation/Data%20Pipeline%20Immune%20System/config/dev.yaml), [config/staging.yaml](file:///Volumes/Work/daemons-lab/d.automation/Data%20Pipeline%20Immune%20System/config/staging.yaml), or [config/production.yaml](file:///Volumes/Work/daemons-lab/d.automation/Data%20Pipeline%20Immune%20System/config/production.yaml).
3. **Least Privilege Enforcement**:
   - Detection, Diagnosis, Risk, and Verification agents must remain strictly read-only.
   - Remediation Agent write permissions are restricted exclusively to calling pre-registered handlers in [src/remediation/actions.py](file:///Volumes/Work/daemons-lab/d.automation/Data%20Pipeline%20Immune%20System/src/remediation/actions.py).
4. **Documentation in Lockstep**:
   - Any architectural modification must be accompanied by an update in [docs/architecture/](file:///Volumes/Work/daemons-lab/d.automation/Data%20Pipeline%20Immune%20System/docs/architecture/) or a new ADR in [docs/decisions/](file:///Volumes/Work/daemons-lab/d.automation/Data%20Pipeline%20Immune%20System/docs/decisions/).

---

## 5. Testing & Verification Checklist

Before opening a pull request or merging code:
- [ ] Run `ruff check .` with zero errors.
- [ ] Run `black --check .` with zero formatting differences.
- [ ] Run `pytest` — ensure 100% of unit tests pass, especially `@pytest.mark.safety_critical`.
- [ ] Run `bandit -r src/ agents/` to verify zero high-severity vulnerabilities.
- [ ] If adding a failure scenario, document it in [failure_injection/README.md](file:///Volumes/Work/daemons-lab/d.automation/Data%20Pipeline%20Immune%20System/failure_injection/README.md) with reproduction steps and expected immune system responses.
