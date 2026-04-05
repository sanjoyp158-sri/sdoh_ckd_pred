"""
Property-based tests for Data Integration Layer.

Tests data ingestion completeness using Hypothesis for property-based testing.
Validates that all required fields are extracted and stored correctly across
a wide range of valid inputs.
"""

import pytest
from hypothesis import given, strategies as st, assume
from datetime import datetime, timedelta
from app.services.data_integration import (
    DataIntegrationLayer,
    DataValidationError
)
from app.models.patient import (
    Address,
    ClinicalRecord,
    AdministrativeRecord,
    SDOHRecord,
    UnifiedPatientRecord,
    Demographics,
    Medication,
    Referral,
)


# Custom Hypothesis strategies for generating valid test data

@st.composite
def valid_egfr_strategy(draw):
    """Generate valid eGFR values for Stage 2-3 CKD (30-89 mL/min/1.73m²)."""
    return draw(st.floats(min_value=30.0, max_value=89.0))


@st.composite
def valid_uacr_strategy(draw):
    """Generate valid UACR values (0-5000 mg/g)."""
    return draw(st.floats(min_value=0.0, max_value=5000.0))


@st.composite
def valid_hba1c_strategy(draw):
    """Generate valid HbA1c values (4.0-14.0%)."""
    return draw(st.floats(min_value=4.0, max_value=14.0))


@st.composite
def valid_blood_pressure_strategy(draw):
    """Generate valid blood pressure values."""
    systolic = draw(st.integers(min_value=80, max_value=200))
    diastolic = draw(st.integers(min_value=40, max_value=130))
    # Ensure systolic > diastolic
    assume(systolic > diastolic)
    return systolic, diastolic


@st.composite
def valid_bmi_strategy(draw):
    """Generate valid BMI values (15.0-60.0 kg/m²)."""
    return draw(st.floats(min_value=15.0, max_value=60.0))


@st.composite
def valid_ckd_stage_strategy(draw):
    """Generate valid CKD stage values for Stage 2-3."""
    return draw(st.sampled_from(['2', '3a', '3b']))


@st.composite
def valid_date_strategy(draw):
    """Generate valid date strings within the last 10 years."""
    days_ago = draw(st.integers(min_value=0, max_value=3650))
    date = datetime.now() - timedelta(days=days_ago)
    return date.strftime('%Y-%m-%d')


