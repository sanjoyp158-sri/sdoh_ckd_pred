"""
Unit tests for Risk Stratification Module.
"""

import pytest
from datetime import datetime

from app.services.risk_stratification import RiskStratificationModule, RiskTierChange
from app.models.patient import (
    UnifiedPatientRecord,
    Demographics,
    ClinicalRecord,
    AdministrativeRecord,
    SDOHRecord,
    Address,
    RiskTier
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
            egfr=35.0,
            egfr_history=[(datetime.now(), 40.0), (datetime.now(), 35.0)],
            uacr=250.0,
            hba1c=7.5,
            systolic_bp=145,
            diastolic_bp=85,
            bmi=32.0,
            medications=[],
            ckd_stage="3b",
            diagnosis_date=datetime.now(),
            comorbidities=["diabetes", "hypertension"]
        ),
        administrative=AdministrativeRecord(
            visit_frequency_12mo=4,
            specialist_referrals=[],
            insurance_type="Medicare",
            insurance_status="Active",
            last_visit_date=datetime.now()
        ),
        sdoh=SDOHRecord(
            adi_percentile=85,
            food_desert=True,
            housing_stability_score=0.4,
            transportation_access_score=0.6,
            rural_urban_code="rural"
        ),
        created_at=datetime.now(),
        updated_at=datetime.now()
    )


class TestRiskStratificationModule:
    """Test Risk Stratification Module."""
    
    def test_initialization(self):
        """Test module initialization."""
        module = RiskStratificationModule()
        
        assert module.high_risk_threshold == 0.65
        assert module.moderate_risk_threshold == 0.35
        assert len(module.tier_change_log) == 0
    
    def test_stratify_high_risk(self, sample_patient):
        """Test stratification for high-risk patient."""
        module = RiskStratificationModule()
        
        risk_score = 0.75
        tier = module.stratify_patient(sample_patient, risk_score)
        
        assert tier == RiskTier.HIGH
    
    def test_stratify_moderate_risk_upper(self, sample_patient):
        """Test stratification for moderate-risk patient (upper bound)."""
        module = RiskStratificationModule()
        
        risk_score = 0.65
        tier = module.stratify_patient(sample_patient, risk_score)
        
        assert tier == RiskTier.MODERATE
    
    def test_stratify_moderate_risk_lower(self, sample_patient):
        """Test stratification for moderate-risk patient (lower bound)."""
        module = RiskStratificationModule()
        
        risk_score = 0.35
        tier = module.stratify_patient(sample_patient, risk_score)
        
        assert tier == RiskTier.MODERATE
    
    def test_stratify_low_risk(self, sample_patient):
        """Test stratification for low-risk patient."""
        module = RiskStratificationModule()
        
        risk_score = 0.25
        tier = module.stratify_patient(sample_patient, risk_score)
        
        assert tier == RiskTier.LOW
    
    def test_stratify_boundary_high_moderate(self, sample_patient):
        """Test boundary between high and moderate risk."""
        module = RiskStratificationModule()
        
        # Just above threshold
        tier_high = module.stratify_patient(sample_patient, 0.66)
        assert tier_high == RiskTier.HIGH
        
        # At threshold
        tier_moderate = module.stratify_patient(sample_patient, 0.65)
        assert tier_moderate == RiskTier.MODERATE
    
    def test_stratify_boundary_moderate_low(self, sample_patient):
        """Test boundary between moderate and low risk."""
        module = RiskStratificationModule()
        
        # At threshold
        tier_moderate = module.stratify_patient(sample_patient, 0.35)
        assert tier_moderate == RiskTier.MODERATE
        
        # Just below threshold
        tier_low = module.stratify_patient(sample_patient, 0.34)
        assert tier_low == RiskTier.LOW
    
    def test_stratify_invalid_score_too_high(self, sample_patient):
        """Test stratification with invalid score (too high)."""
        module = RiskStratificationModule()
        
        with pytest.raises(ValueError, match="Risk score must be between 0 and 1"):
            module.stratify_patient(sample_patient, 1.5)
    
    def test_stratify_invalid_score_negative(self, sample_patient):
        """Test stratification with invalid score (negative)."""
        module = RiskStratificationModule()
        
        with pytest.raises(ValueError, match="Risk score must be between 0 and 1"):
            module.stratify_patient(sample_patient, -0.1)


