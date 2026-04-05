"""
Model validation tests for CKD Early Detection System.

Task 20.3: Run model validation tests
- Verify model AUROC >= 0.87 on test set (Requirement 2.2)
- Verify fairness metrics across subgroups (disparity <= 0.05) (Requirements 10.1-10.4)
- Verify race/ethnicity not used as features (Requirement 10.5)

Note: These tests require a trained ML model. If model is not available,
tests will be skipped with appropriate messages.
"""

import pytest
import os
from pathlib import Path
from unittest.mock import Mock, patch
import numpy as np

from app.ml.analytics_engine import MLAnalyticsEngine
from app.ml.xgboost_classifier import XGBoostClassifier


class TestModelPerformance:
    """Test model performance requirements."""
    
    @pytest.fixture
    def model_path(self):
        """Get path to trained model."""
        # Check multiple possible locations
        possible_paths = [
            Path("models/registry/xgboost_ckd_model.json"),
            Path("../models/registry/xgboost_ckd_model.json"),
            Path("../../models/registry/xgboost_ckd_model.json"),
        ]
        
        for path in possible_paths:
            if path.exists():
                return str(path)
        
        return None
    
    @pytest.fixture
    def test_data_path(self):
        """Get path to test dataset."""
        possible_paths = [
            Path("data/processed/test_set.csv"),
            Path("../data/processed/test_set.csv"),
            Path("../../data/processed/test_set.csv"),
        ]
        
        for path in possible_paths:
            if path.exists():
                return str(path)
        
        return None
    
    def test_model_auroc_requirement(self, model_path, test_data_path):
        """
        Test Requirement 2.2: Model AUROC >= 0.87 on test set
        
        This test requires:
        - Trained XGBoost model file
        - Test dataset with ground truth labels
        """
        if model_path is None:
            pytest.skip("Trained model not found. Run model training pipeline first.")
        
        if test_data_path is None:
            pytest.skip("Test dataset not found. Run data preparation pipeline first.")
        
        # Load model
        classifier = XGBoostClassifier()
        classifier.load_model(model_path)
        
        # Load test data
        import pandas as pd
        test_data = pd.read_csv(test_data_path)
        
        # Separate features and labels
        # Assuming 'progression_24mo' is the target variable
        if 'progression_24mo' not in test_data.columns:
            pytest.skip("Test data missing 'progression_24mo' target variable")
        
        y_true = test_data['progression_24mo'].values
        
        # Remove target and non-feature columns
        feature_cols = [col for col in test_data.columns 
                       if col not in ['progression_24mo', 'patient_id', 'race', 'ethnicity']]
        X_test = test_data[feature_cols]
        
        # Generate predictions
        y_pred_proba = classifier.predict_proba(X_test)
        
        # Calculate AUROC
        from sklearn.metrics import roc_auc_score
        auroc = roc_auc_score(y_true, y_pred_proba)
        
        assert auroc >= 0.87, f"Model AUROC {auroc:.4f} is below 0.87 requirement"
        
        print(f"✓ Model AUROC: {auroc:.4f} (>= 0.87 requirement)")
        
        return auroc
    
    def test_model_performance_metrics(self, model_path, test_data_path):
        """
        Test comprehensive model performance metrics.
        
        Validates: AUROC, sensitivity, specificity, PPV, NPV
        """
        if model_path is None or test_data_path is None:
            pytest.skip("Model or test data not available")
        
        # Load model and data
        classifier = XGBoostClassifier()
        classifier.load_model(model_path)
        
        import pandas as pd
        test_data = pd.read_csv(test_data_path)
        
        y_true = test_data['progression_24mo'].values
        feature_cols = [col for col in test_data.columns 
                       if col not in ['progression_24mo', 'patient_id', 'race', 'ethnicity']]
        X_test = test_data[feature_cols]
        
        # Generate predictions
        y_pred_proba = classifier.predict_proba(X_test)
        y_pred = (y_pred_proba >= 0.5).astype(int)
        
        # Calculate metrics
        from sklearn.metrics import (
            roc_auc_score,
            confusion_matrix,
            precision_score,
            recall_score
        )
        
        auroc = roc_auc_score(y_true, y_pred_proba)
        tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
        
        sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
        ppv = tp / (tp + fp) if (tp + fp) > 0 else 0
        npv = tn / (tn + fn) if (tn + fn) > 0 else 0
        
        print(f"✓ Model Performance Metrics:")
        print(f"  - AUROC: {auroc:.4f}")
        print(f"  - Sensitivity (Recall): {sensitivity:.4f}")
        print(f"  - Specificity: {specificity:.4f}")
        print(f"  - PPV (Precision): {ppv:.4f}")
        print(f"  - NPV: {npv:.4f}")
        
        # Basic sanity checks
        assert 0.5 <= auroc <= 1.0, "AUROC should be between 0.5 and 1.0"
        assert 0.0 <= sensitivity <= 1.0, "Sensitivity should be between 0 and 1"
        assert 0.0 <= specificity <= 1.0, "Specificity should be between 0 and 1"


