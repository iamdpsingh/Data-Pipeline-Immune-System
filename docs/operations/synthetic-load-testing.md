# High-Throughput Synthetic Load Testing & 10M/Day Streaming Playbook

## 1. Overview
The Data Pipeline Immune System includes high-performance synthetic load generation tooling designed to stress-test data ingestion pipelines, quality validation assertion engines, and autonomous multi-agent controllers up to enterprise scale (**10,000,000 records daily** / ~115 to 125 records/second nominal rate).

---

## 2. Load Generation Architecture (`scripts/simulate_24h_10m_stream.py`)
To prevent memory bloat and out-of-memory errors on developer machines or worker nodes, the load generation engine utilizes:
1. **Streaming Generators**: Records are yielded as lightweight dictionaries without buffering millions of objects in RAM.
2. **Micro-Batch Execution**: Data is evaluated in configurable chunks (5,000 to 50,000 records per micro-batch).
3. **Deterministic Anomaly Injection**: Controllable corruption parameters inject realistic failure signatures:
   - Negative order pricing (`amount = -45.00`)
   - Null foreign keys (`customer_id = null`)
   - Upstream rate drops and timeouts
   - Additive non-breaking schema evolution

---

## 3. Execution Commands & Benchmark Modes

### Mode 1: Fast-Forward Throughput Benchmark (Verify System Speed)
Tests processing speed and memory limits across 50,000 to 1,000,000 records in seconds:
```bash
python3 scripts/simulate_24h_10m_stream.py \
    --mode=benchmark \
    --benchmark-records=50000 \
    --batch-size=10000
```
- **Expected Throughput**: >300,000 records/sec on standard multicore developer machines.
- **Expected Outcome**: Clean records promoted to Silver; corrupted records safely routed to Dead-Letter Quarantine.

### Mode 2: Continuous 24-Hour Enterprise Streaming Simulation (~10M Records)
Simulates a real-time 24-hour continuous production stream at ~116 records/second:
```bash
python3 scripts/simulate_24h_10m_stream.py \
    --mode=realtime \
    --target-daily-volume=10000000
```
- **Behavior**: Emits continuous micro-batches every 4.3 seconds, updates terminal metrics, and calculates real-time Composite Health Scores.

### Mode 3: Rapid 24-Hour Equivalent Batch Test (9.8M Records)
Executes a high-speed complete daily equivalent run (e.g. 9.8M records) in minutes to validate BigQuery and GCS write throughput:
```bash
python3 scripts/simulate_24h_10m_stream.py \
    --mode=batch \
    --target-daily-volume=9800000 \
    --batch-size=50000
```

---

## 4. Post-Load Telemetry Validation Checklist
After executing a load test:
- [ ] Verify that total records processed = clean records + quarantined records.
- [ ] Query Silver table to verify 0 records with `amount <= 0` or `customer_id IS NULL`.
- [ ] Confirm Composite Health Score calculated by `HealthScoreCalculator` is >= 95.0.
- [ ] Generate daily executive report: `python3 scripts/send_daily_report.py`.
