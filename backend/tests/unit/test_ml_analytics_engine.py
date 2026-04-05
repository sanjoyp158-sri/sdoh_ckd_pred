"""
Unit tests for ML Analytics Engine.
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np
from xgboost import XGBClassifier
import joblib

from app.ml.analytics_engine import MLAnalyticsEngine, ModelRegistry
from app.models.patient import (
    UnifiedPatientRecord,
    Demographics,
    Address,
    ClinicalRecord,
    AdministrativeRecord,
    SDOHRecord,
    Medication,
    Referral,
    RiskTier,
)
from app.models.ml import ModelMetrics, SubgroupMetrics


@pytest.fixture
def sample_patient():
    """Create a sample patient record for testing."""
    return UnifiedPatientRecord(
        patient_id="test-patient-001",
        demographics=Demographics(
            age=65,
            sex="M",
            race="White",
            ethnicity="Non-Hispanic",
            address=Address(
                street="123 Main St",
                city="Springfield",
                state="IL",
                zip_code="62701",
                zcta="62701",
            ),
        ),
        clinical=ClinicalRecord(
            egfr=45.0,
            egfr_history=[
                (datetime.now() - timedelta(days=365), 50.0),
                (datetime.now() - timedelta(days=180), 47.0),
                (datetime.now(), 45.0),
            ],
            uacr=150.0,
            hba1c=7.2,
            systolic_bp=140,
            diastolic_bp=85,
            bmi=28.5,
            medications=[
                Medication(name="Lisinopril", category="ACE_inhibitor", active=True),
                Medication(name="Metformin", category="Diabetes", active=True),
            ],
            ckd_stage="3a",
            diagnosis_date=datetime.now() - timedelta(days=730),
            comorbidities=["diabetes", "hypertension"],
        ),
        administrative=AdministrativeRecord(
            visit_frequency_12mo=8,
            specialist_referrals=[
                Referral(
                    specialty="Nephrology",
                    date=datetime.now() - timedelta(days=90),
                    completed=True,
                    reason="CKD management",
                ),
            ],
            insurance_type="Medicare",
            insurance_status="Active",
            last_visit_date=datetime.now() - timedelta(days=30),
        ),
        sdoh=SDOHRecord(
            adi_percentile=75,
            food_desert=True,
            housing_stability_score=0.6,
            transportation_access_score=0.4,
            rural_urban_code="3",
        ),
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


@pytest.fixture
def mock_model(tmp_path):
    """Create a mock XGBoost model for testing."""
    # Create a simple mock model
    X_train = np.random.rand(100, 30)
    y_train = np.random.randint(0, 2, 100)
    
    model = XGBClassifier(n_estimators=10, max_depth=3, random_state=42)
    model.fit(X_train, y_train)
    
    # Save model to temp path
    model_path = tmp_path / "test_model.joblib"
    joblib.dump(model, model_path)
    
    return str(model_path)


class TestModelRegistry:
    """Tests for ModelRegistry class."""
    
    def test_register_model(self, tmp_path):
        """Test registering a new model."""
        registry = ModelRegistry(registry_path=str(tmp_path / "registry"))
        
        metrics = ModelMetrics(
            auroc=0.88,
            sensitivity=0.85,
            specificity=0.82,
            ppv=0.78,
            npv=0.87,
            subgroup_metrics={},
            training_date=datetime.now(),
            model_version="v1.0.0",
        )
        
        entry = registry.register_model(
            model_id="model-001",
            model_version="v1.0.0",
            model_path="/path/to/model",
            metrics=metrics,
            is_production=False,
        )
        
        assert entry.model_id == "model-001"
        assert entry.model_version == "v1.0.0"
        assert entry.is_production is False
        assert entry.metrics.auroc == 0.88
    
    def test_get_model(self, tmp_path):
        """Test retrieving a model by ID."""
        registry = ModelRegistry(registry_path=str(tmp_path / "registry"))
        
        metrics = ModelMetrics(
            auroc=0.88,
            sensitivity=0.85,
            specificity=0.82,
            ppv=0.78,
            npv=0.87,
            subgroup_metrics={},
            training_date=datetime.now(),
            model_version="v1.0.0",
        )
        
        registry.register_model(
            model_id="model-001",
            model_version="v1.0.0",
            model_path="/path/to/model",
            metrics=metrics,
        )
        
        retrieved = registry.get_model("model-001")
        assert retrieved is not None
        assert retrieved.model_id == "model-001"
        
        not_found = registry.get_model("nonexistent")
        assert not_found is None
    
    def test_promote_to_production(self, tmp_path):
        """Test promoting a model to production."""
        registry = ModelRegistry(registry_path=str(tmp_path / "registry"))
        
        metrics = ModelMetrics(
            auroc=0.88,
            sensitivity=0.85,
            specificity=0.82,
            ppv=0.78,
            npv=0.87,
            subgroup_metrics={},
            training_date=datetime.now(),
            model_version="v1.0.0",
        )
        
        registry.register_model(
            model_id="model-001",
            model_version="v1.0.0",
            model_path="/path/to/model",
            metrics=metrics,
        )
        
        registry.promote_to_production("model-001")
        
        prod_model = registry.get_production_model()
        assert prod_model is not None
        assert prod_model.model_id == "model-001"
        assert prod_model.is_production is True
    
    def test_rollback(self, tmp_path):
        """Test rolling back to previous model version."""
        registry = ModelRegistry(registry_path=str(tmp_path / "registry"))
        
        metrics_v1 = ModelMetrics(
            auroc=0.87,
            sensitivity=0.84,
            specificity=0.81,
            ppv=0.77,
            npv=0.86,
            subgroup_metrics={},
            training_date=datetime.now(),
            model_version="v1.0.0",
        )
        
        metrics_v2 = ModelMetrics(
            auroc=0.89,
            sensitivity=0.86,
            specificity=0.83,
            ppv=0.79,
            npv=0.88,
            subgroup_metrics={},
            training_date=datetime.now(),
            model_version="v2.0.0",
        )
        
        # Register v1 and promote
        registry.register_model(
            model_id="model-v1",
            model_version="v1.0.0",
            model_path="/path/to/model-v1",
            metrics=metrics_v1,
        )
        registry.promote_to_production("model-v1")
        
        # Register v2 with v1 as previous version
        registry.register_model(
            model_id="model-v2",
            model_version="v2.0.0",
            model_path="/path/to/model-v2",
            metrics=metrics_v2,
            previous_version="v1.0.0",
        )
        registry.promote_to_production("model-v2")
        
        # Rollback to v1
        rolled_back = registry.rollback()
        assert rolled_back is not None
        assert rolled_back.model_version == "v1.0.0"
        
        prod_model = registry.get_production_model()
        assert prod_model.model_version == "v1.0.0"


class TestMLAnalyticsEngine:
    """Tests for MLAnalyticsEngine class."""
    
    def test_initialization(self, tmp_path):
        """Test engine initialization."""
        registry = ModelRegistry(registry_path=str(tmp_path / "registry"))
        engine = MLAnalyticsEngine(model_registry=registry)
        
        assert engine.model_registry is not None
        assert engine._classifier is None
    
    def test_load_model(self, mock_model):
        """Test loading a model from disk."""
        engine = MLAnalyticsEngine()
        engine.load_model(mock_model)
        
        assert engine._classifier is not None
    
    def test_load_model_file_not_found(self):
        """Test loading a non-existent model file."""
        engine = MLAnalyticsEngine()
        
        with pytest.raises(FileNotFoundError):
            engine.load_model("/nonexistent/model.joblib")
    
    def test_extract_features(self, sample_patient):
        """Test feature extraction from patient record."""
        engine = MLAnalyticsEngine()
        features_df = engine.extract_features(sample_patient)
        
        # Check that DataFrame has expected structure
        assert len(features_df) == 1
        assert 'egfr' in features_df.columns
        assert 'uacr' in features_df.columns
        assert 'adi_percentile' in features_df.columns
        
        # Check feature values
        assert features_df['egfr'].iloc[0] == 45.0
        assert features_df['uacr'].iloc[0] == 150.0
        assert features_df['adi_percentile'].iloc[0] == 75
        assert features_df['food_desert'].iloc[0] == 1
        
        # Check derived features
        assert features_df['has_diabetes'].iloc[0] == 1
        assert features_df['has_hypertension'].iloc[0] == 1
        assert features_df['medication_count'].iloc[0] == 2
        assert features_df['ace_inhibitor'].iloc[0] == 1
    
    def test_calculate_egfr_slope(self):
        """Test eGFR slope calculation."""
        engine = MLAnalyticsEngine()
        
        # Test with declining eGFR
        history = [
            (datetime.now() - timedelta(days=365), 50.0),
            (datetime.now() - timedelta(days=180), 47.0),
            (datetime.now(), 45.0),
        ]
        slope = engine._calculate_egfr_slope(history)
        assert slope < 0  # Should be negative (declining)
        
        # Test with insufficient data
        short_history = [(datetime.now(), 45.0)]
        slope = engine._calculate_egfr_slope(short_history)
        assert slope == 0.0
    
    def test_classify_risk_tier(self):
        """Test risk tier classification."""
        engine = MLAnalyticsEngine()
        
        assert engine._classify_risk_tier(0.70) == RiskTier.HIGH
        assert engine._classify_risk_tier(0.65) == RiskTier.MODERATE
        assert engine._classify_risk_tier(0.50) == RiskTier.MODERATE
        assert engine._classify_risk_tier(0.35) == RiskTier.MODERATE
        assert engine._classify_risk_tier(0.30) == RiskTier.LOW
    
    def test_predict_progression_risk(self, mock_model, sample_patient):
        """Test prediction generation."""
        engine = MLAnalyticsEngine()
        engine.load_model(mock_model)
        
        result = engine.predict_progression_risk(sample_patient)
        
        assert result.patient_id == "test-patient-001"
        assert 0.0 <= result.risk_score <= 1.0
        assert result.risk_tier in [RiskTier.HIGH, RiskTier.MODERATE, RiskTier.LOW]
        assert result.processing_time_ms >= 0
        assert result.model_version is not None
    
    def test_predict_without_model(self, sample_patient):
        """Test prediction fails without loaded model."""
        engine = MLAnalyticsEngine()
        
        with pytest.raises(ValueError, match="Model not loaded"):
            engine.predict_progression_risk(sample_patient)
    
    def test_get_feature_names(self):
        """Test getting feature names."""
        engine = MLAnalyticsEngine()
        feature_names = engine.get_feature_names()
        
        assert isinstance(feature_names, list)
        assert len(feature_names) > 0
        assert 'egfr' in feature_names
        assert 'adi_percentile' in feature_names
        assert 'race' not in feature_names  # Should not include race
        assert 'ethnicity' not in feature_names  # Should not include ethnicity


class TestFeatureEngineering:
    """Tests for feature engineering logic."""
    
    def test_interaction_features(self, sample_patient):
        """Test interaction feature calculation."""
        engine = MLAnalyticsEngine()
        features_df = engine.extract_features(sample_patient)
        
        # Check interaction features
        egfr_x_adi = features_df['egfr_x_adi'].iloc[0]
        expected = 45.0 * 75
        assert egfr_x_adi == expected
        
        uacr_x_food_desert = features_df['uacr_x_food_desert'].iloc[0]
        expected = 150.0 * 1
        assert uacr_x_food_desert == expected
    
    def test_temporal_features(self, sample_patient):
        """Test temporal feature calculation."""
        engine = MLAnalyticsEngine()
        features_df = engine.extract_features(sample_patient)
        
        # Check years since diagnosis
        years = features_df['years_since_diagnosis'].iloc[0]
        assert years > 1.9  # Should be around 2 years
        assert years < 2.1
        
        # Check eGFR slope
        slope = features_df['egfr_slope'].iloc[0]
        assert slope < 0  # Should be negative (declining)
    
    def test_no_race_ethnicity_features(self, sample_patient):
        """Test that race and ethnicity are not included as features."""
        engine = MLAnalyticsEngine()
        features_df = engine.extract_features(sample_patient)
        
        # Ensure race and ethnicity are NOT in features
        assert 'race' not in features_df.columns
        assert 'ethnicity' not in features_df.columns
        
        # Also check feature names list
        feature_names = engine.get_feature_names()
        assert 'race' not in feature_names
        assert 'ethnicity' not in feature_names
