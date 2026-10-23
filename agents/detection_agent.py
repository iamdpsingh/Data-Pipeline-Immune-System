"""
Detection Agent

Identifies abnormal pipeline behaviour by comparing current run metrics
against historical baselines and configured thresholds.

Permissions: READ ONLY
Inputs: pipeline_id, run_id
Outputs: DetectionResult with anomaly type, severity, confidence, evidence

The agent never writes to production tables. It only reads from BigQuery
and returns a result to the controller, which handles all state writes.

Detection runs two modes:
  1. Post-run sweep — triggered after a pipeline run completes
  2. Continuous freshness/SLA monitoring — runs on a schedule independent of runs

For the anomaly detection methodology, see docs/architecture/agent-architecture.md.
For the rules engine that runs before AI diagnosis, see rules/detection_rules.yaml.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime

from src.config.loader import AgentConfig
from src.observability.bigquery_client import BigQueryClient
from src.detection.baseline import AdaptiveBaseline
from src.detection.schema_comparator import SchemaComparator
from src.detection.statistics import StatisticalDetector

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DetectionInput:
    pipeline_id: str
    run_id: str


@dataclass(frozen=True)
class DetectionResult:
    incident_id: str | None  # None if no anomaly detected
    anomaly_type: str | None
    severity: str | None
    confidence: float
    evidence: list[str]
    pipeline_id: str
    run_id: str
    detected_at: str
    is_anomaly: bool


class DetectionAgent:
    """
    Identifies abnormal pipeline behaviour.

    Permissions: READ ONLY
    """

    def __init__(self, config: AgentConfig, bq_client: BigQueryClient):
        self.config = config
        self.bq = bq_client
        self.baseline = AdaptiveBaseline(bq_client, config.detection)
        self.schema_comparator = SchemaComparator(bq_client)
        self.statistical_detector = StatisticalDetector(config.detection)

    def detect(self, input: DetectionInput) -> DetectionResult:
        """
        Run all detection checks for a completed pipeline run.
        Returns a DetectionResult. If is_anomaly is False, no incident should be created.
        """
        raise NotImplementedError("Detection agent implementation pending — Phase 5")
