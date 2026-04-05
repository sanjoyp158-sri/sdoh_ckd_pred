"""
Property-based tests for Case Manager Enrollment.
Tests universal correctness properties using Hypothesis.
"""

import pytest
from hypothesis import given, strategies as st, settings as hyp_settings
from datetime import datetime

from app.services.case_manager_enrollment import (
    CaseManagerEnrollment,
    CaseManager
)
from app.models.patient import (
    UnifiedPatientRecord,
    Demographics,
    ClinicalRecord,
    AdministrativeRecord,
    SDOHRecord,
    Address
)


# Custom strategies
@st.composite
def patient_strategy(draw):
    """Generate valid patient records."""
    patient_id = draw(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))))
    
    return UnifiedPatientRecord(
        patient_id=patient_id,
        demographics=Demographics(
            age=draw(st.integers(min_value=18, max_value=100)),
            sex=draw(st.sampled_from(["M", "F"])),
            address=Address(
                zip_code=draw(st.text(min_size=5, max_size=5, alphabet=st.characters(whitelist_categories=('Nd',)))),
                state=draw(st.text(min_size=2, max_size=2, alphabet=st.characters(whitelist_categories=('Lu',))))
            )
        ),
        clinical=ClinicalRecord(
            egfr=draw(st.floats(min_value=10.0, max_value=120.0)),
            egfr_history=[],
            uacr=draw(st.floats(min_value=0.0, max_value=3000.0)),
            hba1c=draw(st.floats(min_value=4.0, max_value=14.0)),
            systolic_bp=draw(st.integers(min_value=80, max_value=200)),
            diastolic_bp=draw(st.integers(min_value=40, max_value=120)),
            bmi=draw(st.floats(min_value=15.0, max_value=50.0)),
            medications=[],
            ckd_stage=draw(st.sampled_from(["2", "3a", "3b", "4"])),
            diagnosis_date=datetime.now(),
            comorbidities=[]
        ),
        administrative=AdministrativeRecord(
            visit_frequency_12mo=draw(st.integers(min_value=0, max_value=50)),
            specialist_referrals=[],
            insurance_type=draw(st.sampled_from(["Medicare", "Medicaid", "Private", "Uninsured"])),
            insurance_status="Active",
            last_visit_date=datetime.now()
        ),
        sdoh=SDOHRecord(
            adi_percentile=draw(st.integers(min_value=1, max_value=100)),
            food_desert=draw(st.booleans()),
            housing_stability_score=draw(st.floats(min_value=0.0, max_value=1.0)),
            transportation_access_score=draw(st.floats(min_value=0.0, max_value=1.0)),
            rural_urban_code=draw(st.sampled_from(["urban", "suburban", "rural"]))
        ),
        created_at=datetime.now(),
        updated_at=datetime.now()
    )


@pytest.mark.property_test
class TestProperty33_CaseManagerAssignmentByCapacity:
    """
    Property 33: Case Manager Assignment by Capacity
    
    For any high-risk patient enrollment, the patient should be assigned to a 
    case manager with available capacity (current caseload < 50).
    
    **Validates: Requirements 9.1**
    """
    
    @given(patient=patient_strategy())
    @hyp_settings(max_examples=50, deadline=None)
    def test_assignment_by_capacity(self, patient):
        """Test that patients are assigned to managers with capacity."""
        enrollment = CaseManagerEnrollment()
        
        # Property 1: Should assign to manager with capacity
        manager = enrollment.assign_case_manager(patient)
        
        if manager is not None:
            # Property 2: Assigned manager should have capacity
            assert manager.has_capacity() is True
            assert manager.current_caseload < manager.max_caseload
        
        # Property 3: When all managers at capacity, assignment should fail
        for mgr in enrollment.case_managers:
            mgr.current_caseload = mgr.max_caseload
        
        manager_no_capacity = enrollment.assign_case_manager(patient)
        assert manager_no_capacity is None


@pytest.mark.property_test
class TestProperty34_CaseRecordCompleteness:
    """
    Property 34: Case Record Completeness
    
    For any case manager enrollment, the case record should contain patient 
    demographics, risk factors, and SDOH barriers.
    
    **Validates: Requirements 9.2**
    """
    
    @given(
        patient=patient_strategy(),
        risk_score=st.floats(min_value=0.66, max_value=1.0)
    )
    @hyp_settings(max_examples=50, deadline=None)
    def test_case_record_completeness(self, patient, risk_score):
        """Test that case records contain all required information."""
        enrollment = CaseManagerEnrollment()
        
        # Enroll patient
        case_record = enrollment.enroll_patient(patient, risk_score)
        
        if case_record is not None:
            # Property 1: Case record should have demographics
            assert case_record.demographics is not None
            assert "age" in case_record.demographics
            assert "sex" in case_record.demographics
            assert "zip_code" in case_record.demographics
            assert "state" in case_record.demographics
            
            # Property 2: Case record should have risk factors
            assert case_record.risk_factors is not None
            assert "risk_score" in case_record.risk_factors
            assert "egfr" in case_record.risk_factors
            assert "ckd_stage" in case_record.risk_factors
            
            # Property 3: Case record should have SDOH barriers
            assert case_record.sdoh_barriers is not None
            assert "adi_percentile" in case_record.sdoh_barriers
            assert "food_desert" in case_record.sdoh_barriers
            assert "housing_stability_score" in case_record.sdoh_barriers
            assert "transportation_access_score" in case_record.sdoh_barriers


