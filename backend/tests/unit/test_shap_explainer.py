"""
Unit tests for SHAP Explainer.
"""

import pytest
import numpy as np
from datetime import datetime
from xgboost import XGBClassifier

from app.ml.shap_explainer import SHAPExplainer
from app.models.patient import (
    UnifiedPatientRecord,
    Demographics,
    ClinicalRecord,
    AdministrativeRecord,
    SDOHRecord,
    Address,
    RiskTier
)


@pytest.fixture
def trained_model():
    """Create a simple trained XGBoost model for testing."""
    np.random.seed(42)
    n_samples = 100
    n_features = 9
    
    # Create synthetic training data
    X_train = np.random.randn(n_samples, n_features)
    y_train = np.random.randint(0, 2, n_samples)
    
    # Train a simple model
    model = XGBClassifier(
        n_estimators=10,
        max_depth=3,
        random_state=42,
        use_label_encoder=False,
        eval_metric='logloss'
    )
    model.fit(X_train, y_train)
    
    return model


@pytest.fixture
def feature_names():
    """Sample feature names."""
    return [
        'egfr_baseline',
        'egfr_slope',
        'uacr_baseline',
        'hba1c',
        'sbp',
        'adi_percentile',
        'food_desert',
        'visit_frequency_12mo',
        'insurance_uninsured'
    ]


@pytest.fixture
def background_data():
    """Sample background data (100 samples, 9 features)."""
    np.random.seed(42)
    return np.random.randn(100, 9)


@pytest.fixture
def sample_patient():
    """Create a sample patient record."""
    return UnifiedPatientRecord(
        patient_id="test_001",
        demographics=Demographics(
            age=65,
            sex="M",
            address=Address(zip_code="12345", state="NY")
        ),
        clinical=ClinicalRecord(
            egfr=35.0,
            egfr_history=[(datetime.now(), 40.0), (datetime.now(), 35.0)],
            uacr=250.0,
            hba1c=7.5,
            systolic_bp=145,
            diastolic_bp=85,
            bmi=32.0,
            medications=[],
            ckd_stage="3b",
            diagnosis_date=datetime.now(),
            comorbidities=["diabetes", "hypertension"]
        ),
        administrative=AdministrativeRecord(
            visit_frequency_12mo=4,
            specialist_referrals=[],
            insurance_type="Medicare",
            insurance_status="Active",
            last_visit_date=datetime.now()
        ),
        sdoh=SDOHRecord(
            adi_percentile=85,
            food_desert=True,
            housing_stability_score=0.4,
            transportation_access_score=0.6,
            rural_urban_code="rural"
        ),
        created_at=datetime.now(),
        updated_at=datetime.now()
    )


class TestSHAPExplainerInitialization:
    """Test SHAP Explainer initialization."""
    
    def test_initialization_with_background_data(self, trained_model, feature_names, background_data):
        """Test initialization with background data."""
        explainer = SHAPExplainer(trained_model, feature_names, background_data)
        
        assert explainer.model == trained_model
        assert explainer.feature_names == feature_names
        assert explainer.background_data is not None
        assert explainer.explainer is not None
        assert isinstance(explainer.baseline_risk, float)
    
    def test_initialization_without_background_data(self, trained_model, feature_names):
        """Test initialization without background data."""
        explainer = SHAPExplainer(trained_model, feature_names)
        
        assert explainer.model == trained_model
        assert explainer.feature_names == feature_names
        assert explainer.background_data is None
        assert explainer.explainer is not None


class TestSHAPValueComputation:
    """Test SHAP value computation."""
    
    def test_compute_shap_values_returns_dict(self, trained_model, feature_names, background_data):
        """Test that compute_shap_values returns a dictionary."""
        explainer = SHAPExplainer(trained_model, feature_names, background_data)
        features = np.random.randn(9)
        
        shap_values = explainer.compute_shap_values(features)
        
        assert isinstance(shap_values, dict)
        assert len(shap_values) == len(feature_names)
        assert all(name in shap_values for name in feature_names)
        assert all(isinstance(v, float) for v in shap_values.values())
    
    def test_compute_shap_values_handles_2d_input(self, trained_model, feature_names, background_data):
        """Test that compute_shap_values handles 2D input."""
        explainer = SHAPExplainer(trained_model, feature_names, background_data)
        features = np.random.randn(1, 9)
        
        shap_values = explainer.compute_shap_values(features)
        
        assert isinstance(shap_values, dict)
        assert len(shap_values) == len(feature_names)


