"""
Unit tests for Data Integration Layer.

Tests data ingestion from EHR, administrative systems, and SDOH providers.
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
def sample_ehr_payload():
    """Sample EHR payload with all required fields."""
    return {
        'egfr': 45.5,
        'uacr': 150.0,
        'hba1c': 7.2,
        'systolic_bp': 140,
        'diastolic_bp': 85,
        'bmi': 28.5,
        'ckd_stage': '3a',
        'diagnosis_date': '2022-01-15',
        'egfr_history': [
            {'date': '2021-06-01', 'value': 52.0},
            {'date': '2021-12-01', 'value': 48.0},
            {'date': '2022-06-01', 'value': 45.5}
        ],
        'medications': [
            {
                'name': 'Lisinopril',
                'category': 'ACE_inhibitor',
                'start_date': '2021-01-01',
                'active': True
            },
            {
                'name': 'Metformin',
                'category': 'Diabetes',
                'start_date': '2020-06-01',
                'active': True
            }
        ],
        'comorbidities': ['Diabetes', 'Hypertension']
    }


@pytest.fixture
def sample_admin_payload():
    """Sample administrative payload with all required fields."""
    return {
        'visit_frequency_12mo': 8,
        'insurance_type': 'Medicare',
        'insurance_status': 'Active',
        'last_visit_date': '2023-11-15',
        'specialist_referrals': [
            {
                'specialty': 'Nephrology',
                'date': '2023-06-01',
                'completed': True,
                'reason': 'CKD management'
            },
            {
                'specialty': 'Cardiology',
                'date': '2023-09-15',
                'completed': False,
                'reason': 'Hypertension'
            }
        ]
    }


@pytest.fixture
def sample_address():
    """Sample patient address."""
    return Address(
        street='123 Main St',
        city='Springfield',
        state='IL',
        zip_code='62701',
        zcta='62701'
    )


@pytest.fixture
def sample_demographics():
    """Sample demographics data."""
    return {
        'age': 65,
        'sex': 'M',
        'race': 'White',
        'ethnicity': 'Non-Hispanic'
    }


class TestClinicalDataIngestion:
    """Test clinical data ingestion from EHR systems."""
    
    def test_ingest_clinical_data_success(self, data_integration_layer, sample_ehr_payload):
        """Test successful ingestion of complete clinical data."""
        clinical_record = data_integration_layer.ingest_clinical_data(sample_ehr_payload)
        
        assert isinstance(clinical_record, ClinicalRecord)
        assert clinical_record.egfr == 45.5
        assert clinical_record.uacr == 150.0
        assert clinical_record.hba1c == 7.2
        assert clinical_record.systolic_bp == 140
        assert clinical_record.diastolic_bp == 85
        assert clinical_record.bmi == 28.5
        assert clinical_record.ckd_stage == '3a'
        assert len(clinical_record.medications) == 2
        assert len(clinical_record.egfr_history) == 3
        assert 'Diabetes' in clinical_record.comorbidities
    
    def test_ingest_clinical_data_missing_required_field(self, data_integration_layer):
        """Test that missing required fields raise DataValidationError."""
        incomplete_payload = {
            'egfr': 45.5,
            'uacr': 150.0,
            # Missing hba1c, blood pressure, bmi, etc.
        }
        
        with pytest.raises(DataValidationError) as exc_info:
            data_integration_layer.ingest_clinical_data(incomplete_payload)
        
        assert 'Missing required clinical fields' in str(exc_info.value)
    
    def test_ingest_clinical_data_without_medications(self, data_integration_layer, sample_ehr_payload):
        """Test ingestion when medications list is empty."""
        sample_ehr_payload['medications'] = []
        
        clinical_record = data_integration_layer.ingest_clinical_data(sample_ehr_payload)
        
        assert isinstance(clinical_record, ClinicalRecord)
        assert len(clinical_record.medications) == 0
    
    def test_ingest_clinical_data_without_egfr_history(self, data_integration_layer, sample_ehr_payload):
        """Test ingestion when eGFR history is not provided."""
        sample_ehr_payload['egfr_history'] = []
        
        clinical_record = data_integration_layer.ingest_clinical_data(sample_ehr_payload)
        
        assert isinstance(clinical_record, ClinicalRecord)
        assert len(clinical_record.egfr_history) == 0
    
    def test_ingest_clinical_data_invalid_type(self, data_integration_layer, sample_ehr_payload):
        """Test that invalid data types raise DataValidationError."""
        sample_ehr_payload['egfr'] = 'invalid'  # Should be float
        
        with pytest.raises(DataValidationError):
            data_integration_layer.ingest_clinical_data(sample_ehr_payload)


class TestAdministrativeDataIngestion:
    """Test administrative data ingestion from billing systems."""
    
    def test_ingest_administrative_data_success(self, data_integration_layer, sample_admin_payload):
        """Test successful ingestion of complete administrative data."""
        admin_record = data_integration_layer.ingest_administrative_data(sample_admin_payload)
        
        assert isinstance(admin_record, AdministrativeRecord)
        assert admin_record.visit_frequency_12mo == 8
        assert admin_record.insurance_type == 'Medicare'
        assert admin_record.insurance_status == 'Active'
        assert len(admin_record.specialist_referrals) == 2
        assert admin_record.specialist_referrals[0].specialty == 'Nephrology'
    
    def test_ingest_administrative_data_missing_required_field(self, data_integration_layer):
        """Test that missing required fields raise DataValidationError."""
        incomplete_payload = {
            'visit_frequency_12mo': 8,
            # Missing insurance_type, insurance_status, last_visit_date
        }
        
        with pytest.raises(DataValidationError) as exc_info:
            data_integration_layer.ingest_administrative_data(incomplete_payload)
        
        assert 'Missing required administrative fields' in str(exc_info.value)
    
    def test_ingest_administrative_data_without_referrals(self, data_integration_layer, sample_admin_payload):
        """Test ingestion when referrals list is empty."""
        sample_admin_payload['specialist_referrals'] = []
        
        admin_record = data_integration_layer.ingest_administrative_data(sample_admin_payload)
        
        assert isinstance(admin_record, AdministrativeRecord)
        assert len(admin_record.specialist_referrals) == 0
    
    def test_ingest_administrative_data_invalid_type(self, data_integration_layer, sample_admin_payload):
        """Test that invalid data types raise DataValidationError."""
        sample_admin_payload['visit_frequency_12mo'] = 'invalid'  # Should be int
        
        with pytest.raises(DataValidationError):
            data_integration_layer.ingest_administrative_data(sample_admin_payload)


class TestSDOHDataRetrieval:
    """Test SDOH data retrieval from external providers."""
    
    def test_retrieve_sdoh_data_success(self, data_integration_layer, sample_address):
        """Test successful retrieval of SDOH data."""
        sdoh_record = data_integration_layer.retrieve_sdoh_data(sample_address)
        
        assert isinstance(sdoh_record, SDOHRecord)
        assert 1 <= sdoh_record.adi_percentile <= 100
        assert isinstance(sdoh_record.food_desert, bool)
        assert 0.0 <= sdoh_record.housing_stability_score <= 1.0
        assert 0.0 <= sdoh_record.transportation_access_score <= 1.0
        assert sdoh_record.rural_urban_code is not None
    
    def test_retrieve_sdoh_data_missing_address(self, data_integration_layer):
        """Test that missing address raises DataValidationError."""
        with pytest.raises(DataValidationError) as exc_info:
            data_integration_layer.retrieve_sdoh_data(None)
        
        assert 'address' in str(exc_info.value).lower()
    
    def test_retrieve_sdoh_data_missing_zip_code(self, data_integration_layer):
        """Test that missing ZIP code raises DataValidationError."""
        invalid_address = Address(
            street='123 Main St',
            city='Springfield',
            state='IL',
            zip_code=None  # Missing ZIP code
        )
        
        with pytest.raises(DataValidationError) as exc_info:
            data_integration_layer.retrieve_sdoh_data(invalid_address)
        
        assert 'zip' in str(exc_info.value).lower()


class TestDataHarmonization:
    """Test data harmonization into unified patient records."""
    
    def test_harmonize_patient_record_success(
        self,
        data_integration_layer,
        sample_demographics,
        sample_ehr_payload,
        sample_admin_payload,
        sample_address
    ):
        """Test successful harmonization of all data sources."""
        # Create individual records
        demographics = Demographics(
            age=sample_demographics['age'],
            sex=sample_demographics['sex'],
            race=sample_demographics['race'],
            ethnicity=sample_demographics['ethnicity'],
            address=sample_address
        )
        clinical = data_integration_layer.ingest_clinical_data(sample_ehr_payload)
        administrative = data_integration_layer.ingest_administrative_data(sample_admin_payload)
        sdoh = data_integration_layer.retrieve_sdoh_data(sample_address)
        
        # Harmonize
        unified_record = data_integration_layer.harmonize_patient_record(
            patient_id='test-patient-123',
            demographics=demographics,
            clinical=clinical,
            administrative=administrative,
            sdoh=sdoh
        )
        
        assert isinstance(unified_record, UnifiedPatientRecord)
        assert unified_record.patient_id == 'test-patient-123'
        assert unified_record.demographics == demographics
        assert unified_record.clinical == clinical
        assert unified_record.administrative == administrative
        assert unified_record.sdoh == sdoh
        assert isinstance(unified_record.created_at, datetime)
        assert isinstance(unified_record.updated_at, datetime)
    
    def test_harmonize_patient_record_timestamps(
        self,
        data_integration_layer,
        sample_demographics,
        sample_ehr_payload,
        sample_admin_payload,
        sample_address
    ):
        """Test that harmonization sets created_at and updated_at timestamps."""
        demographics = Demographics(
            age=sample_demographics['age'],
            sex=sample_demographics['sex'],
            address=sample_address
        )
        clinical = data_integration_layer.ingest_clinical_data(sample_ehr_payload)
        administrative = data_integration_layer.ingest_administrative_data(sample_admin_payload)
        sdoh = data_integration_layer.retrieve_sdoh_data(sample_address)
        
        before = datetime.utcnow()
        unified_record = data_integration_layer.harmonize_patient_record(
            patient_id='test-patient-123',
            demographics=demographics,
            clinical=clinical,
            administrative=administrative,
            sdoh=sdoh
        )
        after = datetime.utcnow()
        
        assert before <= unified_record.created_at <= after
        assert before <= unified_record.updated_at <= after


class TestCompleteIngestionWorkflow:
    """Test complete end-to-end data ingestion workflow."""
    
    def test_ingest_patient_data_success(
        self,
        data_integration_layer,
        sample_demographics,
        sample_ehr_payload,
        sample_admin_payload,
        sample_address
    ):
        """Test complete patient data ingestion workflow."""
        unified_record = data_integration_layer.ingest_patient_data(
            patient_id='test-patient-456',
            demographics_payload=sample_demographics,
            ehr_payload=sample_ehr_payload,
            admin_payload=sample_admin_payload,
            address=sample_address
        )
        
        assert isinstance(unified_record, UnifiedPatientRecord)
        assert unified_record.patient_id == 'test-patient-456'
        assert unified_record.demographics.age == 65
        assert unified_record.clinical.egfr == 45.5
        assert unified_record.administrative.visit_frequency_12mo == 8
        assert unified_record.sdoh.adi_percentile > 0
    
    def test_ingest_patient_data_missing_demographics(
        self,
        data_integration_layer,
        sample_ehr_payload,
        sample_admin_payload,
        sample_address
    ):
        """Test that missing demographics raises DataValidationError."""
        incomplete_demographics = {}  # Missing required fields
        
        with pytest.raises(DataValidationError):
            data_integration_layer.ingest_patient_data(
                patient_id='test-patient-789',
                demographics_payload=incomplete_demographics,
                ehr_payload=sample_ehr_payload,
                admin_payload=sample_admin_payload,
                address=sample_address
            )


class TestDateTimeParsing:
    """Test datetime parsing utility."""
    
    def test_parse_datetime_from_string(self, data_integration_layer):
        """Test parsing datetime from string."""
        date_str = '2023-01-15'
        result = data_integration_layer._parse_datetime(date_str)
        
        assert isinstance(result, datetime)
        assert result.year == 2023
        assert result.month == 1
        assert result.day == 15
    
    def test_parse_datetime_from_datetime(self, data_integration_layer):
        """Test parsing datetime from datetime object."""
        dt = datetime(2023, 1, 15, 10, 30, 0)
        result = data_integration_layer._parse_datetime(dt)
        
        assert result == dt
    
    def test_parse_datetime_from_timestamp(self, data_integration_layer):
        """Test parsing datetime from Unix timestamp."""
        timestamp = 1673784600  # 2023-01-15 10:30:00 UTC
        result = data_integration_layer._parse_datetime(timestamp)
        
        assert isinstance(result, datetime)
    
    def test_parse_datetime_invalid_format(self, data_integration_layer):
        """Test that invalid datetime format raises ValueError."""
        with pytest.raises(ValueError):
            data_integration_layer._parse_datetime('invalid-date')