class TestModelFairness:
    """Test model fairness requirements."""
    
    @pytest.fixture
    def model_path(self):
        """Get path to trained model."""
        possible_paths = [
            Path("models/registry/xgboost_ckd_model.json"),
            Path("../models/registry/xgboost_ckd_model.json"),
            Path("../../models/registry/xgboost_ckd_model.json"),
        ]
        
        for path in possible_paths:
            if path.exists():
                return str(path)
        
        return None
    
    @pytest.fixture
    def test_data_path(self):
        """Get path to test dataset with demographic information."""
        possible_paths = [
            Path("data/processed/test_set.csv"),
            Path("../data/processed/test_set.csv"),
            Path("../../data/processed/test_set.csv"),
        ]
        
        for path in possible_paths:
            if path.exists():
                return str(path)
        
        return None
    
    def test_fairness_across_subgroups(self, model_path, test_data_path):
        """
        Test Requirements 10.1-10.4: Fairness across racial/ethnic subgroups
        
        Validates:
        - AUROC within 0.05 across all subgroups
        - Performance monitored separately for each subgroup
        - Disparity flagging when exceeds 0.05
        """
        if model_path is None or test_data_path is None:
            pytest.skip("Model or test data not available")
        
        # Load model and data
        classifier = XGBoostClassifier()
        classifier.load_model(model_path)
        
        import pandas as pd
        test_data = pd.read_csv(test_data_path)
        
        # Check if demographic data is available
        if 'race' not in test_data.columns:
            pytest.skip("Test data missing 'race' column for fairness analysis")
        
        y_true = test_data['progression_24mo'].values
        feature_cols = [col for col in test_data.columns 
                       if col not in ['progression_24mo', 'patient_id', 'race', 'ethnicity']]
        X_test = test_data[feature_cols]
        
        # Generate predictions
        y_pred_proba = classifier.predict_proba(X_test)
        
        # Calculate AUROC for each subgroup
        from sklearn.metrics import roc_auc_score
        
        subgroups = ['White', 'Black', 'Hispanic', 'Asian', 'Other']
        subgroup_aurocs = {}
        
        for subgroup in subgroups:
            mask = test_data['race'] == subgroup
            if mask.sum() < 10:  # Need at least 10 samples
                print(f"  - {subgroup}: Insufficient data (n={mask.sum()})")
                continue
            
            y_true_subgroup = y_true[mask]
            y_pred_subgroup = y_pred_proba[mask]
            
            # Check if we have both classes
            if len(np.unique(y_true_subgroup)) < 2:
                print(f"  - {subgroup}: Only one class present (n={mask.sum()})")
                continue
            
            auroc = roc_auc_score(y_true_subgroup, y_pred_subgroup)
            subgroup_aurocs[subgroup] = auroc
            print(f"  - {subgroup}: AUROC = {auroc:.4f} (n={mask.sum()})")
        
        if len(subgroup_aurocs) < 2:
            pytest.skip("Insufficient subgroup data for fairness analysis")
        
        # Calculate disparity
        auroc_values = list(subgroup_aurocs.values())
        max_auroc = max(auroc_values)
        min_auroc = min(auroc_values)
        disparity = max_auroc - min_auroc
        
        print(f"\n✓ Fairness Analysis:")
        print(f"  - Max AUROC: {max_auroc:.4f}")
        print(f"  - Min AUROC: {min_auroc:.4f}")
        print(f"  - Disparity: {disparity:.4f}")
        
        assert disparity <= 0.05, (
            f"AUROC disparity {disparity:.4f} exceeds 0.05 threshold. "
            f"Model should be flagged for retraining."
        )
        
        print(f"  - Disparity <= 0.05 requirement: PASSED")
    
    def test_race_ethnicity_not_used_as_features(self, model_path):
        """
        Test Requirement 10.5: Race and ethnicity not used as direct features
        
        Validates that the model does not use race or ethnicity as input features.
        """
        if model_path is None:
            pytest.skip("Model not available")
        
        # Load model
        classifier = XGBoostClassifier()
        classifier.load_model(model_path)
        
        # Get feature names
        feature_names = classifier.get_feature_names()
        
        # Check that race and ethnicity are not in features
        assert 'race' not in feature_names, "Race should not be used as a model feature"
        assert 'ethnicity' not in feature_names, "Ethnicity should not be used as a model feature"
        
        # Also check for variations
        race_related = [f for f in feature_names if 'race' in f.lower()]
        ethnicity_related = [f for f in feature_names if 'ethnic' in f.lower()]
        
        assert len(race_related) == 0, f"Found race-related features: {race_related}"
        assert len(ethnicity_related) == 0, f"Found ethnicity-related features: {ethnicity_related}"
        
        print(f"✓ Race/ethnicity exclusion validated:")
        print(f"  - Total features: {len(feature_names)}")
        print(f"  - Race-related features: 0")
        print(f"  - Ethnicity-related features: 0")
        print(f"  - Requirement 10.5: PASSED")
    
    def test_fairness_metrics_completeness(self, model_path, test_data_path):
        """
        Test Requirement 10.4: Quarterly fairness report completeness
        
        Validates that fairness reports include all required metrics:
        - Sensitivity
        - Specificity
        - Positive Predictive Value (PPV)
        """
        if model_path is None or test_data_path is None:
            pytest.skip("Model or test data not available")
        
        # Load model and data
        classifier = XGBoostClassifier()
        classifier.load_model(model_path)
        
        import pandas as pd
        test_data = pd.read_csv(test_data_path)
        
        if 'race' not in test_data.columns:
            pytest.skip("Test data missing 'race' column")
        
        y_true = test_data['progression_24mo'].values
        feature_cols = [col for col in test_data.columns 
                       if col not in ['progression_24mo', 'patient_id', 'race', 'ethnicity']]
        X_test = test_data[feature_cols]
        
        # Generate predictions
        y_pred_proba = classifier.predict_proba(X_test)
        y_pred = (y_pred_proba >= 0.5).astype(int)
        
        # Calculate metrics for each subgroup
        from sklearn.metrics import confusion_matrix
        
        subgroups = ['White', 'Black', 'Hispanic', 'Asian', 'Other']
        fairness_report = {}
        
        print("\n✓ Fairness Metrics by Subgroup:")
        
        for subgroup in subgroups:
            mask = test_data['race'] == subgroup
            if mask.sum() < 10:
                continue
            
            y_true_subgroup = y_true[mask]
            y_pred_subgroup = y_pred[mask]
            
            if len(np.unique(y_true_subgroup)) < 2:
                continue
            
            tn, fp, fn, tp = confusion_matrix(y_true_subgroup, y_pred_subgroup).ravel()
            
            sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0
            specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
            ppv = tp / (tp + fp) if (tp + fp) > 0 else 0
            
            fairness_report[subgroup] = {
                'sensitivity': sensitivity,
                'specificity': specificity,
                'ppv': ppv,
                'n': mask.sum()
            }
            
            print(f"  {subgroup} (n={mask.sum()}):")
            print(f"    - Sensitivity: {sensitivity:.4f}")
            print(f"    - Specificity: {specificity:.4f}")
            print(f"    - PPV: {ppv:.4f}")
        
        # Verify report completeness
        assert len(fairness_report) > 0, "Fairness report should contain at least one subgroup"
        
        for subgroup, metrics in fairness_report.items():
            assert 'sensitivity' in metrics, f"Missing sensitivity for {subgroup}"
            assert 'specificity' in metrics, f"Missing specificity for {subgroup}"
            assert 'ppv' in metrics, f"Missing PPV for {subgroup}"
        
        print(f"\n  - Fairness report completeness: PASSED")


