# Service Level Objectives (SLO) & Service Level Indicators (SLI)

## 1. Overview
This specification codifies the formal Service Level Indicators (SLIs), Service Level Objectives (SLOs), and Error Budget policies governing the Data Pipeline Immune System across production workloads.

---

## 2. Core Operational SLI / SLO Catalog

### SLO 1: Pipeline Execution Availability
- **Indicator (SLI)**: The ratio of successful or autonomously healed pipeline runs divided by total scheduled pipeline runs:
  $$\text{SLI}_{\text{avail}} = \frac{\text{Successful Runs} + \text{Auto-Remediated Runs}}{\text{Total Scheduled Runs}}$$
- **Objective (SLO)**: **>= 99.5%** over any rolling 30-day window.
- **Critical Threshold**: Alert when 24-hour success rate drops below 98.0%.

### SLO 2: Data Freshness (Delivery Latency)
- **Indicator (SLI)**: The elapsed time between event ingestion into GCS Bronze landing and completion of conformed Silver partition availability:
  $$\text{SLI}_{\text{freshness}} = T_{\text{Silver Available}} - T_{\text{GCS Event Ingested}}$$
- **Objective (SLO)**: **P95 < 15 minutes**; **P99 < 30 minutes**.
- **Critical Threshold**: Alert when partition latency exceeds 60 minutes.

### SLO 3: Data Quality & Cleanness Guarantee
- **Indicator (SLI)**: The percentage of valid, non-corrupted records in the conformed Silver Lakehouse tier:
  $$\text{SLI}_{\text{quality}} = \frac{\text{Records Passing Quality Assertions in Silver}}{\text{Total Records in Silver}} \times 100\%$$
- **Objective (SLO)**: **100.0%** (Inviolable invariant: 0 corrupted records permitted in Silver; corrupted records must be routed to DLQ).

### SLO 4: Autonomous Mean Time to Repair (MTTR)
- **Indicator (SLI)**: The average elapsed wall time from anomaly detection to verified successful remediation for autonomous P2/P3 incidents:
  $$\text{SLI}_{\text{MTTR}} = \frac{1}{N} \sum_{i=1}^N (T_{\text{Verified Healed}} - T_{\text{Anomaly Detected}})$$
- **Objective (SLO)**: **Average MTTR < 1.5 minutes**.

---

## 3. Error Budget & Burn Rate Alerting Policy

| Burn Rate Multiple | 30-Day Budget Consumed | Action Triggered | Notification Channel |
| :--- | :--- | :--- | :--- |
| **1x Normal** | ~3.3% per day | Nominal tracking | Daily Executive Report |
| **2x Warning** | ~6.7% per day | System status marked `DEGRADED` | Telegram Operations Channel |
| **5x Critical** | ~16.7% per day | Freeze non-critical schema migrations | High-Priority Mobile Page |
| **14.4x Emergency** | 100% in 2 days | Executive escalation; automated partition hold | Emergency On-Call Escalation |
