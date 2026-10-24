# ADR-009: Adaptive Baseline & Statistical Anomaly Detection Engine

## Status: Accepted (In Production)

## Context
Traditional data pipeline monitoring relies heavily on hardcoded static thresholds (e.g. "alert if row count drops by more than 20%"). In production enterprise data platforms, static rules suffer from two catastrophic failure modes:
1. **False Positives (Alert Fatigue)**: Weekly seasonality, weekend volume drops, or regional holidays trigger false alarms, desensitizing engineering teams to real system failures.
2. **False Negatives (Silent Data Corruption)**: A slow, creeping 8% loss of transaction data over consecutive days evades a 20% static threshold entirely, silently corrupting analytical models.

Pipelines with naturally high volume variance require dynamic baselines that learn normal operating distributions from recent telemetry.

## Decision
We implement an **Adaptive Statistical Baseline Engine** (`src/detection/baseline.py` and `src/detection/statistics.py`):

1. **Dual-Method Parametric & Non-Parametric Modeling**:
   - **Adaptive Z-Score (Parametric)**: For metrics exhibiting normal distribution characteristics over a 14-day rolling window:
     $$z = \frac{x - \mu}{\sigma}$$
     An anomaly is flagged when $|z| > \text{threshold}$ (default: $z > 3.0$, representing a $99.7\%$ confidence boundary).
   - **Interquartile Range (IQR, Non-Parametric)**: For skewed or multimodal volume metrics:
     $$\text{IQR} = Q_3 - Q_1$$
     Bounds: $[Q_1 - 1.5 \cdot \text{IQR}, Q_3 + 1.5 \cdot \text{IQR}]$. Outliers outside these bounds trigger investigation.

2. **Cold-Start & Sample Guardrails**:
   - Statistical baselines require a minimum number of historical successful runs (`min_baseline_runs = 7`, configurable).
   - If fewer than 7 historical runs exist (e.g., during pipeline launch), the engine automatically falls back to safe static percentage boundaries (`[0.70 \cdot \text{expected}, 1.30 \cdot \text{expected}]`).
   - If historical standard deviation is near zero ($\sigma \approx 0.0$), the engine prevents division-by-zero errors by enforcing an absolute minimum variance floor.

3. **Autonomous Immune Integration**:
   - The `DetectionAgent` continuously computes moving baselines for row count volume, byte throughput, and task execution durations.
   - Significant negative deviations ($z < -3.0$) are classified as `VOLUME_DROP_ANOMALY` or `UPSTREAM_INGESTION_DELAY`, triggering partition holds to protect downstream Gold marts.

## Consequences

### Positive
- **Reduced False Alarms**: Eliminates alert fatigue by accounting for natural volume fluctuations and weekly patterns.
- **High Sensitivity to Real Failures**: Accurately detects sudden upstream drop-offs (e.g., vendor ingestion failures) even when absolute numbers appear non-zero.
- **Self-Calibrating**: As business scale grows from thousands to millions of records, the baseline adapts automatically without manual threshold updates.

### Negative / Trade-Offs
- Rolling baseline computation requires executing an aggregation query over historical pipeline telemetry in BigQuery.
- Sudden, legitimate business spikes (e.g., Black Friday traffic) can trigger temporary P2 warnings unless marked as planned promotional events in the controller configuration.
