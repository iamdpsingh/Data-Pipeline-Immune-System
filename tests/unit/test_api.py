"""Unit tests for FastAPI endpoints."""

from fastapi.testclient import TestClient

from src.api import app

client = TestClient(app)


def test_health_check_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "UP"
    assert data["service"] == "DataPipelineImmuneSystem"


def test_run_completion_webhook_clean_run():
    payload = {
        "pipeline_id": "orders",
        "run_id": "run-api-test-001",
        "context": {
            "task_status": "SUCCESS",
            "rows_written": 1000,
            "historical_row_counts": [990, 1010, 1000, 1005, 995, 1020, 1000],
        },
    }
    response = client.post("/api/v1/runs/complete", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["final_state"] == "RESOLVED"
    assert data["incident_id"] is None