@pytest.mark.property_test
class TestProperty35_CaseManagerNotificationTiming:
    """
    Property 35: Case Manager Notification Timing
    
    For any patient enrollment, the assigned case manager should be notified 
    within 24 hours.
    
    **Validates: Requirements 9.3**
    """
    
    @given(
        patient=patient_strategy(),
        risk_score=st.floats(min_value=0.66, max_value=1.0)
    )
    @hyp_settings(max_examples=50, deadline=None)
    def test_notification_timing(self, patient, risk_score):
        """Test that case manager is notified within 24 hours."""
        enrollment = CaseManagerEnrollment()
        
        # Property 1: Notification window should be 24 hours
        assert enrollment.notification_window_hours == 24
        
        # Enroll patient
        case_record = enrollment.enroll_patient(patient, risk_score)
        
        if case_record is not None:
            # Property 2: Notification should be sent
            assert case_record.notification_sent is True
            
            # Property 3: Notification timestamp should be set
            assert case_record.notification_sent_at is not None
            
            # Property 4: Notification should be sent immediately (within seconds)
            time_diff = (case_record.notification_sent_at - case_record.created_at).total_seconds()
            assert time_diff < 5.0, f"Notification took {time_diff}s"


@pytest.mark.property_test
class TestProperty36_CaseRecordSHAPInclusion:
    """
    Property 36: Case Record SHAP Inclusion
    
    For any case record created, it should include SHAP explanation factors 
    to guide case manager interventions.
    
    **Validates: Requirements 9.4**
    """
    
    @given(
        patient=patient_strategy(),
        risk_score=st.floats(min_value=0.66, max_value=1.0)
    )
    @hyp_settings(max_examples=50, deadline=None)
    def test_shap_inclusion(self, patient, risk_score):
        """Test that case records include SHAP factors."""
        enrollment = CaseManagerEnrollment()
        
        # Create SHAP factors
        shap_factors = [
            {"feature": "eGFR", "value": -0.5, "impact": "high"},
            {"feature": "ADI", "value": 0.3, "impact": "medium"},
            {"feature": "UACR", "value": 0.2, "impact": "medium"}
        ]
        
        # Enroll patient with SHAP factors
        case_record = enrollment.enroll_patient(patient, risk_score, shap_factors)
        
        if case_record is not None:
            # Property 1: Case record should have SHAP factors field
            assert hasattr(case_record, "shap_factors")
            
            # Property 2: SHAP factors should be included when provided
            assert case_record.shap_factors is not None
            assert len(case_record.shap_factors) == 3
            
            # Property 3: SHAP factors should contain feature information
            for factor in case_record.shap_factors:
                assert "feature" in factor
                assert "value" in factor


@pytest.mark.property_test
class TestProperty37_CaseManagerCaseloadLimit:
    """
    Property 37: Case Manager Caseload Limit
    
    For any case manager at any time, their active high-risk patient caseload 
    should not exceed 50 patients.
    
    **Validates: Requirements 9.5**
    """
    
    @given(patient=patient_strategy())
    @hyp_settings(max_examples=30, deadline=None)
    def test_caseload_limit(self, patient):
        """Test that case manager caseload never exceeds limit."""
        enrollment = CaseManagerEnrollment()
        
        # Property 1: Max caseload should be 50
        assert enrollment.max_caseload_per_manager == 50
        
        # Property 2: All case managers should have max caseload of 50
        for manager in enrollment.case_managers:
            assert manager.max_caseload == 50
        
        # Property 3: Case manager should not accept patients beyond limit
        test_manager = CaseManager("test_cm", "Test Manager", max_caseload=2)
        
        # Add patients up to limit
        assert test_manager.add_patient() is True
        assert test_manager.current_caseload == 1
        
        assert test_manager.add_patient() is True
        assert test_manager.current_caseload == 2
        
        # Should fail when at limit
        assert test_manager.add_patient() is False
        assert test_manager.current_caseload == 2  # Should not exceed
        
        # Property 4: has_capacity should return False at limit
        assert test_manager.has_capacity() is False
