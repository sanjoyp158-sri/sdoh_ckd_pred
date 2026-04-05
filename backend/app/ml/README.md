# ML Analytics Engine

The ML Analytics Engine is the core machine learning component of the CKD Early Detection System. It handles model loading, feature engineering, prediction generation, and model versioning.

## Components

### MLAnalyticsEngine

The main class for generating CKD progression predictions.

**Key Features:**
- Loads trained XGBoost models from disk
- Extracts 30+ features from patient records (clinical, administrative, SDOH)
- Generates risk scores (0-1) for Stage 2-3 CKD patients
- Classifies patients into risk tiers (HIGH, MODERATE, LOW)
- Meets 500ms prediction latency requirement
- Excludes race/ethnicity as direct features (fairness requirement)

**Usage:**
```python
from app.ml import MLAnalyticsEngine
from app.models import UnifiedPatientRecord

# Initialize engine
engine = MLAnalyticsEngine()
engine.load_model("path/to/model.joblib")

# Generate prediction
patient = UnifiedPatientRecord(...)
result = engine.predict_progression_risk(patient)

print(f"Risk Score: {result.risk_score:.3f}")
print(f"Risk Tier: {result.risk_tier.value}")
print(f"Processing Time: {result.processing_time_ms}ms")
```

### ModelRegistry

Manages model versioning, deployment, and A/B testing.

**Key Features:**
- Register models with version tracking
- Promote models to production
- Rollback to previous versions
- Support A/B testing with traffic splitting
- Track model metrics and deployment history

**Usage:**
```python
from app.ml import ModelRegistry
from app.models.ml import ModelMetrics

# Initialize registry
registry = ModelRegistry(registry_path="models/registry")

# Register a new model
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
    model_path="/path/to/model.joblib",
    metrics=metrics,
)

# Promote to production
registry.promote_to_production("model-001")

# Rollback if needed
registry.rollback()
```

## Feature Engineering

The engine extracts 30+ features from patient records:

### Clinical Features (11)
- eGFR, UACR, HbA1c
- Systolic/diastolic blood pressure
- BMI
- Medication counts (total, ACE inhibitors, ARBs, SGLT2 inhibitors)
- Comorbidity flags (diabetes, hypertension, CVD)

### Administrative Features (9)
- Visit frequency (last 12 months)
- Specialist referral count
- Insurance type (Medicare, Medicaid, Commercial, Uninsured)

### SDOH Features (4)
- ADI percentile
- Food desert status
- Housing stability score
- Transportation access score

### Temporal Features (2)
- eGFR slope (change per year)
- Years since CKD diagnosis

### Demographic Features (3)
- Age
- Sex (male/female)
- **Note: Race and ethnicity are NOT used as features**

### Interaction Features (2)
- eGFR × ADI percentile
- UACR × food desert status

## Risk Tier Classification

Risk scores are classified into three tiers:

- **HIGH** (>0.65): Triggers full intervention workflow
- **MODERATE** (0.35-0.65): Monitoring and provider notification
- **LOW** (<0.35): Routine care

Thresholds were optimized using Youden's J statistic on validation data.

## Performance Requirements

- **Prediction Latency**: ≤500ms per patient
- **Model AUROC**: ≥0.87 on validation data
- **Fairness**: AUROC within 0.05 across racial/ethnic subgroups
- **Features**: Race and ethnicity excluded as direct inputs

## Model Format

Models should be trained using XGBoost and saved as joblib files:

```python
import joblib
from xgboost import XGBClassifier

# Train model
model = XGBClassifier(
    objective='binary:logistic',
    max_depth=6,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
)
model.fit(X_train, y_train)

# Save model
joblib.dump(model, "model.joblib")
```

## Testing

Run unit tests:
```bash
pytest tests/unit/test_ml_analytics_engine.py -v
```

## Requirements

See `requirements.txt` for dependencies:
- xgboost==2.0.3
- scikit-learn==1.4.0
- numpy==1.26.3
- pandas==2.2.0
- joblib==1.3.2
