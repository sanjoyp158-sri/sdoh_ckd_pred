# XGBoost Classifier Integration

## Overview

The `XGBoostClassifier` wrapper provides a configured XGBoost model optimized for CKD progression prediction. It handles model training, loading, and prediction with timeout enforcement to meet the 500ms latency requirement.

## Features

- **Pre-configured Parameters**: Optimized hyperparameters for CKD prediction
- **Timeout Enforcement**: 500ms prediction timeout to meet performance requirements
- **Model Registry Integration**: Compatible with the model versioning system
- **Training Support**: Built-in training with validation set support
- **Feature Importance**: Extract feature importance scores from trained models

## Configuration

The classifier uses the following default parameters optimized for CKD progression prediction:

```python
{
    'objective': 'binary:logistic',      # Binary classification
    'eval_metric': 'auc',                 # AUROC optimization
    'max_depth': 6,                       # Tree depth
    'learning_rate': 0.05,                # Step size shrinkage
    'subsample': 0.8,                     # Row sampling ratio
    'colsample_bytree': 0.8,              # Column sampling ratio
    'min_child_weight': 3,                # Minimum sum of instance weight
    'scale_pos_weight': 2.5,              # Handle class imbalance
    'tree_method': 'hist',                # Fast histogram-based algorithm
}
```

These parameters are based on the design document specifications (Section: XGBoost Classifier).

## Usage

### Basic Usage

```python
from app.ml.xgboost_classifier import XGBoostClassifier

# Load a pre-trained model
classifier = XGBoostClassifier(model_path="models/ckd_model.joblib")

# Make predictions with timeout enforcement
probabilities = classifier.predict_proba(features_df, timeout_ms=500)
risk_score = probabilities[0, 1]  # Probability of progression
```

### Training a New Model

```python
import pandas as pd
from app.ml.xgboost_classifier import XGBoostClassifier

# Prepare training data
X_train = pd.DataFrame(...)  # Feature matrix
y_train = pd.Series(...)     # Binary labels (0 or 1)

# Create and train classifier
classifier = XGBoostClassifier()
classifier.train(
    X_train, y_train,
    X_val=X_val, y_val=y_val,  # Optional validation set
    n_estimators=100
)

# Save trained model
classifier.save_model("models/new_model.joblib")
```

### Custom Parameters

```python
# Override default parameters
custom_params = {
    'max_depth': 8,
    'learning_rate': 0.1,
}

classifier = XGBoostClassifier(params=custom_params)
```

### Integration with ML Analytics Engine

The `MLAnalyticsEngine` uses the `XGBoostClassifier` internally:

```python
from app.ml.analytics_engine import MLAnalyticsEngine

# Engine automatically uses XGBoostClassifier
engine = MLAnalyticsEngine(model_path="models/ckd_model.joblib")

# Predictions include timeout enforcement
result = engine.predict_progression_risk(patient)
print(f"Risk score: {result.risk_score}")
print(f"Processing time: {result.processing_time_ms}ms")
```

### Feature Importance

```python
# Get feature importance scores
importance = classifier.get_feature_importance()

# Sort by importance
sorted_features = sorted(
    importance.items(),
    key=lambda x: x[1],
    reverse=True
)

for feature, score in sorted_features[:10]:
    print(f"{feature}: {score:.4f}")
```

## Performance Requirements

The classifier enforces a **500ms timeout** for predictions to meet the system's latency requirements (Requirement 2.4). If a prediction exceeds this timeout, a `TimeoutError` is raised.

```python
try:
    probabilities = classifier.predict_proba(features_df, timeout_ms=500)
except TimeoutError as e:
    logger.error(f"Prediction timeout: {e}")
    # Handle timeout (e.g., retry, use cached prediction, alert ops team)
```

## Model Registry Integration

The classifier integrates with the model registry for versioning and deployment:

```python
from app.ml.analytics_engine import ModelRegistry
from app.models.ml import ModelMetrics

# Register a trained model
registry = ModelRegistry()
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
    model_id="ckd-model-v1",
    model_version="v1.0.0",
    model_path="models/ckd_model.joblib",
    metrics=metrics,
    is_production=True,
)

# Load production model
prod_model = registry.get_production_model()
classifier = XGBoostClassifier(model_path=prod_model.model_path)
```

## Testing

The classifier includes comprehensive unit tests:

```bash
# Run XGBoost classifier tests
pytest tests/unit/test_xgboost_classifier.py -v

# Run ML Analytics Engine tests (includes integration)
pytest tests/unit/test_ml_analytics_engine.py -v

# Run property-based tests
pytest tests/property/test_properties_ml_analytics.py -v
```

## Error Handling

The classifier handles various error conditions:

- **Model Not Loaded**: Raises `ValueError` if prediction is attempted without a loaded model
- **File Not Found**: Raises `FileNotFoundError` if model file doesn't exist
- **Prediction Timeout**: Raises `TimeoutError` if prediction exceeds timeout
- **Training Errors**: Logs and re-raises exceptions during training

## Design Document References

This implementation satisfies the following requirements:

- **Requirement 2.1**: Generate risk scores between 0 and 1
- **Requirement 2.4**: Process predictions within 500ms
- **Design Section: XGBoost Classifier**: Implements configured parameters and timeout enforcement

## API Reference

### XGBoostClassifier

#### Constructor

```python
XGBoostClassifier(
    model_path: Optional[str] = None,
    params: Optional[Dict[str, Any]] = None
)
```

#### Methods

- `load_model(model_path: str) -> None`: Load a trained model from disk
- `save_model(model_path: str) -> None`: Save the trained model to disk
- `train(X_train, y_train, X_val=None, y_val=None, n_estimators=100) -> None`: Train the model
- `predict_proba(X, timeout_ms=500) -> np.ndarray`: Generate probability predictions with timeout
- `predict(X) -> np.ndarray`: Generate binary class predictions
- `get_feature_importance() -> Dict[str, float]`: Get feature importance scores
- `get_params() -> Dict[str, Any]`: Get current model parameters

#### Properties

- `is_trained: bool`: Check if model is trained or loaded
- `PREDICTION_TIMEOUT_MS: int`: Default prediction timeout (500ms)
- `DEFAULT_PARAMS: Dict`: Default XGBoost parameters

## Future Enhancements

Potential improvements for future iterations:

1. **Async Predictions**: Support asynchronous prediction for batch processing
2. **GPU Acceleration**: Enable GPU training with `tree_method='gpu_hist'`
3. **Model Monitoring**: Track prediction latency and model drift
4. **Hyperparameter Tuning**: Automated hyperparameter optimization
5. **Ensemble Methods**: Support for model ensembles and stacking
