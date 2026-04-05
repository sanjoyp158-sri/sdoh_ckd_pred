"""
Unit tests for Case Manager Enrollment.
"""

import pytest
from datetime import datetime

from app.services.case_manager_enrollment import (
    CaseManagerEnrollment,
    CaseManager,
    CaseRecord
)
from app.models.patient import (
    UnifiedPatientRecord,
    Demographics,
    ClinicalRecord,
    AdministrativeRecord,
    SDOHRecord,
    Address
)


@pytest.fixture
def sample_patient():
    """Create a sample patient record."""
    return UnifiedPatientRecord(
        patient_id="test_001",
        demographics=Demographics(
            age=65,
            sex="M",
            address=Address(zip_code="12345", state="NY")
        ),
        clinical=ClinicalRecord(
            egfr=25.0,
            egfr_history=[],
            uacr=350.0,
            hba1c=8.5,
            systolic_bp=155,
            diastolic_bp=95,
            bmi=34.0,
            medications=[],
            ckd_stage="4",
            diagnosis_date=datetime.now(),
            comorbidities=["diabetes", "hypertension"]
        ),
        administrative=AdministrativeRecord(
            visit_frequency_12mo=2,
            specialist_referrals=[],
            insurance_type="Medicare",
            insurance_status="Active",
            last_visit_date=datetime.now()
        ),
        sdoh=SDOHRecord(
            adi_percentile=90,
            food_desert=True,
            housing_stability_score=0.3,
            transportation_access_score=0.4,
            rural_urban_code="rural"
        ),
        created_at=datetime.now(),
        updated_at=datetime.now()
    )


class TestCaseManager:
    """Test CaseManager class."""
    
    def test_case_manager_creation(self):
        """Test creating a case manager."""
        manager = CaseManager("cm_001", "Sarah Johnson", max_caseload=50)
        
        assert manager.manager_id == "cm_001"
        assert manager.name == "Sarah Johnson"
        assert manager.max_caseload == 50
        assert manager.current_caseload == 0
    
    def test_has_capacity(self):
        """Test checking case manager capacity."""
        manager = CaseManager("cm_001", "Sarah Johnson", max_caseload=2)
        
        assert manager.has_capacity() is True
        
        manager.add_patient()
        assert manager.has_capacity() is True
        
        manager.add_patient()
        assert manager.has_capacity() is False
    
    def test_add_patient(self):
        """Test adding patient to caseload."""
        manager = CaseManager("cm_001", "Sarah Johnson", max_caseload=2)
        
        success1 = manager.add_patient()
        assert success1 is True
        assert manager.current_caseload == 1
        
        success2 = manager.add_patient()
        assert success2 is True
        assert manager.current_caseload == 2
        
        # Should fail when at capacity
        success3 = manager.add_patient()
        assert success3 is False
        assert manager.current_caseload == 2


class TestCaseRecord:
    """Test CaseRecord class."""
    
    def test_case_record_creation(self):
        """Test creating a case record."""
        demographics = {"age": 65, "sex": "M"}
        risk_factors = {"risk_score": 0.85, "egfr": 25.0}
        sdoh_barriers = {"adi_percentile": 90, "food_desert": True}
        
        record = CaseRecord(
            case_id="case_001",
            patient_id="test_001",
            manager_id="cm_001",
            demographics=demographics,
            risk_factors=risk_factors,
            sdoh_barriers=sdoh_barriers
        )
        
        assert record.case_id == "case_001"
        assert record.patient_id == "test_001"
        assert record.manager_id == "cm_001"
        assert record.demographics == demographics
        assert record.risk_factors == risk_factors
        assert record.sdoh_barriers == sdoh_barriers
        assert record.notification_sent is False


