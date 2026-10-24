# ==============================================================================
# Data Pipeline Immune System — Incident Memory Store (ADR-006)
# ==============================================================================
"""Stores and queries historical incident resolutions using similarity search.

In accordance with ADR-006:
Allows the Diagnosis Agent to recall past resolved incidents with similar
symptoms (e.g. partial API payloads, schema drifts), learning from historical
outcomes to improve recommendation precision.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class HistoricalIncident:
    incident_id: str
    pipeline_id: str
    incident_type: str
    symptoms: list[str]
    root_cause: str
    resolution_action: str
    outcome: str  # SUCCESS, FAILED
    resolved_at: datetime


class IncidentMemory:
    """Manages historical incident storage and contextual similarity matching."""

    def __init__(self, dataset: str = "dpis_dev", bq_client: Any | None = None):
        self.dataset = dataset
        self.bq_client = bq_client
        self._memory_cache: list[HistoricalIncident] = []

    def record_resolution(
        self,
        incident_id: str,
        pipeline_id: str,
        incident_type: str,
        symptoms: list[str],
        root_cause: str,
        resolution_action: str,
        outcome: str = "SUCCESS",
    ) -> HistoricalIncident:
        """Stores a resolved incident in memory."""
        record = HistoricalIncident(
            incident_id=incident_id,
            pipeline_id=pipeline_id,
            incident_type=incident_type,
            symptoms=symptoms,
            root_cause=root_cause,
            resolution_action=resolution_action,
            outcome=outcome,
            resolved_at=datetime.now(UTC),
        )
        self._memory_cache.append(record)
        logger.info(
            "[IncidentMemory] Recorded incident %s (type=%s, cause=%s, action=%s)",
            incident_id,
            incident_type,
            root_cause,
            resolution_action,
        )
        return record

    def find_similar(
        self,
        pipeline_id: str,
        incident_type: str,
        symptoms: list[str],
        limit: int = 3,
    ) -> list[HistoricalIncident]:
        """Finds most relevant historical incidents matching symptoms."""
        scored: list[tuple[float, HistoricalIncident]] = []

        query_tokens = set(
            [s.lower() for s in symptoms] + [pipeline_id.lower(), incident_type.lower()]
        )

        for item in self._memory_cache:
            score = 0.0
            if item.pipeline_id.lower() == pipeline_id.lower():
                score += 2.0
            if item.incident_type.lower() == incident_type.lower():
                score += 3.0

            item_tokens = set(
                [s.lower() for s in item.symptoms] + [item.root_cause.lower()]
            )
            overlap = query_tokens & item_tokens
            score += len(overlap) * 1.5

            if score > 0.0:
                scored.append((score, item))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:limit]]