@st.composite
def medication_strategy(draw):
    """Generate valid medication records as dictionaries for ingestion."""
    return {
        'name': draw(st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll')))),
        'category': draw(st.sampled_from(['ACE_inhibitor', 'ARB', 'Diabetes', 'Statin', 'Diuretic'])),
        'start_date': draw(st.datetimes(min_value=datetime(2010, 1, 1), max_value=datetime.now())),
        'active': draw(st.booleans())
    }


@st.composite
def egfr_history_strategy(draw):
    """Generate valid eGFR history records as dictionaries for ingestion."""
    num_entries = draw(st.integers(min_value=0, max_value=10))
    history = []
    for _ in range(num_entries):
        history.append({
            'date': draw(st.datetimes(min_value=datetime(2010, 1, 1), max_value=datetime.now())),
            'value': draw(st.floats(min_value=15.0, max_value=120.0))
        })
    return history


@st.composite
def ehr_payload_strategy(draw):
    """Generate valid EHR payload with all required clinical fields."""
    systolic, diastolic = draw(valid_blood_pressure_strategy())
    
    return {
        'egfr': draw(valid_egfr_strategy()),
        'uacr': draw(valid_uacr_strategy()),
        'hba1c': draw(valid_hba1c_strategy()),
        'systolic_bp': systolic,
        'diastolic_bp': diastolic,
        'bmi': draw(valid_bmi_strategy()),
        'ckd_stage': draw(valid_ckd_stage_strategy()),
        'diagnosis_date': draw(valid_date_strategy()),
        'egfr_history': draw(egfr_history_strategy()),
        'medications': draw(st.lists(medication_strategy(), min_size=0, max_size=10)),
        'comorbidities': draw(st.lists(
            st.sampled_from(['Diabetes', 'Hypertension', 'CVD', 'Obesity']),
            min_size=0,
            max_size=4,
            unique=True
        ))
    }


@st.composite
def referral_strategy(draw):
    """Generate valid referral records as dictionaries for ingestion."""
    return {
        'specialty': draw(st.sampled_from(['Nephrology', 'Cardiology', 'Endocrinology', 'Ophthalmology'])),
        'date': draw(st.datetimes(min_value=datetime(2020, 1, 1), max_value=datetime.now())),
        'completed': draw(st.booleans()),
        'reason': draw(st.text(min_size=5, max_size=100, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Zs'))))
    }


@st.composite
def admin_payload_strategy(draw):
    """Generate valid administrative payload with all required fields."""
    return {
        'visit_frequency_12mo': draw(st.integers(min_value=0, max_value=50)),
        'insurance_type': draw(st.sampled_from(['Medicare', 'Medicaid', 'Commercial', 'Uninsured'])),
        'insurance_status': draw(st.sampled_from(['Active', 'Inactive', 'Pending'])),
        'last_visit_date': draw(valid_date_strategy()),
        'specialist_referrals': draw(st.lists(referral_strategy(), min_size=0, max_size=10))
    }


@st.composite
def address_strategy(draw):
    """Generate valid address for SDOH lookup."""
    return Address(
        street=draw(st.text(min_size=5, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs')))),
        city=draw(st.text(min_size=3, max_size=30, alphabet=st.characters(whitelist_categories=('Lu', 'Ll')))),
        state=draw(st.sampled_from(['IL', 'CA', 'TX', 'NY', 'FL', 'PA', 'OH', 'MI', 'GA', 'NC'])),
        zip_code=draw(st.text(min_size=5, max_size=5, alphabet=st.characters(whitelist_categories=('Nd',)))),
        zcta=draw(st.text(min_size=5, max_size=5, alphabet=st.characters(whitelist_categories=('Nd',))))
    )


# Property-Based Tests


@given(ehr_payload=ehr_payload_strategy())
@pytest.mark.property_test
def test_property_1_clinical_data_ingestion_completeness(ehr_payload):
    """
    **Validates: Requirements 1.1**
    
    Property 1: Clinical Data Ingestion Completeness
    
    For any EHR payload containing clinical data, the Data Integration Layer 
    should extract and store all required fields: eGFR, UACR, HbA1c, blood 
    pressure, BMI, and medication records in the resulting ClinicalRecord.
    """
    # Create data integration layer instance
    data_integration_layer = DataIntegrationLayer()
    
    # Ingest clinical data
    clinical_record = data_integration_layer.ingest_clinical_data(ehr_payload)
    
    # Verify the record is created
    assert isinstance(clinical_record, ClinicalRecord)
    
    # Verify all required fields are extracted and stored
    assert clinical_record.egfr == ehr_payload['egfr']
    assert clinical_record.uacr == ehr_payload['uacr']
    assert clinical_record.hba1c == ehr_payload['hba1c']
    assert clinical_record.systolic_bp == ehr_payload['systolic_bp']
    assert clinical_record.diastolic_bp == ehr_payload['diastolic_bp']
    assert clinical_record.bmi == ehr_payload['bmi']
    
    # Verify medication records are extracted
    assert len(clinical_record.medications) == len(ehr_payload['medications'])
    for i, med in enumerate(clinical_record.medications):
        assert med.name == ehr_payload['medications'][i]['name']
        assert med.category == ehr_payload['medications'][i]['category']
        assert med.active == ehr_payload['medications'][i]['active']
    
    # Verify eGFR history is extracted
    assert len(clinical_record.egfr_history) == len(ehr_payload['egfr_history'])
    
    # Verify comorbidities are extracted
    assert set(clinical_record.comorbidities) == set(ehr_payload['comorbidities'])


@given(admin_payload=admin_payload_strategy())
@pytest.mark.property_test
def test_property_2_administrative_data_ingestion_completeness(admin_payload):
    """
    **Validates: Requirements 1.2**
    
    Property 2: Administrative Data Ingestion Completeness
    
    For any administrative system payload, the Data Integration Layer should 
    extract and store all required fields: visit frequency, referral records, 
    and insurance status in the resulting AdministrativeRecord.
    """
    # Create data integration layer instance
    data_integration_layer = DataIntegrationLayer()
    
    # Ingest administrative data
    admin_record = data_integration_layer.ingest_administrative_data(admin_payload)
    
    # Verify the record is created
    assert isinstance(admin_record, AdministrativeRecord)
    
    # Verify all required fields are extracted and stored
    assert admin_record.visit_frequency_12mo == admin_payload['visit_frequency_12mo']
    assert admin_record.insurance_type == admin_payload['insurance_type']
    assert admin_record.insurance_status == admin_payload['insurance_status']
    
    # Verify referral records are extracted
    assert len(admin_record.specialist_referrals) == len(admin_payload['specialist_referrals'])
    for i, ref in enumerate(admin_record.specialist_referrals):
        assert ref.specialty == admin_payload['specialist_referrals'][i]['specialty']
        assert ref.completed == admin_payload['specialist_referrals'][i]['completed']
        assert ref.reason == admin_payload['specialist_referrals'][i]['reason']


@given(address=address_strategy())
@pytest.mark.property_test
def test_property_3_sdoh_data_retrieval_completeness(address):
    """
    **Validates: Requirements 1.3**
    
    Property 3: SDOH Data Retrieval Completeness
    
    For any patient address, the Data Integration Layer should retrieve and 
    store all required SDOH fields: ADI score, food desert status, housing 
    stability indicators, and transportation access metrics in the resulting 
    SDOHRecord.
    """
    # Create data integration layer instance
    data_integration_layer = DataIntegrationLayer()
    
    # Retrieve SDOH data
    sdoh_record = data_integration_layer.retrieve_sdoh_data(address)
    
    # Verify the record is created
    assert isinstance(sdoh_record, SDOHRecord)
    
    # Verify all required SDOH fields are present and valid
    # ADI percentile should be between 1 and 100
    assert isinstance(sdoh_record.adi_percentile, int)
    assert 1 <= sdoh_record.adi_percentile <= 100
    
    # Food desert status should be a boolean
    assert isinstance(sdoh_record.food_desert, bool)
    
    # Housing stability score should be between 0 and 1
    assert isinstance(sdoh_record.housing_stability_score, float)
    assert 0.0 <= sdoh_record.housing_stability_score <= 1.0
    
    # Transportation access score should be between 0 and 1
    assert isinstance(sdoh_record.transportation_access_score, float)
    assert 0.0 <= sdoh_record.transportation_access_score <= 1.0
    
    # Rural/urban code should be present
    assert isinstance(sdoh_record.rural_urban_code, str)
    assert len(sdoh_record.rural_urban_code) > 0


@st.composite
def demographics_strategy(draw):
    """Generate valid Demographics instances."""
    from app.models.patient import Demographics
    return Demographics(
        age=draw(st.integers(min_value=18, max_value=100)),
        sex=draw(st.sampled_from(['M', 'F'])),
        race=draw(st.sampled_from(['White', 'Black', 'Hispanic', 'Asian', 'Other'])),
        ethnicity=draw(st.sampled_from(['Hispanic', 'Non-Hispanic'])),
        address=draw(address_strategy())
    )


@st.composite
def clinical_record_strategy(draw):
    """Generate valid ClinicalRecord instances."""
    systolic, diastolic = draw(valid_blood_pressure_strategy())
    return ClinicalRecord(
        egfr=draw(valid_egfr_strategy()),
        egfr_history=draw(egfr_history_strategy()),
        uacr=draw(valid_uacr_strategy()),
        hba1c=draw(valid_hba1c_strategy()),
        systolic_bp=systolic,
        diastolic_bp=diastolic,
        bmi=draw(valid_bmi_strategy()),
        medications=draw(st.lists(medication_strategy(), min_size=0, max_size=10)),
        ckd_stage=draw(valid_ckd_stage_strategy()),
        diagnosis_date=draw(st.datetimes(min_value=datetime(2010, 1, 1), max_value=datetime.now())),
        comorbidities=draw(st.lists(
            st.sampled_from(['Diabetes', 'Hypertension', 'CVD', 'Obesity']),
            min_size=0,
            max_size=4,
            unique=True
        ))
    )


@st.composite
def administrative_record_strategy(draw):
    """Generate valid AdministrativeRecord instances."""
    return AdministrativeRecord(
        visit_frequency_12mo=draw(st.integers(min_value=0, max_value=50)),
        specialist_referrals=draw(st.lists(referral_strategy(), min_size=0, max_size=10)),
        insurance_type=draw(st.sampled_from(['Medicare', 'Medicaid', 'Commercial', 'Uninsured'])),
        insurance_status=draw(st.sampled_from(['Active', 'Inactive', 'Pending'])),
        last_visit_date=draw(st.datetimes(min_value=datetime(2020, 1, 1), max_value=datetime.now()))
    )


@st.composite
def sdoh_record_strategy(draw):
    """Generate valid SDOHRecord instances."""
    return SDOHRecord(
        adi_percentile=draw(st.integers(min_value=1, max_value=100)),
        food_desert=draw(st.booleans()),
        housing_stability_score=draw(st.floats(min_value=0.0, max_value=1.0)),
        transportation_access_score=draw(st.floats(min_value=0.0, max_value=1.0)),
        rural_urban_code=draw(st.sampled_from(['urban', 'rural', 'suburban']))
    )


@given(
    clinical=clinical_record_strategy(),
    administrative=administrative_record_strategy(),
    sdoh=sdoh_record_strategy()
)
@pytest.mark.property_test
def test_property_4_data_harmonization_combines_all_sources(clinical, administrative, sdoh):
    """
    **Validates: Requirements 1.4**
    
    Property 4: Data Harmonization Combines All Sources
    
    For any clinical record, administrative record, and SDOH record, the 
    harmonization function should produce a UnifiedPatientRecord containing 
    data from all three sources.
    """
    from app.models.patient import UnifiedPatientRecord
    
    # Create data integration layer instance
    data_integration_layer = DataIntegrationLayer()
    
    # Create demographics
    demographics = Demographics(
        age=65,
        sex='M',
        race='White',
        ethnicity='Non-Hispanic',
        address=Address(
            street='123 Test St',
            city='TestCity',
            state='IL',
            zip_code='12345',
            zcta='12345'
        )
    )
    
    # Harmonize patient record
    unified_record = data_integration_layer.harmonize_patient_record(
        patient_id='test-patient-harmonization',
        demographics=demographics,
        clinical=clinical,
        administrative=administrative,
        sdoh=sdoh
    )
    
    # Verify the unified record is created
    assert isinstance(unified_record, UnifiedPatientRecord)
    
    # Verify all three data sources are present in the unified record
    assert unified_record.clinical is not None
    assert unified_record.administrative is not None
    assert unified_record.sdoh is not None
    
    # Verify the data from each source is preserved
    # Clinical data
    assert unified_record.clinical.egfr == clinical.egfr
    assert unified_record.clinical.uacr == clinical.uacr
    assert unified_record.clinical.hba1c == clinical.hba1c
    assert unified_record.clinical.systolic_bp == clinical.systolic_bp
    assert unified_record.clinical.diastolic_bp == clinical.diastolic_bp
    assert unified_record.clinical.bmi == clinical.bmi
    
    # Administrative data
    assert unified_record.administrative.visit_frequency_12mo == administrative.visit_frequency_12mo
    assert unified_record.administrative.insurance_type == administrative.insurance_type
    assert unified_record.administrative.insurance_status == administrative.insurance_status
    
    # SDOH data
    assert unified_record.sdoh.adi_percentile == sdoh.adi_percentile
    assert unified_record.sdoh.food_desert == sdoh.food_desert
    assert unified_record.sdoh.housing_stability_score == sdoh.housing_stability_score
    assert unified_record.sdoh.transportation_access_score == sdoh.transportation_access_score
    
    # Verify timestamps are set
    assert isinstance(unified_record.created_at, datetime)
    assert isinstance(unified_record.updated_at, datetime)


@st.composite
def data_source_failure_strategy(draw):
    """Generate scenarios for data source failures."""
    # Choose which data source(s) fail
    clinical_fails = draw(st.booleans())
    administrative_fails = draw(st.booleans())
    sdoh_fails = draw(st.booleans())
    
    # At least one source should succeed (otherwise we can't test continuation)
    # and at least one should fail (to test error handling)
    assume(not (clinical_fails and administrative_fails and sdoh_fails))
    assume(clinical_fails or administrative_fails or sdoh_fails)
    
    return {
        'clinical_fails': clinical_fails,
        'administrative_fails': administrative_fails,
        'sdoh_fails': sdoh_fails
    }


@given(
    ehr_payload=ehr_payload_strategy(),
    admin_payload=admin_payload_strategy(),
    address=address_strategy(),
    failure_scenario=data_source_failure_strategy()
)
@pytest.mark.property_test
def test_property_5_data_ingestion_error_handling(
    ehr_payload, 
    admin_payload, 
    address, 
    failure_scenario
):
    """
    **Validates: Requirements 1.5**
    
    Property 5: Data Ingestion Error Handling
    
    For any data ingestion failure in any channel (clinical, administrative, 
    or SDOH), the system should log the error with source identification and 
    continue processing available data from other channels.
    """
    import logging
    from unittest.mock import patch, MagicMock
    
    # Create data integration layer instance
    data_integration_layer = DataIntegrationLayer()
    
    # Create demographics payload
    demographics_payload = {
        'age': 65,
        'sex': 'M',
        'race': 'White',
        'ethnicity': 'Non-Hispanic'
    }
    
    # Mock the logger to capture log messages
    with patch.object(data_integration_layer, 'logger') as mock_logger:
        # Set up failure scenarios by patching methods
        with patch.object(
            data_integration_layer, 
            'ingest_clinical_data',
            side_effect=DataValidationError("Clinical data ingestion failed") if failure_scenario['clinical_fails'] else data_integration_layer.ingest_clinical_data
        ) as mock_clinical, \
        patch.object(
            data_integration_layer,
            'ingest_administrative_data',
            side_effect=DataValidationError("Administrative data ingestion failed") if failure_scenario['administrative_fails'] else data_integration_layer.ingest_administrative_data
        ) as mock_admin, \
        patch.object(
            data_integration_layer,
            'retrieve_sdoh_data',
            side_effect=DataValidationError("SDOH data retrieval failed") if failure_scenario['sdoh_fails'] else data_integration_layer.retrieve_sdoh_data
        ) as mock_sdoh:
            
            # If clinical or administrative fails, the entire ingestion should fail
            # (these are critical data sources)
            if failure_scenario['clinical_fails'] or failure_scenario['administrative_fails']:
                with pytest.raises(DataValidationError):
                    data_integration_layer.ingest_patient_data(
                        patient_id='test-patient-error-handling',
                        demographics_payload=demographics_payload,
                        ehr_payload=ehr_payload,
                        admin_payload=admin_payload,
                        address=address
                    )
                
                # Verify error was logged with source identification
                error_calls = [call for call in mock_logger.error.call_args_list]
                assert len(error_calls) > 0
                
                # Check that source is identified in error message
                error_messages = [str(call) for call in error_calls]
                # The first failure should be logged with source identification
                # If clinical fails, it fails first (before administrative is attempted)
                # If only administrative fails, it should be logged
                if failure_scenario['clinical_fails']:
                    # Clinical failure should be logged
                    clinical_mentioned = any('EHR system' in msg or 'clinical' in msg.lower() for msg in error_messages)
                    assert clinical_mentioned, f"Clinical failure not logged. Error messages: {error_messages}"
                elif failure_scenario['administrative_fails']:
                    # Only check administrative if clinical didn't fail (since clinical is checked first)
                    admin_mentioned = any('Administrative system' in msg or 'administrative' in msg.lower() for msg in error_messages)
                    assert admin_mentioned, f"Administrative failure not logged. Error messages: {error_messages}"
            
            # If only SDOH fails, ingestion should continue with regional averages
            elif failure_scenario['sdoh_fails']:
                unified_record = data_integration_layer.ingest_patient_data(
                    patient_id='test-patient-error-handling',
                    demographics_payload=demographics_payload,
                    ehr_payload=ehr_payload,
                    admin_payload=admin_payload,
                    address=address
                )
                
                # Verify the record was created despite SDOH failure
                assert isinstance(unified_record, UnifiedPatientRecord)
                
                # Verify clinical and administrative data are present
                assert unified_record.clinical is not None
                assert unified_record.administrative is not None
                
                # Verify SDOH data is present (should use regional averages)
                assert unified_record.sdoh is not None
                
                # Verify error was logged with source identification
                warning_calls = [call for call in mock_logger.warning.call_args_list]
                assert len(warning_calls) > 0
                
                # Check that SDOH source is identified in warning message
                warning_messages = [str(call) for call in warning_calls]
                assert any('SDOH' in msg for msg in warning_messages)
