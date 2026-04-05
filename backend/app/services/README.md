# Data Integration Layer

## Overview

The Data Integration Layer is responsible for ingesting patient data from multiple sources (EHR systems, administrative systems, and SDOH providers) and harmonizing them into unified patient records.

## Components

### DataIntegrationLayer Class

Main class that handles all data ingestion and harmonization operations.

#### Methods

- `ingest_clinical_data(ehr_payload: Dict) -> ClinicalRecord`
  - Ingests clinical data from EHR systems
  - Validates required fields: eGFR, UACR, HbA1c, blood pressure, BMI, medications
  - Extracts eGFR history and medication records
  - Returns validated ClinicalRecord

- `ingest_administrative_data(admin_payload: Dict) -> AdministrativeRecord`
  - Ingests administrative data from billing systems
  - Validates required fields: visit frequency, insurance type/status, referrals
  - Extracts specialist referral records
  - Returns validated AdministrativeRecord

- `retrieve_sdoh_data(patient_address: Address) -> SDOHRecord`
  - Retrieves SDOH data for patient address
  - Fetches ADI score, food desert status, housing stability, transportation access
  - Currently uses placeholder data (TODO: integrate with actual SDOH providers)
  - Returns SDOHRecord

- `harmonize_patient_record(...) -> UnifiedPatientRecord`
  - Combines data from all sources into unified patient record
  - Sets created_at and updated_at timestamps
  - Returns UnifiedPatientRecord

- `ingest_patient_data(...) -> UnifiedPatientRecord`
  - Complete end-to-end ingestion workflow
  - Handles partial failures gracefully with logging
  - Returns unified patient record with all available data

## Data Validation

The layer implements comprehensive data validation:

- **Required Field Validation**: Ensures all critical fields are present
- **Type Validation**: Validates data types (float, int, string, datetime)
- **Range Validation**: Implicit through type conversion
- **Error Handling**: Raises `DataValidationError` for validation failures

## Error Handling

- Missing required fields: Raises `DataValidationError` with field list
- Invalid data types: Raises `DataValidationError` with error details
- SDOH data unavailable: Logs warning and raises error (TODO: implement regional average fallback)
- All errors are logged with source identification

## Usage Example

```python
from backend.app.services import DataIntegrationLayer
from backend.app.models.patient import Address

# Initialize layer
data_layer = DataIntegrationLayer()

# Prepare data
address = Address(
    street='123 Main St',
    city='Springfield',
    state='IL',
    zip_code='62701'
)

demographics = {
    'age': 65,
    'sex': 'M',
    'race': 'White',
    'ethnicity': 'Non-Hispanic'
}

ehr_payload = {
    'egfr': 45.5,
    'uacr': 150.0,
    'hba1c': 7.2,
    'systolic_bp': 140,
    'diastolic_bp': 85,
    'bmi': 28.5,
    'ckd_stage': '3a',
    'diagnosis_date': '2022-01-15',
    'medications': [...],
    'comorbidities': ['Diabetes', 'Hypertension']
}

admin_payload = {
    'visit_frequency_12mo': 8,
    'insurance_type': 'Medicare',
    'insurance_status': 'Active',
    'last_visit_date': '2023-11-15',
    'specialist_referrals': [...]
}

# Ingest complete patient data
unified_record = data_layer.ingest_patient_data(
    patient_id='patient-123',
    demographics_payload=demographics,
    ehr_payload=ehr_payload,
    admin_payload=admin_payload,
    address=address
)

# Access unified data
print(f"Patient eGFR: {unified_record.clinical.egfr}")
print(f"ADI Percentile: {unified_record.sdoh.adi_percentile}")
```

## Testing

### Unit Tests
Located in `backend/tests/unit/test_data_integration.py`
- 20 unit tests covering all ingestion methods
- Tests for success cases, error cases, and edge cases
- Tests for data validation and error handling

### Integration Tests
Located in `backend/tests/integration/test_data_integration_workflow.py`
- 3 integration tests for complete workflows
- Tests for high-risk, low-risk, and typical patient profiles
- End-to-end validation of data flow

Run tests:
```bash
# Unit tests only
python3 -m pytest backend/tests/unit/test_data_integration.py -v

# Integration tests only
python3 -m pytest backend/tests/integration/test_data_integration_workflow.py -v

# All tests
python3 -m pytest backend/tests/ -v
```

## Requirements Validated

This implementation validates the following requirements:

- **Requirement 1.1**: Clinical data ingestion (eGFR, UACR, HbA1c, BP, BMI, medications)
- **Requirement 1.2**: Administrative data ingestion (visit frequency, referrals, insurance)
- **Requirement 1.3**: SDOH data retrieval (ADI, food desert, housing, transportation)
- **Requirement 1.4**: Data harmonization into unified records
- **Requirement 1.5**: Error handling with source identification and logging

## Future Enhancements

1. **SDOH Provider Integration**: Replace placeholder SDOH data with actual API calls to:
   - Neighborhood Atlas for ADI scores
   - USDA Food Access Research Atlas for food desert data
   - HUD data for housing stability
   - Census/DOT data for transportation access

2. **Regional Average Fallback**: Implement fallback to regional averages when SDOH data is unavailable

3. **Batch Processing**: Add support for batch ingestion of multiple patients

4. **Data Quality Metrics**: Track and report data completeness and quality metrics

5. **Caching**: Implement caching for SDOH data to reduce external API calls

6. **Async Processing**: Add async support for parallel data ingestion from multiple sources
