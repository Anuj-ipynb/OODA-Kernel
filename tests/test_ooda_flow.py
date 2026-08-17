import pytest
from fastapi.testclient import TestClient
from app.api.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_submit_low_risk_incident():
    """Low-risk telemetry should process automatically to completion."""
    payload = {"telemetry": "echo 'normal logs trace'"}
    response = client.post("/api/incident/submit", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "incident_id" in data
    assert data["is_interrupted"] is False

def test_submit_high_risk_incident_and_approve():
    """High-risk incident should pause for approval and complete after approval."""
    # DB crash telemetry triggers high-risk command in decide_node (risk_score >= 0.85)
    payload = {"telemetry": "Connection pool exhausted: postgresql://db:5432"}
    response = client.post("/api/incident/submit", json=payload)
    assert response.status_code == 200
    data = response.json()
    incident_id = data["incident_id"]
    
    assert data["is_interrupted"] is True
    assert data["status"] == "AWAITING_APPROVAL"
    
    # Verify state via GET endpoint
    state_res = client.get(f"/api/incident/{incident_id}/state")
    assert state_res.status_code == 200
    assert state_res.json()["values"]["risk_score"] >= 0.85
    
    # Resume graph execution via /approve endpoint
    approve_res = client.post(
        f"/api/incident/{incident_id}/approve",
        json={"approved": True, "operator_notes": "Test approval"}
    )
    assert approve_res.status_code == 200
    approve_data = approve_res.json()
    assert approve_data["is_verified"] is True
