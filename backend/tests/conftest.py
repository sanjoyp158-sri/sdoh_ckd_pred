"""
Pytest configuration and fixtures.
"""

import pytest
import numpy as np
from xgboost import XGBClassifier
import joblib
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Test client for FastAPI application."""
    return TestClient(app)


@pytest.fixture(scope="session")
def mock_model_for_property_tests(tmp_path_factory):
    """
    Create a mock XGBoost model for property-based testing.
    
    This model is trained with synthetic data that has realistic feature relationships:
    - Clinical features (egfr, uacr, hba1c, bp, bmi) strongly predict outcome
    - Administrative features (visit frequency, insurance) moderately predict outcome  
    - SDOH features (adi, food_desert, housing, transportation) moderately predict outcome
    """
    np.random.seed(42)
    
    # Generate 1000 synthetic training samples with 30 features
    n_samples = 1000
    n_features = 30
    
    # Create feature matrix with realistic ranges
    X_train = np.zeros((n_samples, n_features))
    
    # Clinical features (indices 0-9): strong predictors
    X_train[:, 0] = np.random.uniform(30, 89, n_samples)  # egfr
    X_train[:, 1] = np.random.uniform(0, 5000, n_samples)  # uacr
    X_train[:, 2] = np.random.uniform(4, 14, n_samples)  # hba1c
    X_train[:, 3] = np.random.uniform(80, 200, n_samples)  # systolic_bp
    X_train[:, 4] = np.random.uniform(40, 130, n_samples)  # diastolic_bp
    X_train[:, 5] = np.random.uniform(15, 60, n_samples)  # bmi
    X_train[:, 6] = np.random.randint(0, 10, n_samples)  # medication_count
    X_train[:, 7] = np.random.randint(0, 2, n_samples)  # has_diabetes
    X_train[:, 8] = np.random.randint(0, 2, n_samples)  # has_hypertension
    X_train[:, 9] = np.random.uniform(-10, 2, n_samples)  # egfr_slope
    
    # Administrative features (indices 10-14): moderate predictors
    X_train[:, 10] = np.random.randint(0, 50, n_samples)  # visit_frequency_12mo
    X_train[:, 11] = np.random.randint(0, 10, n_samples)  # specialist_referral_count
    X_train[:, 12] = np.random.randint(0, 2, n_samples)  # insurance_medicare
    X_train[:, 13] = np.random.randint(0, 2, n_samples)  # insurance_medicaid
    X_train[:, 14] = np.random.randint(0, 2, n_samples)  # insurance_uninsured
    
    # SDOH features (indices 15-19): moderate predictors
    X_train[:, 15] = np.random.randint(1, 101, n_samples)  # adi_percentile
    X_train[:, 16] = np.random.randint(0, 2, n_samples)  # food_desert
    X_train[:, 17] = np.random.uniform(0, 1, n_samples)  # housing_stability_score
    X_train[:, 18] = np.random.uniform(0, 1, n_samples)  # transportation_access_score
    X_train[:, 19] = np.random.randint(18, 100, n_samples)  # age
    
    # Other features (indices 20-29): fill with random data
    X_train[:, 20:] = np.random.rand(n_samples, 10)
    
    # Create outcome based on feature relationships
    # Lower egfr, higher uacr, higher hba1c, higher adi -> higher risk
    risk_score = (
        (89 - X_train[:, 0]) / 59 * 0.3 +  # egfr (lower is worse)
        (X_train[:, 1] / 5000) * 0.2 +  # uacr (higher is worse)
        ((X_train[:, 2] - 4) / 10) * 0.15 +  # hba1c (higher is worse)
        (X_train[:, 15] / 100) * 0.15 +  # adi (higher is worse)
        (X_train[:, 16]) * 0.1 +  # food_desert (yes is worse)
        ((50 - X_train[:, 10]) / 50) * 0.1  # visit_frequency (lower is worse)
    )
    
    # Add some noise
    risk_score += np.random.normal(0, 0.1, n_samples)
    risk_score = np.clip(risk_score, 0, 1)
    
    # Convert to binary outcome (threshold at 0.5)
    y_train = (risk_score > 0.5).astype(int)
    
    # Train model
    model = XGBClassifier(
        n_estimators=50,
        max_depth=5,
        learning_rate=0.1,
        random_state=42,
        use_label_encoder=False,
        eval_metric='logloss'
    )
    model.fit(X_train, y_train)
    
    # Save model to temp path
    tmp_path = tmp_path_factory.mktemp("models")
    model_path = tmp_path / "test_model.joblib"
    joblib.dump(model, model_path)
    
    return str(model_path)
