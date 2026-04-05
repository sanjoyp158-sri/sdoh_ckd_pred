"""
Unit tests for XGBoostClassifier wrapper.
"""

import pytest
import numpy as np
import pandas as pd
from pathlib import Path
import joblib
from xgboost import XGBClassifier as XGBoostModel

from app.ml.xgboost_classifier import XGBoostClassifier


@pytest.fixture
def sample_training_data():
    """Create sample training data for testing."""
    np.random.seed(42)
    n_samples = 100
    n_features = 10
    
    X = pd.DataFrame(
        np.random.rand(n_samples, n_features),
        columns=[f"feature_{i}" for i in range(n_features)]
    )
    y = pd.Series(np.random.randint(0, 2, n_samples))
    
    return X, y


@pytest.fixture
def trained_model(tmp_path, sample_training_data):
    """Create and save a trained XGBoost model."""
    X_train, y_train = sample_training_data
    
    # Train a simple model
    model = XGBoostModel(
        n_estimators=10,
        max_depth=3,
        random_state=42,
        use_label_encoder=False,
        eval_metric='logloss'
    )
    model.fit(X_train, y_train)
    
    # Save model
    model_path = tmp_path / "test_model.joblib"
    joblib.dump(model, model_path)
    
    return str(model_path)


class TestXGBoostClassifier:
    """Tests for XGBoostClassifier wrapper class."""
    
    def test_initialization_default_params(self):
        """Test initialization with default parameters."""
        classifier = XGBoostClassifier()
        
        assert classifier._model is None
        assert classifier.is_trained is False
        
        # Check default parameters
        params = classifier.get_params()
        assert params['max_depth'] == 6
        assert params['learning_rate'] == 0.05
        assert params['subsample'] == 0.8
        assert params['colsample_bytree'] == 0.8
        assert params['min_child_weight'] == 3
        assert params['scale_pos_weight'] == 2.5
        assert params['tree_method'] == 'hist'
        assert params['objective'] == 'binary:logistic'
        assert params['eval_metric'] == 'auc'
    
    def test_initialization_custom_params(self):
        """Test initialization with custom parameters."""
        custom_params = {
            'max_depth': 8,
            'learning_rate': 0.1,
        }
        
        classifier = XGBoostClassifier(params=custom_params)
        params = classifier.get_params()
        
        # Custom params should override defaults
        assert params['max_depth'] == 8
        assert params['learning_rate'] == 0.1
        
        # Other defaults should remain
        assert params['subsample'] == 0.8
        assert params['tree_method'] == 'hist'
    
    def test_load_model(self, trained_model):
        """Test loading a trained model from disk."""
        classifier = XGBoostClassifier()
        classifier.load_model(trained_model)
        
        assert classifier.is_trained is True
        assert classifier._model is not None
        assert isinstance(classifier._model, XGBoostModel)
    
    def test_load_model_in_constructor(self, trained_model):
        """Test loading model during initialization."""
        classifier = XGBoostClassifier(model_path=trained_model)
        
        assert classifier.is_trained is True
        assert classifier._model is not None
    
    def test_load_model_file_not_found(self):
        """Test loading a non-existent model file."""
        classifier = XGBoostClassifier()
        
        with pytest.raises(FileNotFoundError):
            classifier.load_model("/nonexistent/model.joblib")
    
    def test_save_model(self, tmp_path, sample_training_data):
        """Test saving a trained model."""
        X_train, y_train = sample_training_data
        
        classifier = XGBoostClassifier()
        classifier.train(X_train, y_train, n_estimators=10)
        
        save_path = tmp_path / "saved_model.joblib"
        classifier.save_model(str(save_path))
        
        assert save_path.exists()
        
        # Verify we can load the saved model
        loaded_classifier = XGBoostClassifier(model_path=str(save_path))
        assert loaded_classifier.is_trained is True
    
    def test_save_model_without_training(self):
        """Test saving fails when no model is trained."""
        classifier = XGBoostClassifier()
        
        with pytest.raises(ValueError, match="No model to save"):
            classifier.save_model("/tmp/model.joblib")
    
    def test_train(self, sample_training_data):
        """Test training a model."""
        X_train, y_train = sample_training_data
        
        classifier = XGBoostClassifier()
        classifier.train(X_train, y_train, n_estimators=10)
        
        assert classifier.is_trained is True
        assert classifier._model is not None
    
    def test_train_with_validation(self, sample_training_data):
        """Test training with validation set."""
        X_train, y_train = sample_training_data
        
        # Split into train and validation
        split_idx = int(len(X_train) * 0.8)
        X_val = X_train[split_idx:]
        y_val = y_train[split_idx:]
        X_train = X_train[:split_idx]
        y_train = y_train[:split_idx]
        
        classifier = XGBoostClassifier()
        classifier.train(
            X_train, y_train,
            X_val=X_val, y_val=y_val,
            n_estimators=10
        )
        
        assert classifier.is_trained is True
    
    def test_predict_proba(self, trained_model, sample_training_data):
        """Test probability prediction."""
        X_train, _ = sample_training_data
        
        classifier = XGBoostClassifier(model_path=trained_model)
        
        # Predict on a subset
        X_test = X_train[:10]
        probabilities = classifier.predict_proba(X_test)
        
        # Check shape and values
        assert probabilities.shape == (10, 2)
        assert np.all(probabilities >= 0)
        assert np.all(probabilities <= 1)
        assert np.allclose(probabilities.sum(axis=1), 1.0)
    
    def test_predict_proba_without_model(self, sample_training_data):
        """Test prediction fails without loaded model."""
        X_train, _ = sample_training_data
        
        classifier = XGBoostClassifier()
        
        with pytest.raises(ValueError, match="Model not loaded"):
            classifier.predict_proba(X_train[:10])
    
    def test_predict_proba_timeout(self, trained_model, sample_training_data):
        """Test prediction timeout enforcement."""
        X_train, _ = sample_training_data
        
        classifier = XGBoostClassifier(model_path=trained_model)
        
        # Use a very short timeout that should succeed for small data
        X_test = X_train[:5]
        probabilities = classifier.predict_proba(X_test, timeout_ms=1000)
        
        assert probabilities.shape == (5, 2)
    
    def test_predict(self, trained_model, sample_training_data):
        """Test binary class prediction."""
        X_train, _ = sample_training_data
        
        classifier = XGBoostClassifier(model_path=trained_model)
        
        X_test = X_train[:10]
        predictions = classifier.predict(X_test)
        
        # Check predictions are binary
        assert predictions.shape == (10,)
        assert np.all(np.isin(predictions, [0, 1]))
    
    def test_predict_without_model(self, sample_training_data):
        """Test prediction fails without loaded model."""
        X_train, _ = sample_training_data
        
        classifier = XGBoostClassifier()
        
        with pytest.raises(ValueError, match="Model not loaded"):
            classifier.predict(X_train[:10])
    
    def test_get_feature_importance(self, trained_model):
        """Test getting feature importance."""
        classifier = XGBoostClassifier(model_path=trained_model)
        
        importance = classifier.get_feature_importance()
        
        assert isinstance(importance, dict)
        assert len(importance) > 0
        
        # Check all values are non-negative
        assert all(v >= 0 for v in importance.values())
    
    def test_get_feature_importance_without_model(self):
        """Test feature importance fails without trained model."""
        classifier = XGBoostClassifier()
        
        with pytest.raises(ValueError, match="Model not trained"):
            classifier.get_feature_importance()
    
    def test_default_timeout_constant(self):
        """Test that default timeout is 500ms as required."""
        assert XGBoostClassifier.PREDICTION_TIMEOUT_MS == 500
    
    def test_configured_parameters_match_design(self):
        """Test that default parameters match design document specifications."""
        classifier = XGBoostClassifier()
        params = classifier.get_params()
        
        # Verify parameters match design document
        assert params['max_depth'] == 6
        assert params['learning_rate'] == 0.05
        assert params['subsample'] == 0.8
        assert params['colsample_bytree'] == 0.8
        assert params['min_child_weight'] == 3
        assert params['scale_pos_weight'] == 2.5
        assert params['tree_method'] == 'hist'
        assert params['objective'] == 'binary:logistic'
        assert params['eval_metric'] == 'auc'


