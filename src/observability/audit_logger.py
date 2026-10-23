# ==============================================================================
# Data Pipeline Immune System — Structured Audit & Telemetry Logger (ADR-010)
# ==============================================================================
"""Structured audit logger writing immune lifecycle events to BigQuery.

In accordance with ADR-010:
Stores pipeline runs, task outcomes, data quality results, incident transitions,
and autonomous remediation actions in BigQuery for full auditability and trace.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AuditEvent:
    event_id: str
    incident_id: Optional[str]
    pipeline_id: str
    run_id: str
    agent_name: str
    action_type: str
    details: Dict[str, Any]
    status: str
    timestamp: datetime


class AuditLogger:
    """Manages audit event serialization and persistent recording."""

    def __init__(self, dataset: str = "dpis_dev", bq_client: Optional[Any] = None):
        self.dataset = dataset
        self.bq_client = bq_client
        self._local_buffer: List[AuditEvent] = []

    def record_event(
        self,
        pipeline_id: str,
        run_id: str,
        agent_name: str,
        action_type: str,
        details: Dict[str, Any],
        incident_id: Optional[str] = None,
        status: str = "SUCCESS",
    ) -> AuditEvent:
        """Records an audit event to the audit trail."""
        event = AuditEvent(
            event_id=f"evt-{uuid.uuid4().hex[:12]}",
            incident_id=incident_id,
            pipeline_id=pipeline_id,
            run_id=run_id,
            agent_name=agent_name,
            action_type=action_type,
            details=details,
            status=status,
            timestamp=datetime.now(timezone.utc),
        )

        self._local_buffer.append(event)
        logger.info(
            "[AuditTrail] Agent=%s Action=%s Pipeline=%s Status=%s Incident=%s",
            agent_name,
            action_type,
            pipeline_id,
            status,
            incident_id or "N/A",
        )

        if self.bq_client:
            self._write_to_bigquery(event)

        return event

    def _write_to_bigquery(self, event: AuditEvent) -> None:
        """Dispatches event to BigQuery audit_log table."""
        try:
            table_ref = f"{self.dataset}.audit_log"
            row = {
                "event_id": event.event_id,
                "incident_id": event.incident_id,
                "pipeline_id": event.pipeline_id,
                "run_id": event.run_id,
                "agent_name": event.agent_name,
                "action_type": event.action_type,
                "details": str(event.details),
                "status": event.status,
                "timestamp": event.timestamp.isoformat(),
            }
            # Inserts row via BigQuery client if configured
            errors = self.bq_client.insert_rows_json(table_ref, [row])
            if errors:
                logger.error("Failed to insert audit event into BigQuery: %s", errors)
        except Exception as exc:
            logger.warning("Could not persist audit event to BigQuery: %s", exc)

    def get_events(self) -> List[AuditEvent]:
        """Returns in-memory recorded events (useful for test assertions)."""
        return list(self._local_buffer)

    def clear(self) -> None:
        """Clears local buffer."""
        self._local_buffer.clear()
