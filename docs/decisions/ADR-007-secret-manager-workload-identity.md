# ADR-007: Secret Isolation via Secret Manager & Workload Identity
## Status: Accepted
## Context:
Zero secrets in source repositories or plaintext disk files.
## Decision:
All production API tokens, database keys, and webhook secrets reside in GCP Secret Manager.
## Consequences:
IAM service accounts access secrets dynamically with zero git leakage risk.
