"""
Risk Stratification Module for CKD progression predictions.
Assigns patients to risk tiers and logs tier changes.
"""

from datetime import datetime
from typing import Optional, List
import logging

from app.models.patient import RiskTier, UnifiedPatientRecord
from app.core.config import settings


logger = logging.getLogger(__name__)


class RiskTierChange:
    """Represents a change in patient risk tier."""
    
    def __init__(
        self,
        patient_id: str,
        previous_tier: Optional[RiskTier],
        new_tier: RiskTier,
        previous_score: Optional[float],
        new_score: float,
        timestamp: datetime
    ):
        self.patient_id = patient_id
        self.previous_tier = previous_tier
        self.new_tier = new_tier
        self.previous_score = previous_score
        self.new_score = new_score
        self.timestamp = timestamp
    
    def __repr__(self):
        return (
            f"RiskTierChange(patient_id={self.patient_id}, "
            f"{self.previous_tier} -> {self.new_tier}, "
            f"score: {self.previous_score} -> {self.new_score}, "
            f"timestamp={self.timestamp})"
        )


class RiskStratificationModule:
    """
    Risk Stratification Module for CKD progression predictions.
    
    Assigns patients to risk tiers based on prediction scores:
    - HIGH: score > 0.65
    - MODERATE: 0.35 <= score <= 0.65
    - LOW: score < 0.35
    
    Logs all tier changes with timestamps for audit trail.
    """
    
    def __init__(self):
        """Initialize Risk Stratification Module."""
        self.tier_change_log: List[RiskTierChange] = []
        
        # Risk thresholds from paper (Youden's J statistic optimization)
        self.high_risk_threshold = settings.RISK_THRESHOLD_HIGH  # 0.65
        self.moderate_risk_threshold = settings.RISK_THRESHOLD_MODERATE  # 0.35
    
    def stratify_patient(
        self,
        patient: UnifiedPatientRecord,
        risk_score: float,
        previous_tier: Optional[RiskTier] = None,
        previous_score: Optional[float] = None
    ) -> RiskTier:
        """
        Assign patient to risk tier based on prediction score.
        
        Args:
            patient: Patient record
            risk_score: Predicted risk score (0-1)
            previous_tier: Previous risk tier (if any)
            previous_score: Previous risk score (if any)
        
        Returns:
            RiskTier enum value (HIGH, MODERATE, or LOW)
        """
        # Validate risk score
        if not 0.0 <= risk_score <= 1.0:
            raise ValueError(f"Risk score must be between 0 and 1, got {risk_score}")
        
        # Determine new tier based on thresholds
        if risk_score > self.high_risk_threshold:
            new_tier = RiskTier.HIGH
        elif risk_score >= self.moderate_risk_threshold:
            new_tier = RiskTier.MODERATE
        else:
            new_tier = RiskTier.LOW
        
        # Log tier change if tier has changed
        if previous_tier is not None and previous_tier != new_tier:
            self._log_tier_change(
                patient_id=patient.patient_id,
                previous_tier=previous_tier,
                new_tier=new_tier,
                previous_score=previous_score,
                new_score=risk_score
            )
        elif previous_tier is None:
            # First time assignment - log as initial tier
            self._log_tier_change(
                patient_id=patient.patient_id,
                previous_tier=None,
                new_tier=new_tier,
                previous_score=None,
                new_score=risk_score
            )
        
        return new_tier
    
    def _log_tier_change(
        self,
        patient_id: str,
        previous_tier: Optional[RiskTier],
        new_tier: RiskTier,
        previous_score: Optional[float],
        new_score: float
    ):
        """
        Log a tier change with timestamp.
        
        Args:
            patient_id: Patient identifier
            previous_tier: Previous risk tier (None for initial assignment)
            new_tier: New risk tier
            previous_score: Previous risk score (None for initial assignment)
            new_score: New risk score
        """
        timestamp = datetime.now()
        
        tier_change = RiskTierChange(
            patient_id=patient_id,
            previous_tier=previous_tier,
            new_tier=new_tier,
            previous_score=previous_score,
            new_score=new_score,
            timestamp=timestamp
        )
        
        self.tier_change_log.append(tier_change)
        
        # Log to application logger
        if previous_tier is None:
            logger.info(
                f"Initial risk tier assignment for patient {patient_id}: "
                f"{new_tier.value} (score: {new_score:.3f}) at {timestamp}"
            )
        else:
            logger.info(
                f"Risk tier change for patient {patient_id}: "
                f"{previous_tier.value} -> {new_tier.value} "
                f"(score: {previous_score:.3f} -> {new_score:.3f}) at {timestamp}"
            )
    
    def get_tier_change_history(self, patient_id: str) -> List[RiskTierChange]:
        """
        Get tier change history for a specific patient.
        
        Args:
            patient_id: Patient identifier
        
        Returns:
            List of RiskTierChange objects for the patient
        """
        return [
            change for change in self.tier_change_log
            if change.patient_id == patient_id
        ]
    
    def get_all_tier_changes(self) -> List[RiskTierChange]:
        """
        Get all tier changes across all patients.
        
        Returns:
            List of all RiskTierChange objects
        """
        return self.tier_change_log.copy()
    
    def clear_log(self):
        """Clear the tier change log (for testing purposes)."""
        self.tier_change_log.clear()
