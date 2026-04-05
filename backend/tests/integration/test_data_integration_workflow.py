"""
Integration tests for complete data ingestion workflow.

Tests the end-to-end process of ingesting data from all sources
and creating unified patient records.
"""

import pytest
from datetime import datetime
from app.services.data_integration import DataIntegrationLayer
from app.models.patient import (
    Address,
    UnifiedPatientRecord,
)


@pytest.fixture
def data_integration_layer():
    """Create DataIntegrationLayer instance for testing."""
    return DataIntegrationLayer()


@pytest.fixture
def complete_patient_data():
    """Complete patient data from all sources."""
    return {
        'patient_id': 'integration-test-001',
        'demographics': {
            'age': 68,
            'sex': 'F',
            'race': 'Black',
            'ethnicity': 'Non-Hispanic'
        },
        'address': Address(
            street='456 Oak Avenue',
            city='Rural Town',
            state='MS',
            zip_code='39701',
            zcta='39701'
        ),
        'ehr_payload': {
            'egfr': 38.2,
            'uacr': 320.0,
            'hba1c': 8.1,
            'systolic_bp': 155,
            'diastolic_bp': 92,
            'bmi': 32.4,
            'ckd_stage': '3b',
            'diagnosis_date': '2020-03-10',
            'egfr_history': [
                {'date': '2020-03-10', 'value': 52.0},
                {'date': '2021-03-10', 'value': 45.0},
                {'date': '2022-03-10', 'value': 41.0},
                {'date': '2023-03-10', 'value': 38.2}
            ],
            'medications': [
                {
                    'name': 'Losartan',
                    'category': 'ARB',
                    'start_date': '2020-04-01',
                    'active': True
                },
                {
                    'name': 'Empagliflozin',
                    'category': 'SGLT2_inhibitor',
                    'start_date': '2022-01-15',
                    'active': True
                },
                {
                    'name': 'Insulin',
                    'category': 'Diabetes',
                    'start_date': '2019-06-01',
                    'active': True
                }
            ],
            'comorbidities': ['Diabetes', 'Hypertension', 'Obesity']
        },
        'admin_payload': {
            'visit_frequency_12mo': 12,
            'insurance_type': 'Medicaid',
            'insurance_status': 'Active',
            'last_visit_date': '2023-12-01',
            'specialist_referrals': [
                {
                    'specialty': 'Nephrology',
                    'date': '2023-01-15',
                    'completed': True,
                    'reason': 'CKD Stage 3b management'
                },
                {
                    'specialty': 'Endocrinology',
                    'date': '2023-06-20',
                    'completed': True,
                    'reason': 'Diabetes management'
                },
                {
                    'specialty': 'Cardiology',
                    'date': '2023-11-10',
                    'completed': False,
                    'reason': 'Hypertension evaluation'
                }
            ]
        }
    }


