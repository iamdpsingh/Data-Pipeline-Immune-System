# ==============================================================================
# Data Pipeline Immune System — Cloud Run HTTP API Service
# ==============================================================================
"""HTTP API service hosted on Cloud Run providing endpoints for Airflow and dashboard.

Endpoints:
  GET  /health                   - Liveness and readiness probe
  GET  /api/v1/health-score      - Daily pipeline composite health scores
  POST /api/v1/runs/complete     - Webhook for Airflow DAG run completions
  POST /api/v1/incidents/approve - Operator approval for HIGH risk actions
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

from agents.remediation_agent import ApprovalRecord
from src.config.settings import load_settings
from src.controller.controller import ImmuneSystemController

logger = logging.getLogger("dpis.api")
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Data Pipeline Immune System API",
    description="Autonomous data reliability and self-healing pipeline controller",
    version="1.0.0",
)

settings = load_settings(os.getenv("ENVIRONMENT", "dev"))
controller = ImmuneSystemController(settings=settings)


class RunCompletionPayload(BaseModel):
    pipeline_id: str = Field(..., example="orders")
    run_id: str = Field(..., example="run-20261023-001")
    context: Dict[str, Any] = Field(default_factory=dict)


class ApprovalPayload(BaseModel):
    incident_id: str = Field(..., example="inc-77f98d")
    approved_by: str = Field(..., example="data_engineer@company.com")
    approval_id: str = Field(..., example="appr-20261023-01")
    pipeline_id: str = Field(default="orders")
    run_id: str = Field(default="run-manual")
    context: Dict[str, Any] = Field(default_factory=dict)


@app.get("/health", status_code=status.HTTP_200_OK)
def health_check() -> Dict[str, str]:
    """Liveness probe for Cloud Run container monitoring."""
    return {
        "status": "UP",
        "service": "DataPipelineImmuneSystem",
        "environment": settings.environment,
        "project": settings.project.id,
    }


@app.post("/api/v1/runs/complete", status_code=status.HTTP_200_OK)
def handle_run_completion(payload: RunCompletionPayload) -> Dict[str, Any]:
    """Receives pipeline completion events and executes the immune cycle."""
    try:
        result = controller.handle_run_completion(
            pipeline_id=payload.pipeline_id,
            run_id=payload.run_id,
            context=payload.context,
        )
        return {
            "incident_id": result.incident_id,
            "pipeline_id": result.pipeline_id,
            "run_id": result.run_id,
            "final_state": result.final_state.value,
            "message": result.message,
            "auto_remediated": result.remediation is not None,
        }
    except Exception as exc:
        logger.error("Error processing run completion: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@app.post("/api/v1/incidents/approve", status_code=status.HTTP_200_OK)
def approve_incident_action(payload: ApprovalPayload) -> Dict[str, Any]:
    """Authorizes a high-risk remediation action awaiting human sign-off."""
    approval_rec = ApprovalRecord(
        incident_id=payload.incident_id,
        approved_by=payload.approved_by,
        approved_at=os.getenv("CURRENT_TIME", "2026-10-23T08:30:00Z"),
        approval_id=payload.approval_id,
    )

    try:
        result = controller.handle_run_completion(
            pipeline_id=payload.pipeline_id,
            run_id=payload.run_id,
            context=payload.context,
            approval=approval_rec,
        )
        return {
            "incident_id": result.incident_id,
            "final_state": result.final_state.value,
            "message": result.message,
        }
    except Exception as exc:
        logger.error("Error executing approved action: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )
