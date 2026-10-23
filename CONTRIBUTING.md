# Contributing to Data Pipeline Immune System

Thank you for your interest in contributing to the **Data Pipeline Immune System**! This document provides guidelines for contributing code, tests, documentation, and failure injection scenarios.

By participating, you agree to uphold our [Code of Conduct](file:///Volumes/Work/daemons-lab/d.automation/Data%20Pipeline%20Immune%20System/CODE_OF_CONDUCT.md).

---

## 1. Quick Start & Development Setup

### 1.1. Prerequisites
- **Python**: 3.11 or newer
- **Google Cloud SDK**: `gcloud` CLI installed and authenticated
- **Terraform**: 1.5+ (if making infrastructure changes)
- **Docker**: For running containerized tests or Cloud Run emulation

### 1.2. Local Environment Setup
```bash
# 1. Clone the repository
git clone https://github.com/iamdpsingh/Data-Pipeline-Immune-System.git
cd Data-Pipeline-Immune-System

# 2. Create and activate a Python 3.11 virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# 3. Install development dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install -e .

# 4. Set local environment variables
export ENVIRONMENT=dev
export GCP_PROJECT=data-pipeline-immune-system
```

### 1.3. Running the Test Suite
```bash
# Run all unit, agent, and quality checks
pytest -v

# Run safety-critical tests specifically
pytest -m safety_critical -v

# Run formatting and lint checks
black --check .
ruff check .
bandit -r src/ agents/
```

---

## 2. Areas for Contribution

We actively welcome contributions in:
- **Detection & Diagnosis**: New deterministic rule signatures in `rules/detection_rules.yaml` or improved feature baselines.
- **Remediation Handlers**: New idempotent self-healing actions in [src/remediation/actions.py](file:///Volumes/Work/daemons-lab/d.automation/Data%20Pipeline%20Immune%20System/src/remediation/actions.py).
- **Chaos & Failure Scenarios**: New synthetic failure injections in `failure_injection/` (with documented reproduction and recovery steps).
- **Observability & Dashboards**: Enhanced metrics, BigQuery health-score queries, or UI dashboard visualizations in `dashboard/`.

---

## 3. Engineering Guidelines & Safety Rules

Before writing code, please review:
1. [.agents/AGENTS.md](file:///Volumes/Work/daemons-lab/d.automation/Data%20Pipeline%20Immune%20System/.agents/AGENTS.md) — Fundamental agent safety policies.
2. [.agents/rules/coding-standards.md](file:///Volumes/Work/daemons-lab/d.automation/Data%20Pipeline%20Immune%20System/.agents/rules/coding-standards.md) — Python naming, comments, and structure.
3. [docs/security/security-model.md](file:///Volumes/Work/daemons-lab/d.automation/Data%20Pipeline%20Immune%20System/docs/security/security-model.md) — Security boundaries and least-privilege architecture.

### Non-Negotiable Safety Rules:
- **Never weaken never-allow rules**: Changes to `rules/safety_rules.yaml` or [src/risk/never_allow.py](file:///Volumes/Work/daemons-lab/d.automation/Data%20Pipeline%20Immune%20System/src/risk/never_allow.py) require an Architecture Decision Record (ADR) and explicit review.
- **Rules before LLM**: Always implement deterministic failure handling prior to relying on generative AI models.
- **Idempotency**: All data transformation and remediation logic must be safely re-executable without side effects.

---

## 4. Git & Commit Conventions

We follow the **Conventional Commits** specification:

```
<type>(<scope>): <short description>
```

### Types:
- `feat`: A new user-facing feature or agent capability
- `fix`: A bug fix or incident handler correction
- `docs`: Documentation updates, runbooks, or ADRs
- `test`: Adding or refactoring unit, integration, or chaos tests
- `refactor`: Code changes that neither fix a bug nor add a feature
- `perf`: Performance optimizations (e.g. BigQuery query byte pruning)
- `chore`: Dependency updates, build configs, or CI adjustments

### Commit Granularity:
- Keep commits small, atomic, and self-contained.
- Ensure the commit author name and email match your verified GitHub identity (`dpsingh <dhruvpratapsingh30.official2.o@gmail.com>`).

---

## 5. Pull Request (PR) Workflow

1. Create a feature branch from `main`:
   ```bash
   git checkout -b feat/your-feature-name
   ```
2. Implement your changes with accompanying tests and documentation.
3. Verify that `pytest`, `black`, and `ruff` pass cleanly.
4. Push your branch to GitHub and open a Pull Request.
5. Provide a clear description including:
   - Problem statement / Motivation
   - Proposed changes
   - Test evidence (e.g. output from `pytest`)
   - Any safety impact
