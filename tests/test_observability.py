import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

def test_metrics_endpoint():
    """Verify that the /metrics endpoint is available and returns Prometheus data."""
    response = client.get("/metrics")
    assert response.status_code == 200
    # process_cpu_seconds_total is Linux-only; check cross-platform metrics instead
    assert "python_gc_objects_collected_total" in response.text
    assert "http_request_duration_seconds" in response.text

def test_health_check_with_db(db_session):
    """Verify health check router which now uses instrumented app or logging."""
    response = client.get("/api/stats/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded"]
    assert "checks" in data
