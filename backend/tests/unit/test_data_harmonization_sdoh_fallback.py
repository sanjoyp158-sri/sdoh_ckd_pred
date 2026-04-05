"""
Unit tests for data harmonization with SDOH fallback to regional averages.

Tests that the system handles missing SDOH data gracefully by using
regional averages and logs errors with source identification.
"""

import pytest
from datetime import datetime
from app.services.data_integration import (
    DataIntegrationLayer,
    DataValidationError
)
from app.models.patient import (
    Address,
    Demographics,
    ClinicalRecord,
    AdministrativeRecord,
    SDOHRecord,
    UnifiedPatientRecord,
)


@pytest.fixture
def data_integration_layer():
    """Create DataIntegrationLayer instance for testing."""
    return DataIntegrationLayer()


@pytest.fixture
def sample_demographics():
    """Sample demographics data."""
    return Demographics(
        age=65,
        sex='M',
        race='White',
        ethnicity='Non-Hispanic',
        address=Address(
            street='123 Main St',
            city='Springfield',
            state='IL',
            zip_code='62701',
            zcta='62701'
        )
    )


@pytest.fixture
def sample_clinical():
    """Sample clinical record."""
    return ClinicalRecord(
        egfr=45.5,
        egfr_history=[],
        uacr=150.0,
        hba1c=7.2,
        systolic_bp=140,
        diastolic_bp=85,
        bmi=28.5,
        medications=[],
        ckd_stage='3a',
        diagnosis_date=datetime(2022, 1, 15),
        comorbidities=['Diabetes', 'Hypertension']
    )


@pytest.fixture
def sample_administrative():
    """Sample administrative record."""
    return AdministrativeRecord(
        visit_frequency_12mo=8,
        specialist_referrals=[],
        insurance_type='Medicare',
        insurance_status='Active',
        last_visit_date=datetime(2023, 11, 15)
    )


