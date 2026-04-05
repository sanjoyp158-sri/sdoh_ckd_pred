"""
XGBoost Classifier wrapper for CKD progression prediction.

This module provides a wrapper around XGBoost with configured parameters
optimized for CKD progression prediction. Handles model training, loading,
and prediction with timeout enforcement.
"""

import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import numpy as np
import pandas as pd
from xgboost import XGBClassifier as XGBoostModel
import joblib

logger = logging.getLogger(__name__)


class XGBoostClassifier:
    """
    XGBoost classifier wrapper for CKD progression prediction.
    
    Provides a configured XGBoost model with optimized hyperparameters
    for predicting CKD progression from Stage 2-3 to Stage 4-5 within
    24 months. Includes timeout enforcement for predictions.
    
    Configuration:
        - objective: binary:logistic (binary classification)
        - eval_metric: auc (AUROC optimization)
        - max_depth: 6 (tree depth)
        - learning_rate: 0.05 (step size shrinkage)
        - subsample: 0.8 (row sampling ratio)
        - colsample_bytree: 0.8 (column sampling ratio)
        - min_child_weight: 3 (minimum sum of instance weight)
        - scale_pos_weight: 2.5 (handle class imbalance)
        - tree_method: hist (fast histogram-based algorithm)
    """
    
    # Default XGBoost parameters optimized for CKD prediction
    DEFAULT_PARAMS = {
        'objective': 'binary:logistic',
        'eval_metric': 'auc',
        'max_depth': 6,
        'learning_rate': 0.05,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'min_child_weight': 3,
        'scale_pos_weight': 2.5,
        'tree_method': 'hist',
        'use_label_encoder': False,
        'random_state': 42,
    }
    
    # Prediction timeout in seconds (500ms requirement)
    PREDICTION_TIMEOUT_MS = 500
    
    def __init__(
        self,
        model_path: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize XGBoost classifier.
        
        Args:
            model_path: Path to load a pre-trained model (optional)
            params: Custom XGBoost parameters (optional, uses defaults if not provided)
        """
        self._model: Optional[XGBoostModel] = None
        self._params = {**self.DEFAULT_PARAMS}
        
        # Override with custom parameters if provided
        if params:
            self._params.update(params)
        
        # Load model if path provided
        if model_path:
            self.load_model(model_path)
    
    def load_model(self, model_path: str) -> None:
        """
        Load a trained XGBoost model from disk.
        
        Args:
            model_path: Path to serialized model file (.joblib or .json)
            
        Raises:
            FileNotFoundError: If model file doesn't exist
            Exception: If model loading fails
        """
        try:
            model_file = Path(model_path)
            if not model_file.exists():
                raise FileNotFoundError(f"Model file not found: {model_path}")
            
            # Load model using joblib
            self._model = joblib.load(model_path)
            
            logger.info(f"Loaded XGBoost model from {model_path}")
            
            # Validate that it's an XGBoost model
            if not isinstance(self._model, XGBoostModel):
                raise ValueError(
                    f"Loaded model is not an XGBoost classifier: {type(self._model)}"
                )
            
        except Exception as e:
            logger.error(f"Failed to load model from {model_path}: {e}")
            raise
    
    def save_model(self, model_path: str) -> None:
        """
        Save the trained model to disk.
        
        Args:
            model_path: Path to save the model file
            
        Raises:
            ValueError: If no model is trained
        """
        if self._model is None:
            raise ValueError("No model to save. Train or load a model first.")
        
        try:
            model_file = Path(model_path)
            model_file.parent.mkdir(parents=True, exist_ok=True)
            
            joblib.dump(self._model, model_path)
            logger.info(f"Saved XGBoost model to {model_path}")
            
        except Exception as e:
            logger.error(f"Failed to save model to {model_path}: {e}")
            raise
    
    def train(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: Optional[pd.DataFrame] = None,
        y_val: Optional[pd.Series] = None,
        n_estimators: int = 100,
    ) -> None:
        """
        Train the XGBoost model.
        
        Args:
            X_train: Training features
            y_train: Training labels
            X_val: Validation features (optional)
            y_val: Validation labels (optional)
            n_estimators: Number of boosting rounds
        """
        try:
            # Create model with configured parameters
            self._model = XGBoostModel(
                n_estimators=n_estimators,
                **self._params
            )
            
            # Prepare evaluation set if validation data provided
            eval_set = None
            if X_val is not None and y_val is not None:
                eval_set = [(X_val, y_val)]
            
            # Train model
            logger.info(f"Training XGBoost model with {n_estimators} estimators")
            self._model.fit(
                X_train,
                y_train,
                eval_set=eval_set,
                verbose=False
            )
            
            logger.info("XGBoost model training completed")
            
        except Exception as e:
            logger.error(f"Model training failed: {e}")
            raise
    
    def predict_proba(
        self,
        X: pd.DataFrame,
        timeout_ms: Optional[int] = None
    ) -> np.ndarray:
        """
        Generate probability predictions with timeout enforcement.
        
        Predicts the probability of CKD progression (class 1) for each sample.
        Enforces a timeout to meet the 500ms latency requirement.
        
        Args:
            X: Feature matrix (DataFrame with feature columns)
            timeout_ms: Prediction timeout in milliseconds (default: 500ms)
            
        Returns:
            Array of shape (n_samples, 2) with probabilities for each class
            
        Raises:
            ValueError: If model is not loaded
            TimeoutError: If prediction exceeds timeout
        """
        if self._model is None:
            raise ValueError("Model not loaded. Call load_model() or train() first.")
        
        if timeout_ms is None:
            timeout_ms = self.PREDICTION_TIMEOUT_MS
        
        start_time = time.time()
        
        try:
            # Generate predictions
            probabilities = self._model.predict_proba(X)
            
            # Check timeout
            elapsed_ms = (time.time() - start_time) * 1000
            if elapsed_ms > timeout_ms:
                logger.warning(
                    f"Prediction exceeded timeout: {elapsed_ms:.1f}ms > {timeout_ms}ms"
                )
                raise TimeoutError(
                    f"Prediction took {elapsed_ms:.1f}ms, exceeding {timeout_ms}ms timeout"
                )
            
            logger.debug(f"Prediction completed in {elapsed_ms:.1f}ms")
            
            return probabilities
            
        except TimeoutError:
            raise
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            raise
    
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Generate binary class predictions.
        
        Args:
            X: Feature matrix (DataFrame with feature columns)
            
        Returns:
            Array of predicted classes (0 or 1)
            
        Raises:
            ValueError: If model is not loaded
        """
        if self._model is None:
            raise ValueError("Model not loaded. Call load_model() or train() first.")
        
        try:
            predictions = self._model.predict(X)
            return predictions
            
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            raise
    
    def get_feature_importance(self) -> Dict[str, float]:
        """
        Get feature importance scores from the trained model.
        
        Returns:
            Dictionary mapping feature names to importance scores
            
        Raises:
            ValueError: If model is not trained
        """
        if self._model is None:
            raise ValueError("Model not trained. Train or load a model first.")
        
        try:
            # Get feature importance
            importance = self._model.feature_importances_
            
            # Get feature names
            if hasattr(self._model, 'feature_names_in_'):
                feature_names = self._model.feature_names_in_
            else:
                feature_names = [f"feature_{i}" for i in range(len(importance))]
            
            # Create dictionary
            importance_dict = dict(zip(feature_names, importance))
            
            return importance_dict
            
        except Exception as e:
            logger.error(f"Failed to get feature importance: {e}")
            raise
    
    def get_params(self) -> Dict[str, Any]:
        """
        Get the current model parameters.
        
        Returns:
            Dictionary of model parameters
        """
        return self._params.copy()
    
    @property
    def is_trained(self) -> bool:
        """
        Check if the model is trained or loaded.
        
        Returns:
            True if model is ready for predictions, False otherwise
        """
        return self._model is not None
