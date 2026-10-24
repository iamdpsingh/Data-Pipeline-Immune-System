# ADR-006: Stateless Immune Controller on Google Cloud Run
## Status: Accepted
## Context:
Orchestration layer needs to respond dynamically to webhooks and autoscale without dedicated compute.
## Decision:
Deploy the state controller API on Google Cloud Run with `min_instances = 0` in dev to minimize cost.
## Consequences:
Zero idle compute expenses while scaling sub-second upon incident reception.
