"""
Case Manager Enrollment for automated patient assignment.
Minimal placeholder implementation for high-risk CKD patients.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
import logging

from app.models.patient import UnifiedPatientRecord


logger = logging.getLogger(__name__)


class CaseManager:
    """Represents a case manager."""
    
    def __init__(
        self,
        manager_id: str,
        name: str,
        max_caseload: int = 50
    ):
        self.manager_id = manager_id
        self.name = name
        self.max_caseload = max_caseload
        self.current_caseload = 0
    
    def has_capacity(self) -> bool:
        """Check if case manager has capacity for new patients."""
        return self.current_caseload < self.max_caseload
    
    def add_patient(self):
        """Add a patient to caseload."""
        if self.has_capacity():
            self.current_caseload += 1
            return True
        return False
    
    def __repr__(self):
        return (
            f"CaseManager(id={self.manager_id}, name={self.name}, "
            f"caseload={self.current_caseload}/{self.max_caseload})"
        )


class CaseRecord:
    """Represents a case record for a patient."""
    
    def __init__(
        self,
        case_id: str,
        patient_id: str,
        manager_id: str,
        demographics: Dict[str, Any],
        risk_factors: Dict[str, Any],
        sdoh_barriers: Dict[str, Any],
        shap_factors: Optional[List[Dict[str, Any]]] = None,
        created_at: Optional[datetime] = None
    ):
        self.case_id = case_id
        self.patient_id = patient_id
        self.manager_id = manager_id
        self.demographics = demographics
        self.risk_factors = risk_factors
        self.sdoh_barriers = sdoh_barriers
        self.shap_factors = shap_factors or []
        self.created_at = created_at or datetime.now()
        self.notification_sent = False
        self.notification_sent_at: Optional[datetime] = None
    
    def __repr__(self):
        return (
            f"CaseRecord(id={self.case_id}, patient={self.patient_id}, "
            f"manager={self.manager_id})"
        )


class CaseManagerEnrollment:
    """
    Case Manager Enrollment for automated patient assignment.
    
    Minimal placeholder implementation that simulates:
    - Capacity-based assignment (max 50 patients per manager)
    - Case record creation with demographics, risk factors, and SDOH barriers
    - Case manager notification within 24 hours
    - SHAP explanation factors in case record
    
    In production, this would integrate with:
    - Case management system
    - Staff scheduling system
    - Notification service
    """
    
    def __init__(self):
        """Initialize Case Manager Enrollment."""
        self.case_managers: List[CaseManager] = []
        self.case_records: List[CaseRecord] = []
        self.max_caseload_per_manager = 50
        self.notification_window_hours = 24
        
        # Initialize with some case managers (placeholder)
        self._initialize_case_managers()
    
    def _initialize_case_managers(self):
        """Initialize case managers (placeholder)."""
        # In production, would load from database
        self.case_managers = [
            CaseManager("cm_001", "Sarah Johnson", self.max_caseload_per_manager),
            CaseManager("cm_002", "Michael Chen", self.max_caseload_per_manager),
            CaseManager("cm_003", "Emily Rodriguez", self.max_caseload_per_manager)
        ]
    
    def assign_case_manager(
        self,
        patient: UnifiedPatientRecord
    ) -> Optional[CaseManager]:
        """
        Assign patient to case manager based on capacity.
        
        Args:
            patient: Patient record
        
        Returns:
            Assigned case manager, or None if no capacity
        """
        logger.info(f"Assigning case manager for patient {patient.patient_id}")
        
        # Find case manager with available capacity
        for manager in self.case_managers:
            if manager.has_capacity():
                logger.info(
                    f"Assigned patient {patient.patient_id} to case manager "
                    f"{manager.name} (caseload: {manager.current_caseload}/{manager.max_caseload})"
                )
                return manager
        
        logger.warning(f"No case manager capacity available for patient {patient.patient_id}")
        return None
    
    def create_case_record(
        self,
        patient: UnifiedPatientRecord,
        manager: CaseManager,
        risk_score: float,
        shap_factors: Optional[List[Dict[str, Any]]] = None
    ) -> CaseRecord:
        """
        Create case record with patient information.
        
        Args:
            patient: Patient record
            manager: Assigned case manager
            risk_score: Patient risk score
            shap_factors: SHAP explanation factors
        
        Returns:
            Created case record
        """
        # Generate case ID
        case_id = f"case_{patient.patient_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Extract demographics
        demographics = {
            "age": patient.demographics.age,
            "sex": patient.demographics.sex,
            "zip_code": patient.demographics.address.zip_code,
            "state": patient.demographics.address.state
        }
        
        # Extract risk factors
        risk_factors = {
            "risk_score": risk_score,
            "egfr": patient.clinical.egfr,
            "uacr": patient.clinical.uacr,
            "hba1c": patient.clinical.hba1c,
            "ckd_stage": patient.clinical.ckd_stage,
            "comorbidities": patient.clinical.comorbidities
        }
        
        # Extract SDOH barriers
        sdoh_barriers = {
            "adi_percentile": patient.sdoh.adi_percentile,
            "food_desert": patient.sdoh.food_desert,
            "housing_stability_score": patient.sdoh.housing_stability_score,
            "transportation_access_score": patient.sdoh.transportation_access_score,
            "rural_urban_code": patient.sdoh.rural_urban_code
        }
        
        # Create case record
        case_record = CaseRecord(
            case_id=case_id,
            patient_id=patient.patient_id,
            manager_id=manager.manager_id,
            demographics=demographics,
            risk_factors=risk_factors,
            sdoh_barriers=sdoh_barriers,
            shap_factors=shap_factors
        )
        
        self.case_records.append(case_record)
        
        logger.info(f"Created case record {case_id} for patient {patient.patient_id}")
        
        return case_record
    
    def notify_case_manager(
        self,
        case_record: CaseRecord,
        manager: CaseManager
    ) -> bool:
        """
        Notify case manager of new patient enrollment.
        
        Args:
            case_record: Case record
            manager: Case manager to notify
        
        Returns:
            True if notification sent successfully
        """
        logger.info(
            f"Notifying case manager {manager.name} of new patient enrollment "
            f"(case: {case_record.case_id})"
        )
        
        # Placeholder: Simulate sending notification
        # In production, would call notification service
        notification_message = self._generate_notification_message(case_record, manager)
        
        # Mark notification as sent
        case_record.notification_sent = True
        case_record.notification_sent_at = datetime.now()
        
        logger.info(f"Notification sent to case manager {manager.name}")
        
        return True
    
    def enroll_patient(
        self,
        patient: UnifiedPatientRecord,
        risk_score: float,
        shap_factors: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[CaseRecord]:
        """
        Complete enrollment workflow for a patient.
        
        Assigns case manager, creates case record, and sends notification.
        
        Args:
            patient: Patient record
            risk_score: Patient risk score
            shap_factors: SHAP explanation factors
        
        Returns:
            Case record if successful, None otherwise
        """
        # Assign case manager
        manager = self.assign_case_manager(patient)
        
        if manager is None:
            logger.error(f"Cannot enroll patient {patient.patient_id} - no case manager capacity")
            return None
        
        # Add patient to manager's caseload
        manager.add_patient()
        
        # Create case record
        case_record = self.create_case_record(patient, manager, risk_score, shap_factors)
        
        # Notify case manager
        self.notify_case_manager(case_record, manager)
        
        return case_record
    
    def _generate_notification_message(
        self,
        case_record: CaseRecord,
        manager: CaseManager
    ) -> str:
        """Generate case manager notification message."""
        return f"""
