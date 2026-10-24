# Service Level Objectives (SLOs) & Indicators (SLIs)
## 1. Pipeline Freshness SLI
- **SLI Formula**: `Timestamp_Diff(current_time, max(ingested_at), MINUTE)`
- **SLO Target**: 99.5% of hourly runs completed within 45 minutes of source landing.
## 2. Data Completeness SLI
- **SLI Formula**: `1.0 - (null_count / total_rows)`
- **SLO Target**: Required columns maintain >= 99.99% completeness.
## 3. Autonomous Healing Efficiency
- **Target**: >= 85% of P2/P3 operational incidents resolved without human on-call paging.
