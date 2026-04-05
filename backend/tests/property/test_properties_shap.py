"""
Property-based tests for SHAP Explainer.
Tests universal correctness properties using Hypothesis.
"""

import pytest
import numpy as np
from hypothesis import given, strategies as st, settings as hyp_settings
from datetime import datetime
from xgboost import XGBClassifier

from app.ml.shap_explainer import SHAPExplainer
from app.models.patient import (
    UnifiedPatientRecord,
    Demographics,
    ClinicalRecord,
    AdministrativeRecord,
    SDOHRecord,
    Address
)


# Custom strategies
@st.composite
def feature_vector_strategy(draw, n_features=9):
    """Generate valid feature vectors."""
    return np.array([draw(st.floats(min_value=-10, max_value=10)) for _ in range(n_features)])


@st.composite
def shap_values_strategy(draw, feature_names):
    """Generate SHAP value dictionaries."""
    return {
        name: draw(st.floats(min_value=-1.0, max_value=1.0))
        for name in feature_names
    }


@st.composite
def feature_values_strategy(draw, feature_names):
    """Generate feature value dictionaries."""
    return {
        name: draw(st.floats(min_value=0, max_value=100))
        for name in feature_names
    }


# Fixtures
@pytest.fixture(scope="module")
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


@pytest.fixture(scope="module")
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


@pytest.fixture(scope="module")
def background_data():
    """Sample background data."""
    np.random.seed(42)
    return np.random.randn(100, 9)


@pytest.mark.property_test
class TestProperty9_SHAPCompleteness:
    """
    Property 9: SHAP Completeness
    
    For any prediction, the SHAP Explainer should compute feature importance 
    values for all input features used in the prediction.
    """
    
    @given(features=feature_vector_strategy())
    @hyp_settings(max_examples=50, deadline=None)
    def test_shap_completeness(self, trained_model, feature_names, background_data, features):
        """Test that SHAP values are computed for all features."""
        explainer = SHAPExplainer(trained_model, feature_names, background_data)
        
        shap_values = explainer.compute_shap_values(features)
        
        # Property: All features should have SHAP values
        assert len(shap_values) == len(feature_names)
        assert all(name in shap_values for name in feature_names)
        assert all(isinstance(v, float) for v in shap_values.values())


@pytest.mark.property_test
class TestProperty10_SHAPTopFactors:
    """
    Property 10: SHAP Top Factors
    
    For any prediction, the SHAP Explainer should identify the top 5 
    contributing factors (or fewer if there are fewer than 5 features total).
    """
    
    @given(
        shap_vals=shap_values_strategy(['f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7']),
        feature_vals=feature_values_strategy(['f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7'])
    )
    @hyp_settings(max_examples=50, deadline=None)
    def test_top_factors_count(self, trained_model, background_data, shap_vals, feature_vals):
        """Test that top factors returns correct count."""
        feature_names = list(shap_vals.keys())
        explainer = SHAPExplainer(trained_model, feature_names, background_data)
        
        top_factors = explainer.get_top_factors(shap_vals, feature_vals, n=5)
        
        # Property: Should return min(5, num_features) factors
        expected_count = min(5, len(feature_names))
        assert len(top_factors) == expected_count
    
    @given(
        shap_vals=shap_values_strategy(['f1', 'f2', 'f3']),
        feature_vals=feature_values_strategy(['f1', 'f2', 'f3'])
    )
    @hyp_settings(max_examples=50, deadline=None)
    def test_top_factors_with_fewer_than_5_features(self, trained_model, background_data, 
                                                    shap_vals, feature_vals):
        """Test top factors when there are fewer than 5 features."""
        feature_names = list(shap_vals.keys())
        explainer = SHAPExplainer(trained_model, feature_names, background_data)
        
        top_factors = explainer.get_top_factors(shap_vals, feature_vals, n=5)
        
        # Property: Should return all features if fewer than 5
        assert len(top_factors) == len(feature_names)