New High-Risk Patient Enrollment

Case Manager: {manager.name}
Case ID: {case_record.case_id}
Patient ID: {case_record.patient_id}

Demographics:
- Age: {case_record.demographics['age']}
- Sex: {case_record.demographics['sex']}
- Location: {case_record.demographics['zip_code']}, {case_record.demographics['state']}

Risk Factors:
- Risk Score: {case_record.risk_factors['risk_score']:.3f}
- eGFR: {case_record.risk_factors['egfr']:.1f} mL/min/1.73m²
- UACR: {case_record.risk_factors['uacr']:.1f} mg/g
- CKD Stage: {case_record.risk_factors['ckd_stage']}

SDOH Barriers:
- ADI Percentile: {case_record.sdoh_barriers['adi_percentile']}
- Food Desert: {case_record.sdoh_barriers['food_desert']}
- Housing Stability: {case_record.sdoh_barriers['housing_stability_score']:.2f}
- Transportation Access: {case_record.sdoh_barriers['transportation_access_score']:.2f}

{self._format_shap_factors(case_record.shap_factors)}

Please review the case record and initiate contact with the patient within 24 hours.
"""
    
    def _format_shap_factors(self, shap_factors: List[Dict[str, Any]]) -> str:
        """Format SHAP factors for notification."""
        if not shap_factors:
            return "SHAP Explanation Factors: Not available"
        
        lines = ["SHAP Explanation Factors:"]
        for i, factor in enumerate(shap_factors[:5], 1):
            lines.append(f"  {i}. {factor.get('feature', 'Unknown')}: {factor.get('value', 'N/A')}")
        
        return "\n".join(lines)
    
    def get_case_record(self, case_id: str) -> Optional[CaseRecord]:
        """Get case record by ID."""
        for record in self.case_records:
            if record.case_id == case_id:
                return record
        return None
    
    def get_patient_case_records(self, patient_id: str) -> List[CaseRecord]:
        """Get all case records for a patient."""
        return [r for r in self.case_records if r.patient_id == patient_id]
    
    def get_manager_case_records(self, manager_id: str) -> List[CaseRecord]:
        """Get all case records for a case manager."""
        return [r for r in self.case_records if r.manager_id == manager_id]
    
    def get_case_manager(self, manager_id: str) -> Optional[CaseManager]:
        """Get case manager by ID."""
        for manager in self.case_managers:
            if manager.manager_id == manager_id:
                return manager
        return None
