"""
Example usage of ML Analytics Engine.

This script demonstrates how to:
1. Create a patient record
2. Load a trained model
3. Generate predictions
4. Use the model registry
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
from app.ml import MLAnalyticsEngine, ModelRegistry
from app.models import (
    UnifiedPatientRecord,
    Demographics,
    Address,
    ClinicalRecord,
    AdministrativeRecord,
    SDOHRecord,
    Medication,
    Referral,
)


def create_example_patient() -> UnifiedPatientRecord:
    """Create an example patient record."""
    return UnifiedPatientRecord(
        patient_id="example-patient-001",
        demographics=Demographics(
            age=68,
            sex="F",
            race="Black",
            ethnicity="Non-Hispanic",
            address=Address(
                street="456 Oak Ave",
                city="Rural Town",
                state="MS",
                zip_code="39201",
                zcta="39201",
            ),
        ),
        clinical=ClinicalRecord(
            egfr=38.0,  # Stage 3b CKD
            egfr_history=[
                (datetime.now() - timedelta(days=730), 48.0),
                (datetime.now() - timedelta(days=365), 43.0),
                (datetime.now() - timedelta(days=180), 40.0),
                (datetime.now(), 38.0),
            ],
            uacr=280.0,  # Elevated
            hba1c=8.1,  # Poorly controlled diabetes
            systolic_bp=155,  # Elevated
            diastolic_bp=92,  # Elevated
            bmi=32.5,  # Obese
            medications=[
                Medication(name="Lisinopril", category="ACE_inhibitor", active=True),
                Medication(name="Metformin", category="Diabetes", active=True),
                Medication(name="Amlodipine", category="Calcium_channel_blocker", active=True),
            ],
            ckd_stage="3b",
            diagnosis_date=datetime.now() - timedelta(days=1095),  # 3 years ago
            comorbidities=["diabetes", "hypertension", "obesity"],
        ),
        administrative=AdministrativeRecord(
            visit_frequency_12mo=4,  # Low visit frequency
            specialist_referrals=[],  # No specialist referrals
            insurance_type="Medicaid",
            insurance_status="Active",
            last_visit_date=datetime.now() - timedelta(days=120),  # 4 months ago
        ),
        sdoh=SDOHRecord(
            adi_percentile=92,  # High deprivation
            food_desert=True,  # Limited food access
            housing_stability_score=0.4,  # Low stability
            transportation_access_score=0.3,  # Poor transportation
            rural_urban_code="6",  # Rural area
        ),
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


def main():
    """Run example ML Analytics Engine workflow."""
    print("=" * 60)
    print("ML Analytics Engine Example")
    print("=" * 60)
    
    # Create example patient
    print("\n1. Creating example patient record...")
    patient = create_example_patient()
    print(f"   Patient ID: {patient.patient_id}")
    print(f"   Age: {patient.demographics.age}, Sex: {patient.demographics.sex}")
    print(f"   eGFR: {patient.clinical.egfr} mL/min/1.73m²")
    print(f"   UACR: {patient.clinical.uacr} mg/g")
    print(f"   ADI Percentile: {patient.sdoh.adi_percentile}")
    print(f"   Food Desert: {patient.sdoh.food_desert}")
    
    # Initialize ML Analytics Engine
    print("\n2. Initializing ML Analytics Engine...")
    engine = MLAnalyticsEngine()
    
    # Note: In production, you would load a trained model:
    # engine.load_model("path/to/trained_model.joblib")
    print("   ⚠️  No model loaded (would load trained model in production)")
    
    # Extract features
    print("\n3. Extracting features from patient record...")
    features_df = engine.extract_features(patient)
    print(f"   Extracted {len(features_df.columns)} features")
    print(f"   Feature names: {', '.join(list(features_df.columns)[:10])}...")
    
    # Show some key features
    print("\n4. Key extracted features:")
    print(f"   Clinical:")
    print(f"     - eGFR: {features_df['egfr'].iloc[0]}")
    print(f"     - UACR: {features_df['uacr'].iloc[0]}")
    print(f"     - HbA1c: {features_df['hba1c'].iloc[0]}")
    print(f"     - eGFR slope: {features_df['egfr_slope'].iloc[0]:.2f} mL/min/1.73m²/year")
    print(f"   Administrative:")
    print(f"     - Visit frequency: {features_df['visit_frequency_12mo'].iloc[0]}")
    print(f"     - Specialist referrals: {features_df['specialist_referral_count'].iloc[0]}")
    print(f"   SDOH:")
    print(f"     - ADI percentile: {features_df['adi_percentile'].iloc[0]}")
    print(f"     - Food desert: {features_df['food_desert'].iloc[0]}")
    print(f"   Interaction:")
    print(f"     - eGFR × ADI: {features_df['egfr_x_adi'].iloc[0]}")
    
    # Verify race/ethnicity not in features
    print("\n5. Fairness check:")
    feature_names = engine.get_feature_names()
    has_race = 'race' in feature_names
    has_ethnicity = 'ethnicity' in feature_names
    print(f"   Race in features: {has_race} ✓" if not has_race else f"   Race in features: {has_race} ✗")
    print(f"   Ethnicity in features: {has_ethnicity} ✓" if not has_ethnicity else f"   Ethnicity in features: {has_ethnicity} ✗")
    
    # Model Registry example
    print("\n6. Model Registry example:")
    registry = ModelRegistry(registry_path="models/registry")
    print(f"   Registry path: models/registry")
    print(f"   Registered models: {len(registry.list_models())}")
    
    # Note: In production, you would:
    # result = engine.predict_progression_risk(patient)
    # print(f"\n7. Prediction result:")
    # print(f"   Risk Score: {result.risk_score:.3f}")
    # print(f"   Risk Tier: {result.risk_tier.value}")
    # print(f"   Processing Time: {result.processing_time_ms}ms")
    
    print("\n" + "=" * 60)
    print("Example completed!")
    print("=" * 60)
    print("\nNote: To generate actual predictions, you need to:")
    print("1. Train an XGBoost model on historical CKD data")
    print("2. Save the model using joblib")
    print("3. Load the model: engine.load_model('path/to/model.joblib')")
    print("4. Call: result = engine.predict_progression_risk(patient)")


if __name__ == "__main__":
    main()
