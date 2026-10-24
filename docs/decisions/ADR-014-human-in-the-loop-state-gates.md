# ADR-014: Human-in-the-Loop Gates for High-Risk Remediation
## Status: Accepted
## Context:
Irreversible actions (breaking schema migrations, partition reloads) must not execute autonomously without review.
## Decision:
State machine halts at `AWAITING_APPROVAL` for P1 incidents and requires operator signature before execution.
## Consequences:
Combines autonomous speed for P2/P3 with strict safety governance for critical operations.