class TestModelFeatures:
    """Test model feature engineering and usage."""
    
    def test_feature_categories_present(self):
        """
        Test that model uses features from all three categories:
        - Clinical features
        - Administrative features
        - SDOH features
        """
        # This test can run without a trained model
        # It validates the feature engineering pipeline
        
        from app.ml.analytics_engine import MLAnalyticsEngine
        
        engine = MLAnalyticsEngine()
        feature_names = engine.get_expected_features()
        
        # Check for clinical features
        clinical_features = [f for f in feature_names if any(
            term in f.lower() for term in ['egfr', 'uacr', 'hba1c', 'bp', 'bmi']
        )]
        
        # Check for administrative features
        admin_features = [f for f in feature_names if any(
            term in f.lower() for term in ['visit', 'referral', 'insurance']
        )]
        
        # Check for SDOH features
        sdoh_features = [f for f in feature_names if any(
            term in f.lower() for term in ['adi', 'food', 'housing', 'transport']
        )]
        
        assert len(clinical_features) > 0, "Model should use clinical features"
        assert len(admin_features) > 0, "Model should use administrative features"
        assert len(sdoh_features) > 0, "Model should use SDOH features"
        
        print(f"✓ Feature categories validated:")
        print(f"  - Clinical features: {len(clinical_features)}")
        print(f"  - Administrative features: {len(admin_features)}")
        print(f"  - SDOH features: {len(sdoh_features)}")
        print(f"  - Total features: {len(feature_names)}")


class TestModelDeploymentReadiness:
    """Test model deployment readiness."""
    
    def test_model_file_exists(self):
        """
        Test that model file exists in expected location.
        """
        possible_paths = [
            Path("models/registry/xgboost_ckd_model.json"),
            Path("../models/registry/xgboost_ckd_model.json"),
            Path("../../models/registry/xgboost_ckd_model.json"),
        ]
        
        model_found = any(path.exists() for path in possible_paths)
        
        if not model_found:
            pytest.skip(
                "Model file not found. This is expected if model training hasn't been run yet. "
                "To train the model, run: python ckd_pipeline/step3_train_model.py"
            )
        
        print("✓ Model file found and ready for deployment")
    
    def test_model_version_tracking(self):
        """
        Test that model versioning is configured.
        """
        from app.ml.analytics_engine import MLAnalyticsEngine
        
        engine = MLAnalyticsEngine()
        
        # Check that model version tracking is available
        assert hasattr(engine, 'model_version'), "Model should have version tracking"
        
        print(f"✓ Model version tracking configured: {engine.model_version}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