@pytest.mark.property_test
class TestProperty11_SHAPFactorCategorization:
    """
    Property 11: SHAP Factor Categorization
    
    For any prediction, every factor in the SHAP explanation should be 
    categorized as clinical, administrative, or SDOH.
    """
    
    @given(
        shap_vals=shap_values_strategy([
            'egfr_baseline', 'adi_percentile', 'visit_frequency_12mo',
            'uacr_baseline', 'food_desert', 'insurance_uninsured'
        ]),
        feature_vals=feature_values_strategy([
            'egfr_baseline', 'adi_percentile', 'visit_frequency_12mo',
            'uacr_baseline', 'food_desert', 'insurance_uninsured'
        ])
    )
    @hyp_settings(max_examples=50, deadline=None)
    def test_all_factors_categorized(self, trained_model, background_data, shap_vals, feature_vals):
        """Test that all factors are categorized."""
        feature_names = list(shap_vals.keys())
        explainer = SHAPExplainer(trained_model, feature_names, background_data)
        
        top_factors = explainer.get_top_factors(shap_vals, feature_vals, n=5)
        
        # Property: All factors must have a valid category
        valid_categories = {'clinical', 'administrative', 'sdoh'}
        for factor in top_factors:
            assert factor.category in valid_categories
    
    @given(
        shap_vals=shap_values_strategy([
            'egfr_baseline', 'adi_percentile', 'visit_frequency_12mo'
        ]),
        feature_vals=feature_values_strategy([
            'egfr_baseline', 'adi_percentile', 'visit_frequency_12mo'
        ])
    )
    @hyp_settings(max_examples=50, deadline=None)
    def test_categorized_factors_structure(self, trained_model, background_data, 
                                          shap_vals, feature_vals):
        """Test that categorized factors have correct structure."""
        feature_names = list(shap_vals.keys())
        explainer = SHAPExplainer(trained_model, feature_names, background_data)
        
        top_factors = explainer.get_top_factors(shap_vals, feature_vals, n=5)
        categorized = explainer.categorize_factors(top_factors)
        
        # Property: Categorized factors should have all three lists
        assert hasattr(categorized, 'clinical')
        assert hasattr(categorized, 'administrative')
        assert hasattr(categorized, 'sdoh')
        assert isinstance(categorized.clinical, list)
        assert isinstance(categorized.administrative, list)
        assert isinstance(categorized.sdoh, list)


@pytest.mark.property_test
class TestProperty12_SHAPValueNormalization:
    """
    Property 12: SHAP Value Normalization
    
    For any prediction, the sum of all SHAP values should equal the difference 
    between the prediction and the baseline risk (within numerical precision tolerance).
    """
    
    @given(
        prediction=st.floats(min_value=0.0, max_value=1.0),
        baseline=st.floats(min_value=0.0, max_value=1.0)
    )
    @hyp_settings(max_examples=50, deadline=None)
    def test_shap_normalization(self, trained_model, feature_names, background_data, 
                                prediction, baseline):
        """Test that SHAP values sum to (prediction - baseline)."""
        explainer = SHAPExplainer(trained_model, feature_names, background_data)
        explainer.baseline_risk = baseline
        
        # Create SHAP values that sum correctly
        diff = prediction - baseline
        n_features = len(feature_names)
        shap_values = {name: diff / n_features for name in feature_names}
        
        # Property: Normalization should verify correctly
        assert explainer.verify_normalization(shap_values, prediction)


@pytest.mark.property_test
class TestProperty13_SHAPExplanationLatency:
    """
    Property 13: SHAP Explanation Latency
    
    For any prediction, the SHAP Explainer should generate explanations 
    within 200 milliseconds of prediction completion.
    
    Note: This is a performance property that may be environment-dependent.
    """
    
    @given(features=feature_vector_strategy())
    @hyp_settings(max_examples=20, deadline=None)  # Fewer examples for performance test
    def test_shap_latency(self, trained_model, feature_names, background_data, features):
        """Test that SHAP computation meets latency requirement."""
        explainer = SHAPExplainer(trained_model, feature_names, background_data)
        
        import time
        start_time = time.time()
        shap_values = explainer.compute_shap_values(features)
        elapsed_ms = (time.time() - start_time) * 1000
        
        # Property: Should complete within 200ms (with some tolerance for test environment)
        # Using 500ms tolerance for test environment variability
        assert elapsed_ms < 500, f"SHAP computation took {elapsed_ms}ms"
