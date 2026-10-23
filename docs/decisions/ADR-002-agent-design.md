# ADR-002: Specialized Decoupled Agents vs. Monolithic LLM Agent

- **Status**: Accepted
- **Deciders**: Architecture Team, Data Platform Lead
- **Date**: 2026-10
- **Technical Context**: Agent Architecture & Safety Boundaries

---

## 1. Context and Problem Statement

The platform must detect anomalies, determine root causes, evaluate operational risk, execute safe remediation, verify repair correctness, and learn from past outcomes.

The architectural question was:
Should this be implemented as a **single monolithic LLM agent** with tool-use (e.g. an agent prompt with access to BigQuery, bash execution, and Airflow), or as **specialized, decoupled agents** with distinct permission boundaries?

---

## 2. Decision Outcome

**Chosen option**: Specialized decoupled agents orchestrated by a centralized state controller ([ImmuneSystemController](file:///Volumes/Work/daemons-lab/d.automation/Data%20Pipeline%20Immune%20System/src/controller/controller.py)).

### Specialized Agent Responsibilities:
1. **Detection Agent** — Read-only; evaluates statistical z-scores and deterministic threshold violations.
2. **Diagnosis Agent** — Read-only; evaluates deterministic error signatures first, then queries historical memory and invokes structured LLM reasoning.
3. **Risk Agent** — Read-only; enforces never-allow invariants and assigns risk tiers (LOW, MEDIUM, HIGH, NEVER_ALLOW).
4. **Remediation Agent** — Limited write; strictly constrained to executing pre-approved, idempotent handlers from the action library.
5. **Verification Agent** — Read-only; asserts post-repair health before incident closure.
6. **Learning Agent** — Write restricted to `incident_memory` table only.

---

## 3. Justification & Comparative Rationale

### 1. Blast Radius Minimization:
- A monolithic agent with write permissions has an unbounded blast radius. An LLM prompt injection or hallucination could inadvertently trigger `DROP TABLE` or mutate production rows.
- In our decoupled architecture, only the **Remediation Agent** has any write capability, and that capability is strictly limited to pre-coded action functions in [src/remediation/actions.py](file:///Volumes/Work/daemons-lab/d.automation/Data%20Pipeline%20Immune%20System/src/remediation/actions.py). It cannot run arbitrary SQL.

### 2. Isolation of Concerns & Deterministic Fallbacks:
- Specialized agents allow testing each stage independently. We can test risk classification or baseline calculations with 100% deterministic unit tests without mocking complex LLM conversations.
- Prompt injection cannot bypass code-level checks because prompt-level instructions are not the safety enforcement layer.

### 3. Cost & Latency Optimization:
- The Detection, Risk, and Verification agents run purely in Python code in milliseconds with zero LLM API costs. LLM calls are confined exclusively to the Diagnosis Agent for novel or unclassified failure patterns.

---

## 4. Consequences & Trade-offs

### Positive Consequences:
- High auditability and verifiable safety boundaries.
- Drastic reduction in token consumption and inference latency.
- Unit and integration tests can assert compliance deterministically.

### Negative Consequences / Limitations:
- The central controller must manage state transitions and message passing across six individual agent boundaries.
