"""
Unit tests for dashboard API endpoints.
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


def test_get_patient_list_success():
    """Test retrieving patient list."""
    headers = get_auth_headers("provider")
    response = client.get("/api/v1/patients", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert "patients" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data
    assert isinstance(data["patients"], list)


def test_get_patient_list_unauthorized():
    """Test patient list without authentication."""
    response = client.get("/api/v1/patients")
    assert response.status_code == 403


def test_get_patient_list_filter_by_risk_tier():
    """Test filtering patient list by risk tier."""
    headers = get_auth_headers("provider")
    response = client.get(
        "/api/v1/patients?risk_tier=high",
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # All returned patients should be high risk
    for patient in data["patients"]:
        assert patient["risk_tier"] == "high"


def test_get_patient_list_filter_by_ckd_stage():
    """Test filtering patient list by CKD stage."""
    headers = get_auth_headers("provider")
    response = client.get(
        "/api/v1/patients?ckd_stage=3a",
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # All returned patients should be stage 3a
    for patient in data["patients"]:
        assert patient["ckd_stage"] == "3a"


def test_get_patient_list_pagination():
    """Test patient list pagination."""
    headers = get_auth_headers("provider")
    
    # Get first page
    response1 = client.get(
        "/api/v1/patients?limit=1&offset=0",
        headers=headers
    )
    assert response1.status_code == 200
    data1 = response1.json()
    assert len(data1["patients"]) <= 1
    assert data1["limit"] == 1
    assert data1["offset"] == 0
    
    # Get second page
    response2 = client.get(
        "/api/v1/patients?limit=1&offset=1",
        headers=headers
    )
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["offset"] == 1


def test_get_patient_detail_success():
    """Test retrieving patient detail."""
    headers = get_auth_headers("provider")
    response = client.get("/api/v1/patients/patient-001", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["patient_id"] == "patient-001"
    assert "clinical" in data
    assert "administrative" in data
    assert "sdoh" in data
    assert "top_factors" in data
    assert len(data["top_factors"]) == 5  # Top 5 factors


def test_get_patient_detail_not_found():
    """Test retrieving non-existent patient."""
    headers = get_auth_headers("provider")
    response = client.get("/api/v1/patients/nonexistent", headers=headers)
    
    assert response.status_code == 404


def test_get_patient_detail_clinical_values():
    """Test patient detail includes clinical values."""
    headers = get_auth_headers("provider")
    response = client.get("/api/v1/patients/patient-001", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    clinical = data["clinical"]
    
    required_fields = ["egfr", "uacr", "hba1c", "systolic_bp", "diastolic_bp", "bmi", "ckd_stage"]
    for field in required_fields:
        assert field in clinical


def test_get_patient_detail_sdoh_indicators():
    """Test patient detail includes SDOH indicators."""
    headers = get_auth_headers("provider")
    response = client.get("/api/v1/patients/patient-001", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    sdoh = data["sdoh"]
    
    required_fields = ["adi_percentile", "food_desert", "housing_stability_score", "transportation_access_score"]
    for field in required_fields:
        assert field in sdoh


def test_acknowledge_patient_success():
    """Test acknowledging a patient alert."""
    headers = get_auth_headers("provider")
    response = client.post(
        "/api/v1/patients/acknowledgments",
        json={
            "patient_id": "patient-001",
            "provider_id": "provider-123",
            "notes": "Scheduled follow-up"
        },
        headers=headers
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["patient_id"] == "patient-001"
    assert data["provider_id"] == "provider-123"
    assert "acknowledged_at" in data
    assert data["success"] is True


def test_acknowledge_patient_not_found():
    """Test acknowledging non-existent patient."""
    headers = get_auth_headers("provider")
    response = client.post(
        "/api/v1/patients/acknowledgments",
        json={
            "patient_id": "nonexistent",
            "provider_id": "provider-123"
        },
        headers=headers
    )
    
    assert response.status_code == 404


def test_acknowledge_patient_forbidden_role():
    """Test case manager cannot acknowledge (only provider/admin)."""
    headers = get_auth_headers("case_manager")
    response = client.post(
        "/api/v1/patients/acknowledgments",
        json={
            "patient_id": "patient-001",
            "provider_id": "provider-123"
        },
        headers=headers
    )
    
    assert response.status_code == 403


def test_acknowledge_patient_updates_status():
    """Test acknowledgment updates patient status."""
    headers = get_auth_headers("provider")
    
    # Acknowledge patient
    client.post(
        "/api/v1/patients/acknowledgments",
        json={
            "patient_id": "patient-002",
            "provider_id": "provider-123"
        },
        headers=headers
    )
    
    # Check patient detail shows acknowledged
    response = client.get("/api/v1/patients/patient-002", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["acknowledged"] is True
    assert data["acknowledged_by"] == "provider-123"


def test_case_manager_can_view_patients():
    """Test case manager has read access to patient list."""
    headers = get_auth_headers("case_manager")
    response = client.get("/api/v1/patients", headers=headers)
    
    assert response.status_code == 200


def test_admin_full_access():
    """Test admin has full access to all endpoints."""
    headers = get_auth_headers("admin")
    
    # Can view list
    response1 = client.get("/api/v1/patients", headers=headers)
    assert response1.status_code == 200
    
    # Can view detail
    response2 = client.get("/api/v1/patients/patient-001", headers=headers)
    assert response2.status_code == 200
    
    # Can acknowledge
    response3 = client.post(
        "/api/v1/patients/acknowledgments",
        json={"patient_id": "patient-003", "provider_id": "admin-001"},
        headers=headers
    )
    assert response3.status_code == 201