class TestCompleteDataIngestionWorkflow:
    """Test complete end-to-end data ingestion workflow."""
    
    def test_complete_patient_ingestion(self, data_integration_layer, complete_patient_data):
        """Test ingesting complete patient data from all sources."""
        unified_record = data_integration_layer.ingest_patient_data(
            patient_id=complete_patient_data['patient_id'],
            demographics_payload=complete_patient_data['demographics'],
            ehr_payload=complete_patient_data['ehr_payload'],
            admin_payload=complete_patient_data['admin_payload'],
            address=complete_patient_data['address']
        )
        
        # Verify unified record structure
        assert isinstance(unified_record, UnifiedPatientRecord)
        assert unified_record.patient_id == 'integration-test-001'
        
        # Verify demographics
        assert unified_record.demographics.age == 68
        assert unified_record.demographics.sex == 'F'
        assert unified_record.demographics.race == 'Black'
        assert unified_record.demographics.address.zip_code == '39701'
        
        # Verify clinical data
        assert unified_record.clinical.egfr == 38.2
        assert unified_record.clinical.uacr == 320.0
        assert unified_record.clinical.hba1c == 8.1
        assert unified_record.clinical.systolic_bp == 155
        assert unified_record.clinical.diastolic_bp == 92
        assert unified_record.clinical.bmi == 32.4
        assert unified_record.clinical.ckd_stage == '3b'
        assert len(unified_record.clinical.medications) == 3
        assert len(unified_record.clinical.egfr_history) == 4
        assert 'Diabetes' in unified_record.clinical.comorbidities
        
        # Verify administrative data
        assert unified_record.administrative.visit_frequency_12mo == 12
        assert unified_record.administrative.insurance_type == 'Medicaid'
        assert unified_record.administrative.insurance_status == 'Active'
        assert len(unified_record.administrative.specialist_referrals) == 3
        
        # Verify SDOH data
        assert 1 <= unified_record.sdoh.adi_percentile <= 100
        assert isinstance(unified_record.sdoh.food_desert, bool)
        assert 0.0 <= unified_record.sdoh.housing_stability_score <= 1.0
        assert 0.0 <= unified_record.sdoh.transportation_access_score <= 1.0
        assert unified_record.sdoh.rural_urban_code is not None
        
        # Verify timestamps
        assert isinstance(unified_record.created_at, datetime)
        assert isinstance(unified_record.updated_at, datetime)
    
    def test_high_risk_patient_profile(self, data_integration_layer):
        """Test ingestion of a high-risk patient profile."""
        # High-risk patient: low eGFR, high UACR, poor control, high ADI
        high_risk_data = {
            'patient_id': 'high-risk-001',
            'demographics': {
                'age': 72,
                'sex': 'M',
                'race': 'Hispanic',
                'ethnicity': 'Hispanic'
            },
            'address': Address(
                street='789 Rural Route',
                city='Small Town',
                state='AL',
                zip_code='35004',
                zcta='35004'
            ),
            'ehr_payload': {
                'egfr': 28.5,  # Low eGFR (Stage 4 borderline)
                'uacr': 850.0,  # Very high UACR
                'hba1c': 9.5,  # Poor diabetes control
                'systolic_bp': 165,  # Uncontrolled hypertension
                'diastolic_bp': 98,
                'bmi': 35.2,  # Obesity
                'ckd_stage': '3b',
                'diagnosis_date': '2018-06-15',
                'egfr_history': [
                    {'date': '2018-06-15', 'value': 55.0},
                    {'date': '2020-06-15', 'value': 42.0},
                    {'date': '2022-06-15', 'value': 35.0},
                    {'date': '2023-06-15', 'value': 28.5}
                ],
                'medications': [
                    {
                        'name': 'Lisinopril',
                        'category': 'ACE_inhibitor',
                        'start_date': '2018-07-01',
                        'active': True
                    }
                ],
                'comorbidities': ['Diabetes', 'Hypertension', 'CVD', 'Obesity']
            },
            'admin_payload': {
                'visit_frequency_12mo': 4,  # Low visit frequency
                'insurance_type': 'Uninsured',
                'insurance_status': 'Inactive',
                'last_visit_date': '2023-09-01',
                'specialist_referrals': []  # No specialist referrals
            }
        }
        
        unified_record = data_integration_layer.ingest_patient_data(
            patient_id=high_risk_data['patient_id'],
            demographics_payload=high_risk_data['demographics'],
            ehr_payload=high_risk_data['ehr_payload'],
            admin_payload=high_risk_data['admin_payload'],
            address=high_risk_data['address']
        )
        
        # Verify high-risk indicators
        assert unified_record.clinical.egfr < 30.0  # Stage 4 borderline
        assert unified_record.clinical.uacr > 300.0  # Severe albuminuria
        assert unified_record.clinical.hba1c > 9.0  # Poor control
        assert unified_record.administrative.visit_frequency_12mo < 6  # Low engagement
        assert unified_record.administrative.insurance_type == 'Uninsured'
        assert len(unified_record.administrative.specialist_referrals) == 0
        
        # Calculate eGFR slope (should be declining)
        egfr_history = unified_record.clinical.egfr_history
        if len(egfr_history) >= 2:
            first_egfr = egfr_history[0][1]
            last_egfr = egfr_history[-1][1]
            assert last_egfr < first_egfr  # Declining kidney function
    
    def test_low_risk_patient_profile(self, data_integration_layer):
        """Test ingestion of a low-risk patient profile."""
        # Low-risk patient: stable eGFR, low UACR, good control
        low_risk_data = {
            'patient_id': 'low-risk-001',
            'demographics': {
                'age': 58,
                'sex': 'F',
                'race': 'Asian',
                'ethnicity': 'Non-Hispanic'
            },
            'address': Address(
                street='123 Suburban Lane',
                city='Metro City',
                state='CA',
                zip_code='90001',
                zcta='90001'
            ),
            'ehr_payload': {
                'egfr': 62.0,  # Stage 2 CKD
                'uacr': 45.0,  # Mild albuminuria
                'hba1c': 6.2,  # Good diabetes control
                'systolic_bp': 128,  # Controlled blood pressure
                'diastolic_bp': 78,
                'bmi': 24.5,  # Normal weight
                'ckd_stage': '2',
                'diagnosis_date': '2021-01-10',
                'egfr_history': [
                    {'date': '2021-01-10', 'value': 60.0},
                    {'date': '2022-01-10', 'value': 61.0},
                    {'date': '2023-01-10', 'value': 62.0}
                ],
                'medications': [
                    {
                        'name': 'Lisinopril',
                        'category': 'ACE_inhibitor',
                        'start_date': '2021-02-01',
                        'active': True
                    },
                    {
                        'name': 'Metformin',
                        'category': 'Diabetes',
                        'start_date': '2020-01-01',
                        'active': True
                    }
                ],
                'comorbidities': ['Diabetes', 'Hypertension']
            },
            'admin_payload': {
                'visit_frequency_12mo': 10,  # Good engagement
                'insurance_type': 'Commercial',
                'insurance_status': 'Active',
                'last_visit_date': '2023-12-15',
                'specialist_referrals': [
                    {
                        'specialty': 'Nephrology',
                        'date': '2023-03-01',
                        'completed': True,
                        'reason': 'CKD monitoring'
                    }
                ]
            }
        }
        
        unified_record = data_integration_layer.ingest_patient_data(
            patient_id=low_risk_data['patient_id'],
            demographics_payload=low_risk_data['demographics'],
            ehr_payload=low_risk_data['ehr_payload'],
            admin_payload=low_risk_data['admin_payload'],
            address=low_risk_data['address']
        )
        
        # Verify low-risk indicators
        assert unified_record.clinical.egfr >= 60.0  # Stage 2 CKD
        assert unified_record.clinical.uacr < 300.0  # Mild albuminuria
        assert unified_record.clinical.hba1c < 7.0  # Good control
        assert unified_record.administrative.visit_frequency_12mo >= 8  # Good engagement
        assert unified_record.administrative.insurance_status == 'Active'
        
        # Calculate eGFR slope (should be stable or improving)
        egfr_history = unified_record.clinical.egfr_history
        if len(egfr_history) >= 2:
            first_egfr = egfr_history[0][1]
            last_egfr = egfr_history[-1][1]
            assert last_egfr >= first_egfr  # Stable or improving kidney function
