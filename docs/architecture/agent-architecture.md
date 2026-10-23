# Agent Architecture — Data Pipeline Immune System

This document covers how the immune system agents are designed, how they communicate, and what each one is responsible for. For the technical specifications (inputs, outputs, permissions), see [`.agents/rules/agent-rules.md`](../../.agents/rules/agent-rules.md).

---

## Why specialised agents

The first instinct when building an AI-powered reliability system is to create one general agent that does everything. This is a bad idea.

A single general agent with write access has a wide blast radius. One bad LLM response could delete data, trigger cascading reruns, or silently corrupt the production table. There's no clean way to audit what it did or why.

Specialised agents with different permission levels solve this:
- Most agents are read-only. They can't cause damage.
- The Remediation Agent has limited write access to a pre-defined set of actions.
- The AI model never gets to choose what SQL to run — it only gets to pick from an approved action library.
- Each agent's decision is logged independently, so the full decision trail is auditable.

---

## Agent overview

```
                  ImmuneSystemController
                          │
          ┌───────────────┼───────────────┐
          ↓               ↓               ↓
   Detection Agent  Diagnosis Agent   Risk Agent
   (read-only)      (read-only)       (read-only)
                          │
                    Remediation Agent
                    (limited write)
                          │
                   Verification Agent
                    (read-only)
                          │
                    Learning Agent
                    (writes to memory only)
```

The controller is the only component that knows the full incident state. Agents receive specific inputs, produce specific outputs, and don't communicate with each other directly.

---

## Controller

The `ImmuneSystemController` orchestrates the entire incident lifecycle. It:

1. Receives a pipeline run completion event
2. Calls the Detection Agent
3. If an anomaly is found, creates an incident
4. Calls the Diagnosis Agent
5. Calls the Risk Agent
6. Based on risk assessment: auto-proceeds or waits for human approval
7. Calls the Remediation Agent (after approval is granted)
8. Calls the Verification Agent
9. Marks the incident RESOLVED or ESCALATED
10. Calls the Learning Agent

The controller writes every state transition to BigQuery before proceeding to the next step. If it restarts mid-incident, it reads the current state from BigQuery and continues from where it left off.

---

## Rule engine (first pass)

Before any LLM is involved, the rule engine runs on the incident:

```
Incident arrives
      ↓
Rule engine checks detection_rules.yaml
      ↓
Known pattern? → Deterministic classification → skip AI diagnosis
Unknown pattern? → Send to Diagnosis Agent
```

This handles the majority of common failures (transient task failures, missing partitions, API timeouts) without any LLM call. The AI adds value for novel or ambiguous cases.

---

## Agent communication pattern

Agents receive typed input objects and return typed output objects. The controller handles all the BigQuery writes — agents don't write to incident tables directly (except the Learning Agent, which writes to `incident_memory`).

Example message flow:

```python
# Controller calls Detection Agent
detection_input = DetectionInput(pipeline_id="orders", run_id="run-8291")
detection_result = detection_agent.detect(detection_input)

# If anomaly found, controller creates incident and calls Diagnosis Agent
diagnosis_input = DiagnosisInput(
    incident_id=incident.id,
    detection_result=detection_result
)
diagnosis_result = diagnosis_agent.diagnose(diagnosis_input)

# Controller calls Risk Agent
risk_input = RiskInput(
    incident_id=incident.id,
    diagnosis_result=diagnosis_result
)
risk_assessment = risk_agent.assess(risk_input)
```

Every input/output is logged to `agent_decisions` with the incident ID, agent name, input summary, output summary, confidence, and timestamp.

---

## LLM integration

The Diagnosis Agent uses an LLM for cases where the rule engine returns UNKNOWN. The LLM is given:

- The anomaly type and metrics
- Pipeline run history (last N runs)
- Task-level results
- Quality check results
- Similar historical incidents from memory
- The available root cause types

The LLM is NOT given:
- Raw data records
- PII fields
- Credentials or configuration values
- Arbitrary write access to anything

The LLM produces a structured JSON response:

```json
{
  "root_cause": "UPSTREAM_PARTIAL_LOAD",
  "confidence": 0.91,
  "evidence": [
    "source row count dropped from 98,213 to 51,203",
    "Airflow task completed successfully",
    "Spark job completed successfully",
    "schema unchanged from previous run"
  ],
  "recommended_action": "RETRY_SOURCE_EXTRACTION"
}
```

The controller validates this response before acting on it. If `recommended_action` maps to a never-allow rule, the action is blocked regardless of what the LLM returned.

---

## Confidence model in practice

High confidence doesn't mean auto-approve. The confidence score feeds into the risk assessment but never overrides safety rules:

| Scenario | Confidence | Result |
|---|---|---|
| Transient failure, rule match | N/A (deterministic) | Auto-remediate |
| Partial load, high confidence (0.91) | HIGH | Auto-remediate (LOW risk action) |
| Unknown failure, high confidence (0.95) | HIGH | Escalate (UNKNOWN root cause policy) |
| Schema deletion, any confidence | ANY | Block unconditionally |
| Low confidence (< 0.50) | LOW | Escalate to human |

---

## Human-in-the-loop

For HIGH risk incidents or when auto-remediation is not approved:

1. Controller writes an approval request to `approval_requests` table
2. Dashboard shows the pending request with full incident context
3. Human reviews: diagnosis, confidence, proposed action, risk level, evidence
4. Human clicks APPROVE or REJECT
5. Dashboard writes decision back to BigQuery
6. Controller polls `approval_requests` for the decision
7. If APPROVE: controller calls Remediation Agent
8. If REJECT: incident marked ESCALATED, human handles manually

The approval interface shows:

```
Incident INC-2026-042

Pipeline: payments_pipeline
Detected: Row count anomaly (-46%)

Root Cause: Upstream partial extraction
Confidence: 91%

Evidence:
  - Source row count: 643,241 (expected ~1,200,000)
  - Airflow task: SUCCESS
  - Spark job: SUCCESS
  - Schema: unchanged

Proposed Action: RETRY_SOURCE_EXTRACTION
Risk Level: LOW

[ APPROVE ]   [ REJECT ]
```

---

## Agent failure handling

If an agent call fails (network error, timeout, unexpected exception):

1. Controller logs the failure with full context
2. Incident transitions to ESCALATED
3. Alert is sent (email/Slack/Cloud Monitoring)
4. Incident is not silently dropped

The system is designed to fail loudly rather than silently assume everything is fine.

---

*Last updated: 2026-10*