class TestTopFactors:
    """Test top factor identification."""
    
    def test_get_top_factors_returns_correct_count(self, trained_model, feature_names, background_data):
        """Test that get_top_factors returns correct number of factors."""
        explainer = SHAPExplainer(trained_model, feature_names, background_data)
        
        shap_values = {name: float(i) for i, name in enumerate(feature_names)}
        feature_values = {name: float(i * 10) for i, name in enumerate(feature_names)}
        
        top_factors = explainer.get_top_factors(shap_values, feature_values, n=5)
        
        assert len(top_factors) == 5
    
    def test_get_top_factors_sorted_by_absolute_value(self, trained_model, feature_names, background_data):
        """Test that top factors are sorted by absolute SHAP value."""
        explainer = SHAPExplainer(trained_model, feature_names, background_data)
        
        shap_values = {
            'egfr_baseline': -0.5,
            'adi_percentile': 0.3,
            'uacr_baseline': 0.8,
            'hba1c': -0.2,
            'food_desert': 0.1
        }
        feature_values = {name: 1.0 for name in shap_values.keys()}
        
        top_factors = explainer.get_top_factors(shap_values, feature_values, n=3)
        
        assert len(top_factors) == 3
        assert abs(top_factors[0].shap_value) >= abs(top_factors[1].shap_value)
        assert abs(top_factors[1].shap_value) >= abs(top_factors[2].shap_value)
    
    def test_get_top_factors_includes_direction(self, trained_model, feature_names, background_data):
        """Test that factors include correct direction."""
        explainer = SHAPExplainer(trained_model, feature_names, background_data)
        
        shap_values = {
            'egfr_baseline': -0.5,
            'adi_percentile': 0.3
        }
        feature_values = {name: 1.0 for name in shap_values.keys()}
        
        top_factors = explainer.get_top_factors(shap_values, feature_values, n=2)
        
        assert top_factors[0].direction in ["increases_risk", "decreases_risk"]
        assert top_factors[1].direction in ["increases_risk", "decreases_risk"]


class TestFactorCategorization:
    """Test factor categorization."""
    
    def test_categorize_feature_clinical(self, trained_model, feature_names, background_data):
        """Test clinical feature categorization."""
        explainer = SHAPExplainer(trained_model, feature_names, background_data)
        
        assert explainer._categorize_feature('egfr_baseline') == 'clinical'
        assert explainer._categorize_feature('uacr_baseline') == 'clinical'
        assert explainer._categorize_feature('hba1c') == 'clinical'
        assert explainer._categorize_feature('diabetes') == 'clinical'
    
    def test_categorize_feature_administrative(self, trained_model, feature_names, background_data):
        """Test administrative feature categorization."""
        explainer = SHAPExplainer(trained_model, feature_names, background_data)
        
        assert explainer._categorize_feature('visit_frequency_12mo') == 'administrative'
        assert explainer._categorize_feature('insurance_uninsured') == 'administrative'
        assert explainer._categorize_feature('missed_referral') == 'administrative'
    
    def test_categorize_feature_sdoh(self, trained_model, feature_names, background_data):
        """Test SDOH feature categorization."""
        explainer = SHAPExplainer(trained_model, feature_names, background_data)
        
        assert explainer._categorize_feature('adi_percentile') == 'sdoh'
        assert explainer._categorize_feature('food_desert') == 'sdoh'
        assert explainer._categorize_feature('housing_stability') == 'sdoh'
        assert explainer._categorize_feature('poverty_rate') == 'sdoh'


class TestNormalization:
    """Test SHAP value normalization."""
    
    def test_verify_normalization_correct(self, trained_model, feature_names, background_data):
        """Test normalization verification with correct values."""
        explainer = SHAPExplainer(trained_model, feature_names, background_data)
        explainer.baseline_risk = 0.2
        
        # SHAP values that sum to (prediction - baseline)
        prediction = 0.7
        shap_values = {
            'feature1': 0.3,
            'feature2': 0.1,
            'feature3': 0.1
        }
        
        assert explainer.verify_normalization(shap_values, prediction)
    
    def test_verify_normalization_incorrect(self, trained_model, feature_names, background_data):
        """Test normalization verification with incorrect values."""
        explainer = SHAPExplainer(trained_model, feature_names, background_data)
        explainer.baseline_risk = 0.2
        
        # SHAP values that don't sum correctly
        prediction = 0.7
        shap_values = {
            'feature1': 0.1,
            'feature2': 0.1,
            'feature3': 0.1
        }
        
        assert not explainer.verify_normalization(shap_values, prediction)
