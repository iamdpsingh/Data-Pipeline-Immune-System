# ADR-012: Pub/Sub Event-Driven Ingestion with Backpressure
## Status: Accepted
## Context:
Sudden bursts of upstream ingestion payloads can overwhelm the agent diagnosis engine.
## Decision:
Buffer incoming anomaly webhooks in Google Cloud Pub/Sub with dead-letter queue backpressure.
## Consequences:
Guarantees at-least-once processing and protects the API controller from OOM crashes.