class TestSDOHFallbackToRegionalAverages:
    """Test SDOH fallback to regional averages when data is unavailable."""
    
    def test_harmonize_with_none_sdoh_uses_regional_averages(
        self,
        data_integration_layer,
        sample_demographics,
        sample_clinical,
        sample_administrative
    ):
        """Test that harmonization with None SDOH uses regional averages."""
        # Harmonize with None SDOH
        unified_record = data_integration_layer.harmonize_patient_record(
            patient_id='test-patient-001',
            demographics=sample_demographics,
            clinical=sample_clinical,
            administrative=sample_administrative,
            sdoh=None  # Missing SDOH data
        )
        
        # Verify unified record is created
        assert isinstance(unified_record, UnifiedPatientRecord)
        assert unified_record.patient_id == 'test-patient-001'
        
        # Verify SDOH data is populated with regional averages
        assert unified_record.sdoh is not None
        assert isinstance(unified_record.sdoh, SDOHRecord)
        
        # Verify SDOH fields are valid
        assert 1 <= unified_record.sdoh.adi_percentile <= 100
        assert isinstance(unified_record.sdoh.food_desert, bool)
        assert 0.0 <= unified_record.sdoh.housing_stability_score <= 1.0
        assert 0.0 <= unified_record.sdoh.transportation_access_score <= 1.0
        assert unified_record.sdoh.rural_urban_code in ['rural', 'urban']
    
    def test_regional_averages_vary_by_state(self, data_integration_layer):
        """Test that regional averages differ by state."""
        # Illinois address
        il_address = Address(
            street='123 Main St',
            city='Chicago',
            state='IL',
            zip_code='60601',
            zcta='60601'
        )
        il_sdoh = data_integration_layer._get_regional_average_sdoh(il_address)
        
        # Mississippi address (higher deprivation)
        ms_address = Address(
            street='456 Oak St',
            city='Jackson',
            state='MS',
            zip_code='39201',
            zcta='39201'
        )
        ms_sdoh = data_integration_layer._get_regional_average_sdoh(ms_address)
        
        # Mississippi should have higher ADI (more disadvantaged)
        assert ms_sdoh.adi_percentile > il_sdoh.adi_percentile
        
        # Mississippi should have lower housing and transportation scores
        assert ms_sdoh.housing_stability_score < il_sdoh.housing_stability_score
        assert ms_sdoh.transportation_access_score < il_sdoh.transportation_access_score
    
    def test_regional_averages_use_national_fallback_for_unknown_state(
        self,
        data_integration_layer
    ):
        """Test that unknown states use national averages."""
        # Unknown state
        unknown_address = Address(
            street='123 Main St',
            city='Unknown City',
            state='ZZ',  # Not in state averages
            zip_code='00000',
            zcta='00000'
        )
        sdoh = data_integration_layer._get_regional_average_sdoh(unknown_address)
        
        # Should use national averages
        assert sdoh.adi_percentile == 50  # National average
        assert sdoh.food_desert == False
        assert sdoh.housing_stability_score == 0.60
        assert sdoh.transportation_access_score == 0.60
    
    def test_regional_averages_handle_none_address(self, data_integration_layer):
        """Test that None address uses national averages."""
        sdoh = data_integration_layer._get_regional_average_sdoh(None)
        
        # Should use national averages
        assert sdoh.adi_percentile == 50
        assert sdoh.food_desert == False
        assert sdoh.housing_stability_score == 0.60
        assert sdoh.transportation_access_score == 0.60
    
    def test_ingest_patient_data_with_sdoh_failure_uses_fallback(
        self,
        data_integration_layer,
        monkeypatch
    ):
        """Test that SDOH retrieval failure triggers regional average fallback."""
        # Mock retrieve_sdoh_data to raise an error
        def mock_retrieve_sdoh_data(address):
            raise DataValidationError("SDOH provider unavailable")
        
        monkeypatch.setattr(
            data_integration_layer,
            'retrieve_sdoh_data',
            mock_retrieve_sdoh_data
        )
        
        # Prepare test data
        patient_id = 'test-patient-002'
        demographics_payload = {
            'age': 70,
            'sex': 'F',
            'race': 'Black',
            'ethnicity': 'Non-Hispanic'
        }
        address = Address(
            street='789 Rural Rd',
            city='Small Town',
            state='AL',
            zip_code='35004',
            zcta='35004'
        )
        ehr_payload = {
            'egfr': 38.0,
            'uacr': 250.0,
            'hba1c': 7.8,
            'systolic_bp': 150,
            'diastolic_bp': 90,
            'bmi': 30.0,
            'ckd_stage': '3b',
            'diagnosis_date': '2020-01-01',
            'egfr_history': [],
            'medications': [],
            'comorbidities': ['Diabetes']
        }
        admin_payload = {
            'visit_frequency_12mo': 6,
            'insurance_type': 'Medicaid',
            'insurance_status': 'Active',
            'last_visit_date': '2023-12-01',
            'specialist_referrals': []
        }
        
        # Ingest patient data (should not raise error despite SDOH failure)
        unified_record = data_integration_layer.ingest_patient_data(
            patient_id=patient_id,
            demographics_payload=demographics_payload,
            ehr_payload=ehr_payload,
            admin_payload=admin_payload,
            address=address
        )
        
        # Verify record is created with regional average SDOH
        assert isinstance(unified_record, UnifiedPatientRecord)
        assert unified_record.patient_id == patient_id
        assert unified_record.sdoh is not None
        
        # Alabama should have high ADI (disadvantaged state)
        assert unified_record.sdoh.adi_percentile >= 60
        assert unified_record.sdoh.rural_urban_code == 'rural'
    
    def test_error_logging_includes_source_identification(
        self,
        data_integration_layer,
        sample_demographics,
        sample_clinical,
        sample_administrative,
        caplog
    ):
        """Test that error logs include source identification."""
        import logging
        
        # Set log level to capture warnings
        caplog.set_level(logging.WARNING)
        
        # Harmonize with None SDOH
        unified_record = data_integration_layer.harmonize_patient_record(
            patient_id='test-patient-003',
            demographics=sample_demographics,
            clinical=sample_clinical,
            administrative=sample_administrative,
            sdoh=None
        )
        
        # Verify warning was logged with source identification
        assert any('SDOH data unavailable' in record.message for record in caplog.records)
        assert any('Source: SDOH provider' in record.message for record in caplog.records)
        assert any('regional averages' in record.message for record in caplog.records)


class TestErrorLoggingWithSourceIdentification:
    """Test that all errors are logged with source identification."""
    
    def test_clinical_data_error_includes_source(
        self,
        data_integration_layer,
        caplog
    ):
        """Test that clinical data errors include source identification."""
        import logging
        caplog.set_level(logging.ERROR)
        
        # Invalid clinical payload
        invalid_payload = {'egfr': 'invalid'}
        
        with pytest.raises(DataValidationError):
            data_integration_layer.ingest_clinical_data(invalid_payload)
        
        # Verify error log includes source
        assert any('clinical' in record.message.lower() for record in caplog.records)
    
    def test_administrative_data_error_includes_source(
        self,
        data_integration_layer,
        caplog
    ):
        """Test that administrative data errors include source identification."""
        import logging
        caplog.set_level(logging.ERROR)
        
        # Invalid administrative payload
        invalid_payload = {'visit_frequency_12mo': 'invalid'}
        
        with pytest.raises(DataValidationError):
            data_integration_layer.ingest_administrative_data(invalid_payload)
        
        # Verify error log includes source
        assert any('administrative' in record.message.lower() for record in caplog.records)
    
    def test_sdoh_data_error_includes_source(
        self,
        data_integration_layer,
        caplog
    ):
        """Test that SDOH data errors include source identification."""
        import logging
        caplog.set_level(logging.ERROR)
        
        # Invalid address (None)
        with pytest.raises(DataValidationError):
            data_integration_layer.retrieve_sdoh_data(None)
        
        # Verify error log includes source
        assert any('address' in record.message.lower() for record in caplog.records)
