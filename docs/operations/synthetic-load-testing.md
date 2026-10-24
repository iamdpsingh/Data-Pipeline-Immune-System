# Synthetic Load & Stress Testing Guide
## 1. High-Throughput Burst Generation
To test agent state machine performance under load:
```bash
python3 scripts/simulate_chaos_scenarios.py --burst-rate 5000 --duration-seconds 60
```
## 2. Evaluation Metrics
- Cloud Run response latency: P95 < 250ms
- Pub/Sub buffer queue depth: zero dropped messages
- BigQuery streaming insert error rate: 0.00%
