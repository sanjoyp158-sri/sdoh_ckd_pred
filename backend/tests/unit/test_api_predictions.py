"""
Unit tests for prediction API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import create_access_token


client = TestClient(app)


def get_auth_headers(role="provider"):
    """Helper to get authentication headers."""
    token = create_access_token(
        data={"sub": "testuser", "user_id": "test-001", "role": role}
    )
    return {"Authorization": f"Bearer {token}"}


def test_predict_success():
    """Test successful prediction request."""
    headers = get_auth_headers("provider")
    response = client.post(
        "/api/v1/predictions/predict",
        json={"patient_id": "patient-test-001"},
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["patient_id"] == "patient-test-001"
    assert "risk_score" in data
    assert 0.0 <= data["risk_score"] <= 1.0
    assert "risk_tier" in data
    assert data["risk_tier"] in ["high", "moderate", "low"]
    assert "top_factors" in data
    assert "model_version" in data
    assert "processing_time_ms" in data


def test_predict_unauthorized():
    """Test prediction without authentication."""
    response = client.post(
        "/api/v1/predictions/predict",
        json={"patient_id": "patient-test-001"}
    )
    
    assert response.status_code == 403  # No credentials


def test_predict_forbidden_role():
    """Test prediction with unauthorized role."""
    headers = get_auth_headers("case_manager")
    response = client.post(
        "/api/v1/predictions/predict",
        json={"patient_id": "patient-test-001"},
        headers=headers
    )
    
    assert response.status_code == 403
    assert "Access denied" in response.json()["detail"]


def test_predict_admin_role():
    """Test prediction with admin role."""
    headers = get_auth_headers("admin")
    response = client.post(
        "/api/v1/predictions/predict",
        json={"patient_id": "patient-admin-test"},
        headers=headers
    )
    
    assert response.status_code == 200


def test_get_prediction_success():
    """Test retrieving existing prediction."""
    # First create a prediction
    headers = get_auth_headers("provider")
    client.post(
        "/api/v1/predictions/predict",
        json={"patient_id": "patient-get-test"},
        headers=headers
    )
    
    # Then retrieve it
    response = client.get(
        "/api/v1/predictions/patient-get-test",
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["patient_id"] == "patient-get-test"


def test_get_prediction_not_found():
    """Test retrieving non-existent prediction."""
    headers = get_auth_headers("provider")
    response = client.get(
        "/api/v1/predictions/nonexistent-patient",
        headers=headers
    )
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_prediction_case_manager_access():
    """Test case manager can retrieve predictions."""
    # Create prediction as provider
    provider_headers = get_auth_headers("provider")
    client.post(
        "/api/v1/predictions/predict",
        json={"patient_id": "patient-cm-test"},
        headers=provider_headers
    )
    
    # Retrieve as case manager
    cm_headers = get_auth_headers("case_manager")
    response = client.get(
        "/api/v1/predictions/patient-cm-test",
        headers=cm_headers
    )
    
    assert response.status_code == 200


def test_prediction_response_structure():
    """Test prediction response has all required fields."""
    headers = get_auth_headers("provider")
    response = client.post(
        "/api/v1/predictions/predict",
        json={"patient_id": "patient-structure-test"},
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Check required fields
    required_fields = [
        "patient_id", "risk_score", "risk_tier", "prediction_date",
        "model_version", "processing_time_ms", "top_factors"
    ]
    for field in required_fields:
        assert field in data, f"Missing required field: {field}"
    
    # Check top_factors structure
    if len(data["top_factors"]) > 0:
        factor = data["top_factors"][0]
        assert "feature_name" in factor
        assert "feature_value" in factor
        assert "shap_value" in factor
        assert "category" in factor
        assert "direction" in factor
