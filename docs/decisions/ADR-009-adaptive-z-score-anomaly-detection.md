# ADR-009: Adaptive Statistical Z-Score Anomaly Detection
## Status: Accepted
## Context:
Static volume bounds generate false alarms on weekends and seasonality cycles.
## Decision:
Calculate rolling 14-day mean and standard deviation to flag anomalies exceeding |z| > 2.0.
## Consequences:
Eliminates weekend alert fatigue and adapts to natural platform growth.
