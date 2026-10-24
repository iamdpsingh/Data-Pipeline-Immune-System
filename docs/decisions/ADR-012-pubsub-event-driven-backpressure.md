# ADR-012: Cloud Pub/Sub Event-Driven Ingestion & Backpressure Regulation

## Status: Accepted (In Production)

## Context
High-throughput streaming pipelines experience sudden burst traffic (e.g. mobile flash sales, upstream partner bulk syncs, or network reconnection dumps). If raw events are pushed directly to synchronous REST APIs or unbuffered database writers, two critical failure modes occur:
1. **Downstream API Exhaustion (HTTP 429 / 503)**: Webhook servers crash under TCP connection exhaustion and memory exhaustion.
2. **Cascading Failure Amplification**: When an ingestion stage fails, unbuffered upstream sources continue pushing data, exacerbating downtime and complicating point-in-time recovery.

The Immune System requires an asynchronous, fault-tolerant message buffer with built-in backpressure controls.

## Decision
We implement **Google Cloud Pub/Sub** as the central event-driven ingestion buffer and backpressure control plane:

1. **Decoupled Architecture**:
   - Ingestion producers publish events to Cloud Pub/Sub topics:
     - `dpis-events-<env>`: Raw event stream landing topic.
     - `dpis-incidents-<env>`: Anomaly detection and agent event topic.
     - `dpis-dead-letter-<env>`: Unparseable message dead-letter holding topic.

2. **Flow Control & Backpressure Regulation**:
   - Subscriber workers (FastAPI consumers and Cloud Run instances) configure strict Pub/Sub Flow Control settings:
     - `max_outstanding_messages = 1000`: Limits concurrent in-flight unacknowledged messages per worker.
     - `max_outstanding_bytes = 100 * 1024 * 1024` (100 MB buffer ceiling).
   - When downstream processing slows (e.g., during validation retries), workers pause message pulls, allowing Pub/Sub to safely buffer up to 7 days of message volume without dropping a single byte.

3. **Dead-Letter Topic & Exponential Retry**:
   - Subscriptions enforce a Dead-Letter Queue (DLQ) policy:
     - `max_delivery_attempts = 5`: Failed messages retry up to 5 times with exponential backoff (1s to 60s).
     - Messages that continue failing after 5 attempts are automatically routed to `dpis-dead-letter-<env>` for operator inspection and zero-loss offline analysis.

4. **Direct BigQuery Ingestion (BigQuery Subscription)**:
   - For high-volume append-only raw Bronze landing, we utilize Pub/Sub BigQuery Subscriptions to stream messages directly into `dpis_bronze_<env>` with zero intermediary compute servers.

## Consequences

### Positive
- **Elastic Burst Absorption**: Handles sudden 10x traffic spikes seamlessly without server degradation or dropped events.
- **Zero-Loss Resilience**: In the event of downstream service maintenance or network timeouts, messages remain safely queued in Pub/Sub.
- **Cost-Efficient Serverless Streaming**: Eliminates the operational and compute overhead of managing self-hosted Kafka clusters.

### Negative / Trade-Offs
- At-least-once delivery semantics: Pub/Sub guarantees at-least-once delivery; downstream Silver transformation stages must enforce idempotent deduplication based on `order_id` or message ID.
- Message order: Standard Pub/Sub topics do not guarantee global ordering without explicit ordering keys.
