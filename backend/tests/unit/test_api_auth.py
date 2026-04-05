"""
Unit tests for authentication API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_login_success():
    """Test successful login with valid credentials."""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "provider1", "password": "password123"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert len(data["access_token"]) > 0


def test_login_invalid_username():
    """Test login with invalid username."""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "invalid_user", "password": "password123"}
    )
    
    assert response.status_code == 401
    assert "Incorrect username or password" in response.json()["detail"]


def test_login_invalid_password():
    """Test login with invalid password."""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "provider1", "password": "wrong_password"}
    )
    
    assert response.status_code == 401
    assert "Incorrect username or password" in response.json()["detail"]


def test_login_missing_fields():
    """Test login with missing fields."""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "provider1"}
    )
    
    assert response.status_code == 422  # Validation error


def test_admin_login():
    """Test admin user login."""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin1", "password": "admin123"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