class TestTierChangeLogging:
    """Test tier change logging functionality."""
    
    def test_initial_assignment_logged(self, sample_patient):
        """Test that initial tier assignment is logged."""
        module = RiskStratificationModule()
        
        risk_score = 0.75
        tier = module.stratify_patient(sample_patient, risk_score)
        
        # Check log
        assert len(module.tier_change_log) == 1
        
        change = module.tier_change_log[0]
        assert change.patient_id == "test_001"
        assert change.previous_tier is None
        assert change.new_tier == RiskTier.HIGH
        assert change.previous_score is None
        assert change.new_score == 0.75
        assert isinstance(change.timestamp, datetime)
    
    def test_tier_change_logged(self, sample_patient):
        """Test that tier changes are logged."""
        module = RiskStratificationModule()
        
        # Initial assignment
        tier1 = module.stratify_patient(sample_patient, 0.75)
        
        # Tier change
        tier2 = module.stratify_patient(
            sample_patient,
            0.50,
            previous_tier=tier1,
            previous_score=0.75
        )
        
        # Check log
        assert len(module.tier_change_log) == 2
        
        # Check second change
        change = module.tier_change_log[1]
        assert change.patient_id == "test_001"
        assert change.previous_tier == RiskTier.HIGH
        assert change.new_tier == RiskTier.MODERATE
        assert change.previous_score == 0.75
        assert change.new_score == 0.50
    
    def test_no_change_not_logged(self, sample_patient):
        """Test that same tier is not logged as a change."""
        module = RiskStratificationModule()
        
        # Initial assignment
        tier1 = module.stratify_patient(sample_patient, 0.75)
        
        # Same tier (no change)
        tier2 = module.stratify_patient(
            sample_patient,
            0.70,
            previous_tier=tier1,
            previous_score=0.75
        )
        
        # Only initial assignment should be logged
        assert len(module.tier_change_log) == 1
    
    def test_get_tier_change_history(self, sample_patient):
        """Test retrieving tier change history for a patient."""
        module = RiskStratificationModule()
        
        # Create changes for multiple patients
        patient2 = UnifiedPatientRecord(
            patient_id="test_002",
            demographics=sample_patient.demographics,
            clinical=sample_patient.clinical,
            administrative=sample_patient.administrative,
            sdoh=sample_patient.sdoh,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        module.stratify_patient(sample_patient, 0.75)
        module.stratify_patient(patient2, 0.40)
        module.stratify_patient(sample_patient, 0.50, previous_tier=RiskTier.HIGH, previous_score=0.75)
        
        # Get history for test_001
        history = module.get_tier_change_history("test_001")
        
        assert len(history) == 2
        assert all(change.patient_id == "test_001" for change in history)
    
    def test_get_all_tier_changes(self, sample_patient):
        """Test retrieving all tier changes."""
        module = RiskStratificationModule()
        
        patient2 = UnifiedPatientRecord(
            patient_id="test_002",
            demographics=sample_patient.demographics,
            clinical=sample_patient.clinical,
            administrative=sample_patient.administrative,
            sdoh=sample_patient.sdoh,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        module.stratify_patient(sample_patient, 0.75)
        module.stratify_patient(patient2, 0.40)
        
        all_changes = module.get_all_tier_changes()
        
        assert len(all_changes) == 2
    
    def test_tier_change_timestamps(self, sample_patient):
        """Test that tier changes have timestamps."""
        module = RiskStratificationModule()
        
        before = datetime.now()
        module.stratify_patient(sample_patient, 0.75)
        after = datetime.now()
        
        change = module.tier_change_log[0]
        assert before <= change.timestamp <= after


class TestRiskTierChange:
    """Test RiskTierChange data class."""
    
    def test_risk_tier_change_creation(self):
        """Test creating a RiskTierChange object."""
        timestamp = datetime.now()
        
        change = RiskTierChange(
            patient_id="test_001",
            previous_tier=RiskTier.MODERATE,
            new_tier=RiskTier.HIGH,
            previous_score=0.50,
            new_score=0.75,
            timestamp=timestamp
        )
        
        assert change.patient_id == "test_001"
        assert change.previous_tier == RiskTier.MODERATE
        assert change.new_tier == RiskTier.HIGH
        assert change.previous_score == 0.50
        assert change.new_score == 0.75
        assert change.timestamp == timestamp
    
    def test_risk_tier_change_repr(self):
        """Test RiskTierChange string representation."""
        timestamp = datetime.now()
        
        change = RiskTierChange(
            patient_id="test_001",
            previous_tier=RiskTier.MODERATE,
            new_tier=RiskTier.HIGH,
            previous_score=0.50,
            new_score=0.75,
            timestamp=timestamp
        )
        
        repr_str = repr(change)
        assert "test_001" in repr_str
        assert "MODERATE" in repr_str
        assert "HIGH" in repr_str
