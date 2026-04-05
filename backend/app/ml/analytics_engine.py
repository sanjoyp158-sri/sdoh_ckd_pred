"""
ML Analytics Engine for CKD progression prediction.

This module implements the core ML prediction functionality using XGBoost,
including model loading, feature engineering, prediction generation, and
model registry management.
"""

import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import joblib
import numpy as np
import pandas as pd

from app.ml.xgboost_classifier import XGBoostClassifier
from app.models.patient import (
    UnifiedPatientRecord,
    PredictionResult,
    RiskTier,
)
from app.models.ml import ModelMetrics, ModelRegistryEntry

logger = logging.getLogger(__name__)


class ModelRegistry:
    """
    Model registry for versioning and managing ML models.
    
    Handles model storage, retrieval, versioning, and A/B testing configuration.
    """
    
    def __init__(self, registry_path: str = "models/registry"):
        """
        Initialize model registry.
        
        Args:
            registry_path: Path to model registry directory
        """
        self.registry_path = Path(registry_path)
        self.registry_path.mkdir(parents=True, exist_ok=True)
        self._models: Dict[str, ModelRegistryEntry] = {}
        self._production_model_id: Optional[str] = None
        
    def register_model(
        self,
        model_id: str,
        model_version: str,
        model_path: str,
        metrics: ModelMetrics,
        is_production: bool = False,
        previous_version: Optional[str] = None,
    ) -> ModelRegistryEntry:
        """
        Register a new model in the registry.
        
        Args:
            model_id: Unique identifier for the model
            model_version: Version string (e.g., "v1.0.0")
            model_path: Path to serialized model file
            metrics: Model performance metrics
            is_production: Whether this is the production model
            previous_version: Previous model version for rollback
            
        Returns:
            ModelRegistryEntry for the registered model
        """
        entry = ModelRegistryEntry(
            model_id=model_id,
            model_version=model_version,
            model_path=model_path,
            metrics=metrics,
            created_at=datetime.now(),
            is_production=is_production,
            previous_version=previous_version,
            deployment_date=datetime.now() if is_production else None,
        )
        
        self._models[model_id] = entry
        
        if is_production:
            self._production_model_id = model_id
            logger.info(f"Registered production model: {model_id} (version {model_version})")
        else:
            logger.info(f"Registered model: {model_id} (version {model_version})")
            
        return entry
    
    def get_model(self, model_id: str) -> Optional[ModelRegistryEntry]:
        """
        Retrieve a model entry by ID.
        
        Args:
            model_id: Model identifier
            
        Returns:
            ModelRegistryEntry if found, None otherwise
        """
        return self._models.get(model_id)
    
    def get_production_model(self) -> Optional[ModelRegistryEntry]:
        """
        Get the current production model.
        
        Returns:
            ModelRegistryEntry for production model, None if not set
        """
        if self._production_model_id:
            return self._models.get(self._production_model_id)
        return None
    
    def promote_to_production(
        self,
        model_id: str,
        ab_test_percentage: float = 0.0
    ) -> None:
        """
        Promote a model to production.
        
        Args:
            model_id: Model to promote
            ab_test_percentage: Percentage of traffic for A/B testing (0-100)
        """
        if model_id not in self._models:
            raise ValueError(f"Model {model_id} not found in registry")
        
        # Demote current production model
        if self._production_model_id:
            old_model = self._models[self._production_model_id]
            old_model.is_production = False
            logger.info(f"Demoted model {self._production_model_id} from production")
        
        # Promote new model
        new_model = self._models[model_id]
        new_model.is_production = True
        new_model.deployment_date = datetime.now()
        new_model.ab_test_percentage = ab_test_percentage
        self._production_model_id = model_id
        
        logger.info(
            f"Promoted model {model_id} to production "
            f"(A/B test: {ab_test_percentage}%)"
        )
    
    def rollback(self) -> Optional[ModelRegistryEntry]:
        """
        Rollback to the previous model version.
        
        Returns:
            ModelRegistryEntry of the rolled-back model, None if no previous version
        """
        current = self.get_production_model()
        if not current or not current.previous_version:
            logger.warning("No previous version available for rollback")
            return None
        
        # Find the previous version
        previous_model = None
        for model in self._models.values():
            if model.model_version == current.previous_version:
                previous_model = model
                break
        
        if previous_model:
            self.promote_to_production(previous_model.model_id)
            logger.info(f"Rolled back to model {previous_model.model_id}")
            return previous_model
        
        logger.error(f"Previous version {current.previous_version} not found")
        return None
    
    def list_models(self) -> List[ModelRegistryEntry]:
        """
        List all registered models.
        
        Returns:
            List of all ModelRegistryEntry objects
        """
        return list(self._models.values())