class TestCaseManagerEnrollment:
    """Test Case Manager Enrollment."""
    
    def test_enrollment_initialization(self):
        """Test enrollment service initialization."""
        enrollment = CaseManagerEnrollment()
        
        assert len(enrollment.case_managers) > 0
        assert len(enrollment.case_records) == 0
        assert enrollment.max_caseload_per_manager == 50
        assert enrollment.notification_window_hours == 24
    
    def test_assign_case_manager(self, sample_patient):
        """Test assigning case manager to patient."""
        enrollment = CaseManagerEnrollment()
        
        manager = enrollment.assign_case_manager(sample_patient)
        
        assert manager is not None
        assert isinstance(manager, CaseManager)
    
    def test_assign_case_manager_no_capacity(self, sample_patient):
        """Test assignment when no capacity available."""
        enrollment = CaseManagerEnrollment()
        
        # Fill all case managers to capacity
        for manager in enrollment.case_managers:
            manager.current_caseload = manager.max_caseload
        
        manager = enrollment.assign_case_manager(sample_patient)
        
        assert manager is None
    
    def test_create_case_record(self, sample_patient):
        """Test creating case record."""
        enrollment = CaseManagerEnrollment()
        manager = enrollment.case_managers[0]
        
        shap_factors = [
            {"feature": "eGFR", "value": -0.5},
            {"feature": "ADI", "value": 0.3}
        ]
        
        record = enrollment.create_case_record(
            patient=sample_patient,
            manager=manager,
            risk_score=0.85,
            shap_factors=shap_factors
        )
        
        assert record is not None
        assert record.patient_id == "test_001"
        assert record.manager_id == manager.manager_id
        assert record.demographics["age"] == 65
        assert record.risk_factors["risk_score"] == 0.85
        assert record.sdoh_barriers["adi_percentile"] == 90
        assert len(record.shap_factors) == 2
    
    def test_notify_case_manager(self, sample_patient):
        """Test notifying case manager."""
        enrollment = CaseManagerEnrollment()
        manager = enrollment.case_managers[0]
        
        record = enrollment.create_case_record(
            patient=sample_patient,
            manager=manager,
            risk_score=0.85
        )
        
        success = enrollment.notify_case_manager(record, manager)
        
        assert success is True
        assert record.notification_sent is True
        assert record.notification_sent_at is not None
    
    def test_enroll_patient_complete_workflow(self, sample_patient):
        """Test complete enrollment workflow."""
        enrollment = CaseManagerEnrollment()
        
        shap_factors = [
            {"feature": "eGFR", "value": -0.5},
            {"feature": "ADI", "value": 0.3}
        ]
        
        record = enrollment.enroll_patient(
            patient=sample_patient,
            risk_score=0.85,
            shap_factors=shap_factors
        )
        
        assert record is not None
        assert record.patient_id == "test_001"
        assert record.notification_sent is True
        assert len(enrollment.case_records) == 1
    
    def test_get_case_record(self, sample_patient):
        """Test retrieving case record by ID."""
        enrollment = CaseManagerEnrollment()
        
        record = enrollment.enroll_patient(sample_patient, 0.85)
        
        retrieved = enrollment.get_case_record(record.case_id)
        
        assert retrieved == record
    
    def test_get_patient_case_records(self, sample_patient):
        """Test retrieving all case records for a patient."""
        enrollment = CaseManagerEnrollment()
        
        record1 = enrollment.enroll_patient(sample_patient, 0.85)
        record2 = enrollment.enroll_patient(sample_patient, 0.90)
        
        patient_records = enrollment.get_patient_case_records("test_001")
        
        assert len(patient_records) == 2
        assert record1 in patient_records
        assert record2 in patient_records
    
    def test_get_manager_case_records(self, sample_patient):
        """Test retrieving all case records for a manager."""
        enrollment = CaseManagerEnrollment()
        
        record = enrollment.enroll_patient(sample_patient, 0.85)
        
        manager_records = enrollment.get_manager_case_records(record.manager_id)
        
        assert len(manager_records) >= 1
        assert record in manager_records
