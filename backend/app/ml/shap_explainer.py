"""
SHAP Explainer for CKD progression predictions.
Provides interpretable explanations using TreeSHAP.
"""

import time
import numpy as np
import shap
from typing import List, Dict, Optional
from dataclasses import dataclass

from app.models.patient import (
    UnifiedPatientRecord,
    Factor,
    CategorizedFactors,
    SHAPExplanation
)
from app.core.config import settings


class SHAPExplainer:
    """
    SHAP-based explainability for XGBoost predictions.
    Uses TreeSHAP for efficient computation.
    """
    
    def __init__(self, model, feature_names: List[str], background_data: Optional[np.ndarray] = None):
        """
        Initialize SHAP explainer.
        
        Args:
            model: Trained XGBoost model
            feature_names: List of feature names in order
            background_data: Background dataset for SHAP (1000 samples recommended)
        """
        self.model = model
        self.feature_names = feature_names
        self.background_data = background_data
        
        # Create TreeExplainer (optimized for tree-based models)
        if background_data is not None:
            self.explainer = shap.TreeExplainer(model, background_data)
        else:
            self.explainer = shap.TreeExplainer(model)
        
        # Calculate baseline risk (expected value)
        self.baseline_risk = float(self.explainer.expected_value)
    
    def compute_shap_values(self, features: np.ndarray) -> Dict[str, float]:
        """
        Compute SHAP values for all features.
        
        Args:
            features: Feature vector (1D array)
        
        Returns:
            Dictionary mapping feature names to SHAP values
        """
        # Reshape if needed
        if features.ndim == 1:
            features = features.reshape(1, -1)
        
        # Compute SHAP values
        shap_values = self.explainer.shap_values(features)
        
        # If multiple outputs, take first (binary classification)
        if isinstance(shap_values, list):
            shap_values = shap_values[0]
        
        # Flatten if needed
        if shap_values.ndim > 1:
            shap_values = shap_values.flatten()
        
        # Create dictionary
        shap_dict = {
            name: float(value) 
            for name, value in zip(self.feature_names, shap_values)
        }
        
        return shap_dict
    
    def get_top_factors(self, shap_values: Dict[str, float], 
                       feature_values: Dict[str, any],
                       n: int = 5) -> List[Factor]:
        """
        Get top N contributing factors by absolute SHAP value.
        
        Args:
            shap_values: Dictionary of feature -> SHAP value
            feature_values: Dictionary of feature -> actual value
            n: Number of top factors to return
        
        Returns:
            List of Factor objects sorted by importance
        """
        # Sort by absolute SHAP value
        sorted_features = sorted(
            shap_values.items(),
            key=lambda x: abs(x[1]),
            reverse=True
        )
        
        # Take top N
        top_features = sorted_features[:n]
        
        # Create Factor objects
        factors = []
        for feature_name, shap_value in top_features:
            feature_value = feature_values.get(feature_name, None)
            
            # Determine category
            category = self._categorize_feature(feature_name)
            
            # Determine direction
            direction = "increases_risk" if shap_value > 0 else "decreases_risk"
            
            factor = Factor(
                feature_name=feature_name,
                feature_value=feature_value,
                shap_value=shap_value,
                category=category,
                direction=direction
            )
            factors.append(factor)
        
        return factors
    
    def categorize_factors(self, factors: List[Factor]) -> CategorizedFactors:
        """
        Categorize factors by type (clinical, administrative, SDOH).
        
        Args:
            factors: List of Factor objects
        
        Returns:
            CategorizedFactors object
        """
        clinical = []
        administrative = []
        sdoh = []
        
        for factor in factors:
            if factor.category == "clinical":
                clinical.append(factor)
            elif factor.category == "administrative":
                administrative.append(factor)
            elif factor.category == "sdoh":
                sdoh.append(factor)
        
        return CategorizedFactors(
            clinical=clinical,
            administrative=administrative,
            sdoh=sdoh
        )
    
    def _categorize_feature(self, feature_name: str) -> str:
        """
        Categorize a feature as clinical, administrative, or SDOH.
        
        Args:
            feature_name: Name of the feature
        
        Returns:
            Category string
        """
        # Clinical features
        clinical_keywords = [
            'egfr', 'uacr', 'hba1c', 'bp', 'bmi', 'medication',
            'diabetes', 'hypertension', 'chf', 'charlson', 'age', 'sex'
        ]
        
        # Administrative features
        admin_keywords = [
            'visit', 'referral', 'insurance', 'ed_visits'
        ]
        
        # SDOH features
        sdoh_keywords = [
            'adi', 'food_desert', 'housing', 'transportation',
            'poverty', 'income', 'unemployment', 'education',
            'linguistic', 'walkability', 'rural'
        ]
        
        feature_lower = feature_name.lower()
        
        for keyword in clinical_keywords:
            if keyword in feature_lower:
                return "clinical"
        
        for keyword in admin_keywords:
            if keyword in feature_lower:
                return "administrative"
        
        for keyword in sdoh_keywords:
            if keyword in feature_lower:
                return "sdoh"
        
        # Default to clinical if unknown
        return "clinical"
    
    def explain_prediction(self, 
                          patient: UnifiedPatientRecord,
                          prediction: float,
                          features: np.ndarray,
                          feature_values: Dict[str, any]) -> SHAPExplanation:
        """
        Generate complete SHAP explanation for a prediction.
        
        Args:
            patient: Patient record
            prediction: Risk score (0-1)
            features: Feature vector used for prediction
            feature_values: Dictionary of feature name -> value
        
        Returns:
            SHAPExplanation object
        """
        start_time = time.time()
        
        # Compute SHAP values
        shap_values = self.compute_shap_values(features)
        
        # Get top 5 factors
        top_factors = self.get_top_factors(shap_values, feature_values, n=5)
        
        # Categorize factors
        categorized_factors = self.categorize_factors(top_factors)
        
        # Calculate computation time
        computation_time_ms = int((time.time() - start_time) * 1000)
        
        # Verify latency requirement (200ms)
        if computation_time_ms > settings.SHAP_TIMEOUT_MS:
            import logging
            logging.warning(
                f"SHAP computation exceeded timeout: {computation_time_ms}ms > {settings.SHAP_TIMEOUT_MS}ms"
            )
        
        return SHAPExplanation(
            patient_id=patient.patient_id,
            baseline_risk=self.baseline_risk,
            prediction=prediction,
            shap_values=shap_values,
            top_factors=top_factors,
            categorized_factors=categorized_factors,
            computation_time_ms=computation_time_ms
        )
    
    def verify_normalization(self, shap_values: Dict[str, float], 
                            prediction: float) -> bool:
        """
        Verify that SHAP values sum to (prediction - baseline).
        
        Args:
            shap_values: Dictionary of SHAP values
            prediction: Prediction score
        
        Returns:
            True if normalized correctly (within tolerance)
        """
        shap_sum = sum(shap_values.values())
        expected_sum = prediction - self.baseline_risk
        
        # Allow small numerical tolerance
        tolerance = 1e-5
        return abs(shap_sum - expected_sum) < tolerance