class MLAnalyticsEngine:
    """
    ML Analytics Engine for CKD progression prediction.
    
    Handles model loading, feature engineering, prediction generation,
    and model management. Supports model versioning and A/B testing.
    """
    
    def __init__(
        self,
        model_registry: Optional[ModelRegistry] = None,
        model_path: Optional[str] = None,
    ):
        """
        Initialize ML Analytics Engine.
        
        Args:
            model_registry: ModelRegistry instance for model management
            model_path: Path to load a specific model (if not using registry)
        """
        self.model_registry = model_registry or ModelRegistry()
        self._classifier: Optional[XGBoostClassifier] = None
        self._model_version: Optional[str] = None
        self._feature_names: Optional[List[str]] = None
        
        # Load model if path provided
        if model_path:
            self.load_model(model_path)
        else:
            # Try to load production model from registry
            prod_model = self.model_registry.get_production_model()
            if prod_model:
                self.load_model(prod_model.model_path)
                self._model_version = prod_model.model_version
    
    def load_model(self, model_path: str) -> None:
        """
        Load a trained XGBoost model from disk.
        
        Args:
            model_path: Path to serialized model file
            
        Raises:
            FileNotFoundError: If model file doesn't exist
            Exception: If model loading fails
        """
        try:
            model_file = Path(model_path)
            if not model_file.exists():
                raise FileNotFoundError(f"Model file not found: {model_path}")
            
            # Create XGBoostClassifier wrapper and load model
            self._classifier = XGBoostClassifier(model_path=model_path)
            logger.info(f"Loaded model from {model_path}")
            
            # Extract feature names if available
            if hasattr(self._classifier._model, 'feature_names_in_'):
                self._feature_names = list(self._classifier._model.feature_names_in_)
            
        except Exception as e:
            logger.error(f"Failed to load model from {model_path}: {e}")
            raise
    
    def extract_features(self, patient: UnifiedPatientRecord) -> pd.DataFrame:
        """
        Extract features from patient record for prediction.
        
        Implements feature engineering pipeline including:
        - Clinical features (eGFR, UACR, HbA1c, BP, BMI, medications)
        - Administrative features (visit frequency, referrals, insurance)
        - SDOH features (ADI, food desert, housing, transportation)
        - Temporal features (eGFR slope)
        - Interaction features (eGFR × ADI, UACR × food desert)
        
        Args:
            patient: UnifiedPatientRecord with all patient data
            
        Returns:
            DataFrame with single row containing all features
        """
        features = {}
        
        # Clinical features
        features['egfr'] = patient.clinical.egfr
        features['uacr'] = patient.clinical.uacr
        features['hba1c'] = patient.clinical.hba1c
        features['systolic_bp'] = patient.clinical.systolic_bp
        features['diastolic_bp'] = patient.clinical.diastolic_bp
        features['bmi'] = patient.clinical.bmi
        
        # Medication counts by category
        features['medication_count'] = len(patient.clinical.medications)
        features['ace_inhibitor'] = sum(
            1 for m in patient.clinical.medications
            if 'ACE' in m.category and m.active
        )
        features['arb'] = sum(
            1 for m in patient.clinical.medications
            if 'ARB' in m.category and m.active
        )
        features['sglt2_inhibitor'] = sum(
            1 for m in patient.clinical.medications
            if 'SGLT2' in m.category and m.active
        )
        
        # Comorbidity flags
        features['has_diabetes'] = int('diabetes' in [c.lower() for c in patient.clinical.comorbidities])
        features['has_hypertension'] = int('hypertension' in [c.lower() for c in patient.clinical.comorbidities])
        features['has_cvd'] = int('cvd' in [c.lower() for c in patient.clinical.comorbidities])
        
        # Administrative features
        features['visit_frequency_12mo'] = patient.administrative.visit_frequency_12mo
        features['specialist_referral_count'] = len(patient.administrative.specialist_referrals)
        features['insurance_medicare'] = int(patient.administrative.insurance_type == 'Medicare')
        features['insurance_medicaid'] = int(patient.administrative.insurance_type == 'Medicaid')
        features['insurance_commercial'] = int(patient.administrative.insurance_type == 'Commercial')
        features['insurance_uninsured'] = int(patient.administrative.insurance_type == 'Uninsured')
        
        # SDOH features
        features['adi_percentile'] = patient.sdoh.adi_percentile
        features['food_desert'] = int(patient.sdoh.food_desert)
        features['housing_stability_score'] = patient.sdoh.housing_stability_score
        features['transportation_access_score'] = patient.sdoh.transportation_access_score
        
        # Temporal features - eGFR slope
        features['egfr_slope'] = self._calculate_egfr_slope(patient.clinical.egfr_history)
        
        # Time since diagnosis (in years)
        years_since_diagnosis = (
            datetime.now() - patient.clinical.diagnosis_date
        ).days / 365.25
        features['years_since_diagnosis'] = years_since_diagnosis
        
        # Demographic features (age, sex - NOT race/ethnicity)
        features['age'] = patient.demographics.age
        features['sex_male'] = int(patient.demographics.sex == 'M')
        features['sex_female'] = int(patient.demographics.sex == 'F')
        
        # Interaction features
        features['egfr_x_adi'] = features['egfr'] * features['adi_percentile']
        features['uacr_x_food_desert'] = features['uacr'] * features['food_desert']
        
        # Convert to DataFrame
        df = pd.DataFrame([features])
        
        return df
    
    def _calculate_egfr_slope(
        self,
        egfr_history: List[Tuple[datetime, float]]
    ) -> float:
        """
        Calculate eGFR slope from historical measurements.
        
        Uses linear regression on eGFR values over time.
        
        Args:
            egfr_history: List of (date, eGFR) tuples
            
        Returns:
            eGFR slope in mL/min/1.73m² per year
        """
        if len(egfr_history) < 2:
            return 0.0
        
        # Sort by date
        sorted_history = sorted(egfr_history, key=lambda x: x[0])
        
        # Convert dates to days since first measurement
        first_date = sorted_history[0][0]
        days = [(date - first_date).days for date, _ in sorted_history]
        egfr_values = [egfr for _, egfr in sorted_history]
        
        # Simple linear regression
        days_array = np.array(days)
        egfr_array = np.array(egfr_values)
        
        # Calculate slope (change per day)
        if len(days) > 1:
            slope_per_day = np.polyfit(days_array, egfr_array, 1)[0]
            # Convert to change per year
            slope_per_year = slope_per_day * 365.25
            return float(slope_per_year)
        
        return 0.0
    
    def predict_progression_risk(
        self,
        patient: UnifiedPatientRecord
    ) -> PredictionResult:
        """
        Generate CKD progression risk prediction for a patient.
        
        Predicts probability of progression from Stage 2-3 to Stage 4-5
        within 24 months. Meets 500ms latency requirement.
        
        Args:
            patient: UnifiedPatientRecord with complete patient data
            
        Returns:
            PredictionResult with risk score, tier, and metadata
            
        Raises:
            ValueError: If model is not loaded
            Exception: If prediction fails
        """
        if self._classifier is None:
            raise ValueError("Model not loaded. Call load_model() first.")
        
        start_time = time.time()
        
        try:
            # Extract features
            features_df = self.extract_features(patient)
            
            # Generate prediction (probability of progression) with 500ms timeout
            probabilities = self._classifier.predict_proba(
                features_df,
                timeout_ms=500
            )
            risk_score = float(probabilities[0, 1])
            
            # Determine risk tier
            risk_tier = self._classify_risk_tier(risk_score)
            
            # Calculate processing time
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            result = PredictionResult(
                patient_id=patient.patient_id,
                risk_score=risk_score,
                risk_tier=risk_tier,
                prediction_date=datetime.now(),
                model_version=self._model_version or "unknown",
                processing_time_ms=processing_time_ms,
            )
            
            logger.info(
                f"Prediction for patient {patient.patient_id}: "
                f"risk_score={risk_score:.3f}, tier={risk_tier.value}, "
                f"time={processing_time_ms}ms"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Prediction failed for patient {patient.patient_id}: {e}")
            raise
    
    def _classify_risk_tier(self, risk_score: float) -> RiskTier:
        """
        Classify risk score into risk tier.
        
        Args:
            risk_score: Risk score between 0 and 1
            
        Returns:
            RiskTier (HIGH, MODERATE, or LOW)
        """
        if risk_score > 0.65:
            return RiskTier.HIGH
        elif risk_score >= 0.35:
            return RiskTier.MODERATE
        else:
            return RiskTier.LOW
    
    def get_feature_names(self) -> List[str]:
        """
        Get list of feature names used by the model.
        
        Returns:
            List of feature names
        """
        if self._feature_names:
            return self._feature_names
        
        # Return default feature list if not available from model
        return [
            'egfr', 'uacr', 'hba1c', 'systolic_bp', 'diastolic_bp', 'bmi',
            'medication_count', 'ace_inhibitor', 'arb', 'sglt2_inhibitor',
            'has_diabetes', 'has_hypertension', 'has_cvd',
            'visit_frequency_12mo', 'specialist_referral_count',
            'insurance_medicare', 'insurance_medicaid', 'insurance_commercial', 'insurance_uninsured',
            'adi_percentile', 'food_desert', 'housing_stability_score', 'transportation_access_score',
            'egfr_slope', 'years_since_diagnosis',
            'age', 'sex_male', 'sex_female',
            'egfr_x_adi', 'uacr_x_food_desert',
        ]
