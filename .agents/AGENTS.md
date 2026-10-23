# Data Pipeline Immune System — Project Agent Rules

These rules apply to all agents (AI or human) working on this codebase. They exist to keep the project consistent, safe, and maintainable. Read this before touching any core component.

---

## Core principles

**Safety first.** This system makes autonomous decisions that affect production data. Any change that weakens safety guarantees — never-allow rules, risk classification, verification checks — needs explicit justification and review. Do not merge changes to `rules/safety_rules.yaml` or the never-allow enforcement code without a clear written reason.

**Rules before LLM.** The deterministic rules engine runs before the AI diagnosis layer. If you are adding a new known failure pattern, add it to the rules engine first. Don't rely on the LLM to handle something that can be handled deterministically.

**Auditability.** Every significant decision the system makes must be traceable. Incident detection, diagnosis, risk assessment, remediation, and verification all write structured records to BigQuery. If an autonomous action cannot be explained from the audit tables alone, the implementation is incomplete.

**Least privilege.** Agents have different permissions. Detection, Diagnosis, Risk, and Verification agents are read-only. Remediation Agent has limited write access to specific pre-approved action types only. Do not expand agent permissions without updating this document and the agent's permission spec.

---

## What you may change freely

- Data quality check thresholds in `config/` (dev, staging, production)
- Pipeline health score weights in `config/`
- Detection rule conditions in `rules/detection_rules.yaml`
- Remediation rule conditions in `rules/remediation_rules.yaml`
- Severity classifications in `rules/severity_rules.yaml`
- Dashboard layout and queries
- Test cases for any component

---

## What requires review before changing

- `rules/safety_rules.yaml` — any change to never-allow or critical-risk rules
- Never-allow enforcement code in `src/risk/` — this is the hard boundary that LLM output cannot override
- Agent permission definitions in `agents/`
- BigQuery DDL schemas in `sql/ddl/` — schema changes affect every layer
- Airflow DAG structure that changes the pipeline stage sequence
- Verification checks — weakening verification is the same as weakening safety

---

## Code quality expectations

**Do not add unnecessary abstraction.** If a simple function does the job, use it. Premature abstraction in a system this complex creates maintenance burden without adding value.

**Comment the why, not the what.** A comment that says `# check if row count is within range` adds nothing. A comment that says `# use z-score > 3 rather than percentage threshold because percentage thresholds break for pipelines with naturally high variance` is useful.

**Configuration belongs in config/, not in code.** Thresholds, SLAs, environment-specific values, and policy settings should never be hardcoded in application logic. If you find a hardcoded threshold, move it.

**Secrets never go in git.** Not in config files, not in `.env` files that get committed, not in test fixtures. GCP Secret Manager is the source of truth for secrets. See `docs/security/security-model.md` for the full setup.

---

## Testing expectations

Before considering any component complete, verify:
1. The implementation actually works
2. Tests cover the important behaviour (happy path + failure cases)
3. Documentation explains how and why it works

Do not write tests that only test the happy path for safety-critical components (risk classification, never-allow rules, verification checks). These need explicit failure case tests.

---

## Documentation expectations

**Write documentation alongside the implementation, not after.** If you build a new agent, document its responsibilities, inputs, outputs, permissions, and failure behaviour in `docs/architecture/agent-architecture.md` before the PR is merged.

**Update docs when behaviour changes.** If you change how the verification engine works, update `docs/flow.md` and any relevant runbook sections.

**ADRs for significant decisions.** If you make a decision that affects the overall architecture, add an entry to `docs/decisions/decision.md`. Not every implementation choice needs an ADR — only the ones that would confuse a developer who reads the code later without context.

---

## Failure injection rules

Failure injection scenarios are for testing only. The framework includes environment guards that prevent it from running in production without an explicit override flag. Do not remove these guards.

Every failure scenario must be documented in `failure_injection/README.md` with:
- What failure it simulates
- Which component it targets
- What the expected immune system response is
- How to verify the response was correct

---

## Incident memory

The Learning Agent writes to `incident_memory`. Do not manually edit this table to "fix" incorrect historical records. If a past incident was incorrectly classified, add a correction mechanism — don't silently patch the data. The audit trail matters.

---

## Environment separation

Development, staging, and production behave differently. Key differences are documented in `docs/operations/runbook.md`. The short version:

- **Dev:** failure injection enabled, lower thresholds, Cloud Run min instances = 0
- **Staging:** failure injection disabled, production-like thresholds, real GCP services
- **Production:** failure injection disabled, strict thresholds, min instances = 1 for critical services, all never-allow rules enforced

Configuration for each environment lives in `config/dev.yaml`, `config/staging.yaml`, `config/production.yaml`. The application reads the correct file based on the `ENVIRONMENT` environment variable.

---

## CI/CD expectations

Every PR must pass:
- `ruff` linting
- `black` formatting check
- All unit tests
- All integration tests (against BigQuery emulator or test project)
- Security scan (`bandit` or equivalent)
- Terraform validation (if infrastructure changes are included)

The pipeline blocks merges on failure. Do not bypass CI checks.
