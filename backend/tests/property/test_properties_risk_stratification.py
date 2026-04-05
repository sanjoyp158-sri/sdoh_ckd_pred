"""
Property-based tests for Risk Stratification Module.
Tests universal correctness properties using Hypothesis.
"""

import pytest
from hypothesis import given, strategies as st, settings as hyp_settings
from datetime import datetime

from app.services.risk_stratification import RiskStratificationModule
from app.models.patient import (
    UnifiedPatientRecord,
    Demographics,
    ClinicalRecord,
    AdministrativeRecord,
    SDOHRecord,
    Address,
    RiskTier
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
            ckd_stage=draw(st.sampled_from(["1", "2", "3a", "3b", "4", "5"])),
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
class TestProperty14_RiskTierAssignmentCorrectness:
    """
    Property 14: Risk Tier Assignment Correctness
    
    For any valid risk score (0-1), the Risk Stratification Module should 
    assign the correct tier based on thresholds:
    - HIGH: score > 0.65
    - MODERATE: 0.35 <= score <= 0.65
    - LOW: score < 0.35
    """
    
    @given(
        patient=patient_strategy(),
        risk_score=st.floats(min_value=0.0, max_value=1.0)
    )
    @hyp_settings(max_examples=100, deadline=None)
    def test_tier_assignment_correctness(self, patient, risk_score):
        """Test that tier assignment follows threshold rules."""
        module = RiskStratificationModule()
        
        tier = module.stratify_patient(patient, risk_score)
        
        # Property: Tier must match threshold rules
        if risk_score > 0.65:
            assert tier == RiskTier.HIGH, f"Score {risk_score} should be HIGH"
        elif risk_score >= 0.35:
            assert tier == RiskTier.MODERATE, f"Score {risk_score} should be MODERATE"
        else:
            assert tier == RiskTier.LOW, f"Score {risk_score} should be LOW"
    
    @given(patient=patient_strategy())
    @hyp_settings(max_examples=50, deadline=None)
    def test_high_risk_threshold(self, patient):
        """Test high-risk threshold boundary."""
        module = RiskStratificationModule()
        
        # Just above threshold
        tier_high = module.stratify_patient(patient, 0.66)
        assert tier_high == RiskTier.HIGH
        
        # At threshold
        tier_moderate = module.stratify_patient(patient, 0.65)
        assert tier_moderate == RiskTier.MODERATE
    
    @given(patient=patient_strategy())
    @hyp_settings(max_examples=50, deadline=None)
    def test_moderate_risk_threshold(self, patient):
        """Test moderate-risk threshold boundary."""
        module = RiskStratificationModule()
        
        # At threshold
        tier_moderate = module.stratify_patient(patient, 0.35)
        assert tier_moderate == RiskTier.MODERATE
        
        # Just below threshold
        tier_low = module.stratify_patient(patient, 0.34)
        assert tier_low == RiskTier.LOW


@pytest.mark.property_test
class TestProperty15_RiskTierChangeLogging:
    """
    Property 15: Risk Tier Change Logging
    
    For any tier change, the Risk Stratification Module should log:
    - Patient ID
    - Previous tier and score
    - New tier and score
    - Timestamp of change
    """
    
    @given(
        patient=patient_strategy(),
        initial_score=st.floats(min_value=0.0, max_value=1.0),
        new_score=st.floats(min_value=0.0, max_value=1.0)
    )
    @hyp_settings(max_examples=100, deadline=None)
    def test_tier_change_logging_completeness(self, patient, initial_score, new_score):
        """Test that tier changes are logged with all required fields."""
        module = RiskStratificationModule()
        
        # Initial assignment
        initial_tier = module.stratify_patient(patient, initial_score)
        
        # New assignment
        new_tier = module.stratify_patient(
            patient,
            new_score,
            previous_tier=initial_tier,
            previous_score=initial_score
        )
        
        # Property: All tier assignments should be logged
        assert len(module.tier_change_log) >= 1
        
        # Check initial assignment log
        initial_log = module.tier_change_log[0]
        assert initial_log.patient_id == patient.patient_id
        assert initial_log.previous_tier is None
        assert initial_log.new_tier == initial_tier
        assert initial_log.previous_score is None
        assert initial_log.new_score == initial_score
        assert isinstance(initial_log.timestamp, datetime)
        
        # If tier changed, check change log
        if initial_tier != new_tier:
            assert len(module.tier_change_log) == 2
            change_log = module.tier_change_log[1]
            assert change_log.patient_id == patient.patient_id
            assert change_log.previous_tier == initial_tier
            assert change_log.new_tier == new_tier
            assert change_log.previous_score == initial_score
            assert change_log.new_score == new_score
            assert isinstance(change_log.timestamp, datetime)
        else:
            # No tier change, only initial assignment logged
            assert len(module.tier_change_log) == 1
    
    @given(
        patient=patient_strategy(),
        risk_score=st.floats(min_value=0.0, max_value=1.0)
    )
    @hyp_settings(max_examples=50, deadline=None)
    def test_initial_assignment_always_logged(self, patient, risk_score):
        """Test that initial tier assignment is always logged."""
        module = RiskStratificationModule()
        
        tier = module.stratify_patient(patient, risk_score)
        
        # Property: Initial assignment must be logged
        assert len(module.tier_change_log) == 1
        
        log_entry = module.tier_change_log[0]
        assert log_entry.patient_id == patient.patient_id
        assert log_entry.previous_tier is None
        assert log_entry.new_tier == tier
        assert log_entry.previous_score is None
        assert log_entry.new_score == risk_score
    
    @given(
        patient=patient_strategy(),
        score1=st.floats(min_value=0.0, max_value=0.3),  # Will be LOW
        score2=st.floats(min_value=0.7, max_value=1.0)   # Will be HIGH
    )
    @hyp_settings(max_examples=50, deadline=None)
    def test_tier_change_always_logged(self, patient, score1, score2):
        """Test that tier changes are always logged."""
        module = RiskStratificationModule()
        
        # Initial assignment (LOW)
        tier1 = module.stratify_patient(patient, score1)
        
        # Change to HIGH
        tier2 = module.stratify_patient(
            patient,
            score2,
            previous_tier=tier1,
            previous_score=score1
        )
        
        # Property: Both assignments should be logged
        assert len(module.tier_change_log) == 2
        assert tier1 == RiskTier.LOW
        assert tier2 == RiskTier.HIGH
    
    @given(
        patient=patient_strategy(),
        risk_score=st.floats(min_value=0.0, max_value=1.0)
    )
    @hyp_settings(max_examples=50, deadline=None)
    def test_get_tier_change_history(self, patient, risk_score):
        """Test retrieving tier change history for a patient."""
        module = RiskStratificationModule()
        
        tier = module.stratify_patient(patient, risk_score)
        
        history = module.get_tier_change_history(patient.patient_id)
        
        # Property: History should contain all changes for the patient
        assert len(history) >= 1
        assert all(change.patient_id == patient.patient_id for change in history)