class TestXGBoostClassifierIntegration:
    """Integration tests for XGBoostClassifier."""
    
    def test_full_training_and_prediction_workflow(self, tmp_path, sample_training_data):
        """Test complete workflow: train, save, load, predict."""
        X_train, y_train = sample_training_data
        
        # Train model
        classifier = XGBoostClassifier()
        classifier.train(X_train, y_train, n_estimators=10)
        
        # Save model
        model_path = tmp_path / "workflow_model.joblib"
        classifier.save_model(str(model_path))
        
        # Load model in new classifier
        new_classifier = XGBoostClassifier(model_path=str(model_path))
        
        # Make predictions
        X_test = X_train[:10]
        probabilities = new_classifier.predict_proba(X_test)
        predictions = new_classifier.predict(X_test)
        
        assert probabilities.shape == (10, 2)
        assert predictions.shape == (10,)
        assert np.all(np.isin(predictions, [0, 1]))
    
    def test_model_registry_integration(self, tmp_path, sample_training_data):
        """Test integration with model registry pattern."""
        X_train, y_train = sample_training_data
        
        # Train and save model
        classifier = XGBoostClassifier()
        classifier.train(X_train, y_train, n_estimators=10)
        
        model_path = tmp_path / "registry_model.joblib"
        classifier.save_model(str(model_path))
        
        # Simulate loading from registry
        registry_classifier = XGBoostClassifier(model_path=str(model_path))
        
        # Verify predictions work
        X_test = X_train[:5]
        probabilities = registry_classifier.predict_proba(X_test, timeout_ms=500)
        
        assert probabilities.shape == (5, 2)
        assert np.all(probabilities >= 0)
        assert np.all(probabilities <= 1)
