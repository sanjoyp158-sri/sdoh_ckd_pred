"""
Data Access Objects (DAOs) for database CRUD operations.

Provides high-level interface for interacting with patient records,
predictions, and other entities with automatic encryption/decryption.
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from typing import List, Optional, Dict, Any
from datetime import datetime
import json

from app.db.models import (
    PatientModel, PredictionModel, RiskTierChangeLogModel,
    AuditLogModel, InterventionWorkflowModel, CaseManagerModel, CaseRecordModel
)
from app.db.encryption import get_encryption_service
from app.models.patient import (
    UnifiedPatientRecord, Demographics, Address, ClinicalRecord,
    AdministrativeRecord, SDOHRecord, Medication, Referral,
    PredictionResult, RiskTier, SHAPExplanation, Factor, CategorizedFactors
)


class PatientDAO:
    """
    Data Access Object for patient records.
    
    Handles CRUD operations with automatic encryption/decryption of sensitive fields.
    """
    
    def __init__(self, db: Session):
        """
        Initialize PatientDAO.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.encryption = get_encryption_service()
    
    def create(self, patient: UnifiedPatientRecord) -> PatientModel:
        """
        Create a new patient record in the database.
        
        Args:
            patient: UnifiedPatientRecord to store
            
        Returns:
            Created PatientModel
        """
        # Encrypt sensitive address fields
        encrypted_street = self.encryption.encrypt(patient.demographics.address.street or "")
        encrypted_city = self.encryption.encrypt(patient.demographics.address.city or "")
        
        # Serialize complex fields to JSON
        egfr_history_json = [
            [ts.isoformat(), value] for ts, value in patient.clinical.egfr_history
        ]
        
        medications_json = [
            {
                'name': med.name,
                'category': med.category,
                'start_date': med.start_date.isoformat() if med.start_date else None,
                'active': med.active
            }
            for med in patient.clinical.medications
        ]
        
        referrals_json = [
            {
                'specialty': ref.specialty,
                'date': ref.date.isoformat(),
                'completed': ref.completed,
                'reason': ref.reason
            }
            for ref in patient.administrative.specialist_referrals
        ]
        
        # Create database model
        db_patient = PatientModel(
            patient_id=patient.patient_id,
            age=patient.demographics.age,
            sex=patient.demographics.sex,
            race=patient.demographics.race,
            ethnicity=patient.demographics.ethnicity,
            address_street=encrypted_street,
            address_city=encrypted_city,
            address_state=patient.demographics.address.state,
            address_zip_code=patient.demographics.address.zip_code,
            address_zcta=patient.demographics.address.zcta,
            egfr=patient.clinical.egfr,
            egfr_history=egfr_history_json,
            uacr=patient.clinical.uacr,
            hba1c=patient.clinical.hba1c,
            systolic_bp=patient.clinical.systolic_bp,
            diastolic_bp=patient.clinical.diastolic_bp,
            bmi=patient.clinical.bmi,
            medications=medications_json,
            ckd_stage=patient.clinical.ckd_stage,
            diagnosis_date=patient.clinical.diagnosis_date,
            comorbidities=patient.clinical.comorbidities,
            visit_frequency_12mo=patient.administrative.visit_frequency_12mo,
            specialist_referrals=referrals_json,
            insurance_type=patient.administrative.insurance_type,
            insurance_status=patient.administrative.insurance_status,
            last_visit_date=patient.administrative.last_visit_date,
            adi_percentile=patient.sdoh.adi_percentile,
            food_desert=patient.sdoh.food_desert,
            housing_stability_score=patient.sdoh.housing_stability_score,
            transportation_access_score=patient.sdoh.transportation_access_score,
            rural_urban_code=patient.sdoh.rural_urban_code,
            created_at=patient.created_at,
            updated_at=patient.updated_at
        )
        
        self.db.add(db_patient)
        self.db.commit()
        self.db.refresh(db_patient)
        
        return db_patient
    
    def get_by_id(self, patient_id: str) -> Optional[UnifiedPatientRecord]:
        """
        Retrieve patient record by ID.
        
        Args:
            patient_id: Patient identifier
            
        Returns:
            UnifiedPatientRecord if found, None otherwise
        """
        db_patient = self.db.query(PatientModel).filter(
            PatientModel.patient_id == patient_id
        ).first()
        
        if not db_patient:
            return None
        
        return self._to_domain_model(db_patient)
    
    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        ckd_stage: Optional[str] = None
    ) -> List[UnifiedPatientRecord]:
        """
        Retrieve all patient records with optional filtering.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            ckd_stage: Filter by CKD stage (optional)
            
        Returns:
            List of UnifiedPatientRecord objects
        """
        query = self.db.query(PatientModel)
        
        if ckd_stage:
            query = query.filter(PatientModel.ckd_stage == ckd_stage)
        
        db_patients = query.offset(skip).limit(limit).all()
        
        return [self._to_domain_model(p) for p in db_patients]
    
    def update(self, patient: UnifiedPatientRecord) -> Optional[PatientModel]:
        """
        Update existing patient record.
        
        Args:
            patient: Updated UnifiedPatientRecord
            
        Returns:
            Updated PatientModel if found, None otherwise
        """
        db_patient = self.db.query(PatientModel).filter(
            PatientModel.patient_id == patient.patient_id
        ).first()
        
        if not db_patient:
            return None
        
        # Update fields (similar to create, but updating existing record)
        encrypted_street = self.encryption.encrypt(patient.demographics.address.street or "")
        encrypted_city = self.encryption.encrypt(patient.demographics.address.city or "")
        
        egfr_history_json = [
            [ts.isoformat(), value] for ts, value in patient.clinical.egfr_history
        ]
        
        medications_json = [
            {
                'name': med.name,
                'category': med.category,
                'start_date': med.start_date.isoformat() if med.start_date else None,
                'active': med.active
            }
            for med in patient.clinical.medications
        ]
        
        referrals_json = [
            {
                'specialty': ref.specialty,
                'date': ref.date.isoformat(),
                'completed': ref.completed,
                'reason': ref.reason
            }
            for ref in patient.administrative.specialist_referrals
        ]
        
        # Update all fields
        db_patient.age = patient.demographics.age
        db_patient.sex = patient.demographics.sex
        db_patient.race = patient.demographics.race
        db_patient.ethnicity = patient.demographics.ethnicity
        db_patient.address_street = encrypted_street
        db_patient.address_city = encrypted_city
        db_patient.address_state = patient.demographics.address.state
        db_patient.address_zip_code = patient.demographics.address.zip_code
        db_patient.address_zcta = patient.demographics.address.zcta
        db_patient.egfr = patient.clinical.egfr
        db_patient.egfr_history = egfr_history_json
        db_patient.uacr = patient.clinical.uacr
        db_patient.hba1c = patient.clinical.hba1c
        db_patient.systolic_bp = patient.clinical.systolic_bp
        db_patient.diastolic_bp = patient.clinical.diastolic_bp
        db_patient.bmi = patient.clinical.bmi
        db_patient.medications = medications_json
        db_patient.ckd_stage = patient.clinical.ckd_stage
        db_patient.diagnosis_date = patient.clinical.diagnosis_date
        db_patient.comorbidities = patient.clinical.comorbidities
        db_patient.visit_frequency_12mo = patient.administrative.visit_frequency_12mo
        db_patient.specialist_referrals = referrals_json
        db_patient.insurance_type = patient.administrative.insurance_type
        db_patient.insurance_status = patient.administrative.insurance_status
        db_patient.last_visit_date = patient.administrative.last_visit_date
        db_patient.adi_percentile = patient.sdoh.adi_percentile
        db_patient.food_desert = patient.sdoh.food_desert
        db_patient.housing_stability_score = patient.sdoh.housing_stability_score
        db_patient.transportation_access_score = patient.sdoh.transportation_access_score
        db_patient.rural_urban_code = patient.sdoh.rural_urban_code
        db_patient.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(db_patient)
        
        return db_patient
    
    def delete(self, patient_id: str) -> bool:
        """
        Delete patient record.
        
        Args:
            patient_id: Patient identifier
            
        Returns:
            True if deleted, False if not found
        """
        db_patient = self.db.query(PatientModel).filter(
            PatientModel.patient_id == patient_id
        ).first()
        
        if not db_patient:
            return False
        
        self.db.delete(db_patient)
        self.db.commit()
        
        return True
    
    def _to_domain_model(self, db_patient: PatientModel) -> UnifiedPatientRecord:
        """
        Convert database model to domain model with decryption.
        
        Args:
            db_patient: PatientModel from database
            
        Returns:
            UnifiedPatientRecord domain model
        """
        # Decrypt sensitive fields
        decrypted_street = self.encryption.decrypt(db_patient.address_street or "")
        decrypted_city = self.encryption.decrypt(db_patient.address_city or "")
        
        # Parse address
        address = Address(
            street=decrypted_street if decrypted_street else None,
            city=decrypted_city if decrypted_city else None,
            state=db_patient.address_state,
            zip_code=db_patient.address_zip_code,
            zcta=db_patient.address_zcta
        )
        
        # Parse demographics
        demographics = Demographics(
            age=db_patient.age,
            sex=db_patient.sex,
            race=db_patient.race,
            ethnicity=db_patient.ethnicity,
            address=address
        )
        
        # Parse eGFR history
        egfr_history = [
            (datetime.fromisoformat(ts), value)
            for ts, value in db_patient.egfr_history
        ]
        
        # Parse medications
        medications = [
            Medication(
                name=med['name'],
                category=med['category'],
                start_date=datetime.fromisoformat(med['start_date']) if med.get('start_date') else None,
                active=med['active']
            )
            for med in db_patient.medications
        ]
        
        # Parse clinical record
        clinical = ClinicalRecord(
            egfr=db_patient.egfr,
            egfr_history=egfr_history,
            uacr=db_patient.uacr,
            hba1c=db_patient.hba1c,
            systolic_bp=db_patient.systolic_bp,
            diastolic_bp=db_patient.diastolic_bp,
            bmi=db_patient.bmi,
            medications=medications,
            ckd_stage=db_patient.ckd_stage,
            diagnosis_date=db_patient.diagnosis_date,
            comorbidities=db_patient.comorbidities
        )
        
        # Parse referrals
        referrals = [
            Referral(
                specialty=ref['specialty'],
                date=datetime.fromisoformat(ref['date']),
                completed=ref['completed'],
                reason=ref.get('reason')
            )
            for ref in db_patient.specialist_referrals
        ]
        
        # Parse administrative record
        administrative = AdministrativeRecord(
            visit_frequency_12mo=db_patient.visit_frequency_12mo,
            specialist_referrals=referrals,
            insurance_type=db_patient.insurance_type,
            insurance_status=db_patient.insurance_status,
            last_visit_date=db_patient.last_visit_date
        )
        
        # Parse SDOH record
        sdoh = SDOHRecord(
            adi_percentile=db_patient.adi_percentile,
            food_desert=db_patient.food_desert,
            housing_stability_score=db_patient.housing_stability_score,
            transportation_access_score=db_patient.transportation_access_score,
            rural_urban_code=db_patient.rural_urban_code
        )
        
        # Create unified record
        return UnifiedPatientRecord(
            patient_id=db_patient.patient_id,
            demographics=demographics,
            clinical=clinical,
            administrative=administrative,
            sdoh=sdoh,
            created_at=db_patient.created_at,
            updated_at=db_patient.updated_at
        )


class PredictionDAO:
    """Data Access Object for prediction records."""
    
    def __init__(self, db: Session):
        """Initialize PredictionDAO."""
        self.db = db
    
    def create(
        self,
        prediction: PredictionResult,
        shap_explanation: Optional[SHAPExplanation] = None
    ) -> PredictionModel:
        """
        Create a new prediction record.
        
        Args:
            prediction: PredictionResult to store
            shap_explanation: Optional SHAP explanation
            
        Returns:
            Created PredictionModel
        """
        # Prepare SHAP data if available
        shap_values_json = None
        top_factors_json = None
        categorized_factors_json = None
        baseline_risk = None
        explanation_time_ms = None
        
        if shap_explanation:
            shap_values_json = shap_explanation.shap_values
            baseline_risk = shap_explanation.baseline_risk
            explanation_time_ms = shap_explanation.computation_time_ms
            
            top_factors_json = [
                {
                    'feature_name': f.feature_name,
                    'feature_value': f.feature_value,
                    'shap_value': f.shap_value,
                    'category': f.category,
                    'direction': f.direction
                }
                for f in shap_explanation.top_factors
            ]
            
            categorized_factors_json = {
                'clinical': [
                    {
                        'feature_name': f.feature_name,
                        'feature_value': f.feature_value,
                        'shap_value': f.shap_value,
                        'category': f.category,
                        'direction': f.direction
                    }
                    for f in shap_explanation.categorized_factors.clinical
                ],
                'administrative': [
                    {
                        'feature_name': f.feature_name,
                        'feature_value': f.feature_value,
                        'shap_value': f.shap_value,
                        'category': f.category,
                        'direction': f.direction
                    }
                    for f in shap_explanation.categorized_factors.administrative
                ],
                'sdoh': [
                    {
                        'feature_name': f.feature_name,
                        'feature_value': f.feature_value,
                        'shap_value': f.shap_value,
                        'category': f.category,
                        'direction': f.direction
                    }
                    for f in shap_explanation.categorized_factors.sdoh
                ]
            }
        
        # Create database model
        db_prediction = PredictionModel(
            patient_id=prediction.patient_id,
            risk_score=prediction.risk_score,
            risk_tier=prediction.risk_tier.value,
            prediction_date=prediction.prediction_date,
            model_version=prediction.model_version,
            processing_time_ms=prediction.processing_time_ms,
            baseline_risk=baseline_risk,
            shap_values=shap_values_json,
            top_factors=top_factors_json,
            categorized_factors=categorized_factors_json,
            explanation_time_ms=explanation_time_ms
        )
        
        self.db.add(db_prediction)
        self.db.commit()
        self.db.refresh(db_prediction)
        
        return db_prediction
    
    def get_by_patient(
        self,
        patient_id: str,
        limit: int = 10
    ) -> List[PredictionModel]:
        """
        Get predictions for a patient.
        
        Args:
            patient_id: Patient identifier
            limit: Maximum number of predictions to return
            
        Returns:
            List of PredictionModel objects
        """
        return self.db.query(PredictionModel).filter(
            PredictionModel.patient_id == patient_id
        ).order_by(desc(PredictionModel.prediction_date)).limit(limit).all()
    
    def get_latest_by_patient(self, patient_id: str) -> Optional[PredictionModel]:
        """
        Get most recent prediction for a patient.
        
        Args:
            patient_id: Patient identifier
            
        Returns:
            Latest PredictionModel if found, None otherwise
        """
        return self.db.query(PredictionModel).filter(
            PredictionModel.patient_id == patient_id
        ).order_by(desc(PredictionModel.prediction_date)).first()
    
    def get_by_risk_tier(
        self,
        risk_tier: RiskTier,
        skip: int = 0,
        limit: int = 100
    ) -> List[PredictionModel]:
        """
        Get predictions by risk tier.
        
        Args:
            risk_tier: Risk tier to filter by
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of PredictionModel objects
        """
        return self.db.query(PredictionModel).filter(
            PredictionModel.risk_tier == risk_tier.value
        ).order_by(desc(PredictionModel.prediction_date)).offset(skip).limit(limit).all()


class AuditLogDAO:
    """Data Access Object for audit logs."""
    
    def __init__(self, db: Session):
        """Initialize AuditLogDAO."""
        self.db = db
    
    def create(
        self,
        user_id: str,
        action: str,
        resource: str,
        patient_id: Optional[str] = None,
        data_elements: Optional[List[str]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> AuditLogModel:
        """
        Create audit log entry.
        
        Args:
            user_id: User performing the action
            action: Action performed ('read', 'write', 'delete')
            resource: Resource accessed
            patient_id: Patient ID if applicable
            data_elements: List of data elements accessed
            ip_address: IP address of request
            user_agent: User agent string
            success: Whether action succeeded
            error_message: Error message if failed
            
        Returns:
            Created AuditLogModel
        """
        db_log = AuditLogModel(
            user_id=user_id,
            patient_id=patient_id,
            action=action,
            resource=resource,
            data_elements=data_elements or [],
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            error_message=error_message
        )
        
        self.db.add(db_log)
        self.db.commit()
        self.db.refresh(db_log)
        
        return db_log
    
    def get_by_patient(
        self,
        patient_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[AuditLogModel]:
        """
        Get audit logs for a patient.
        
        Args:
            patient_id: Patient identifier
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of AuditLogModel objects
        """
        return self.db.query(AuditLogModel).filter(
            AuditLogModel.patient_id == patient_id
        ).order_by(desc(AuditLogModel.timestamp)).offset(skip).limit(limit).all()
    
    def get_by_user(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[AuditLogModel]:
        """
        Get audit logs for a user.
        
        Args:
            user_id: User identifier
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of AuditLogModel objects
        """
        return self.db.query(AuditLogModel).filter(
            AuditLogModel.user_id == user_id
        ).order_by(desc(AuditLogModel.timestamp)).offset(skip).limit(limit).all()


class RiskTierChangeLogDAO:
    """Data Access Object for risk tier change logs."""
    
    def __init__(self, db: Session):
        """Initialize RiskTierChangeLogDAO."""
        self.db = db
    
    def create(
        self,
        patient_id: str,
        previous_tier: RiskTier,
        new_tier: RiskTier,
        risk_score: float
    ) -> RiskTierChangeLogModel:
        """
        Log a risk tier change.
        
        Args:
            patient_id: Patient identifier
            previous_tier: Previous risk tier
            new_tier: New risk tier
            risk_score: Current risk score
            
        Returns:
            Created RiskTierChangeLogModel
        """
        db_log = RiskTierChangeLogModel(
            patient_id=patient_id,
            previous_tier=previous_tier.value,
            new_tier=new_tier.value,
            risk_score=risk_score
        )
        
        self.db.add(db_log)
        self.db.commit()
        self.db.refresh(db_log)
        
        return db_log
    
    def get_by_patient(
        self,
        patient_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[RiskTierChangeLogModel]:
        """
        Get risk tier change history for a patient.
        
        Args:
            patient_id: Patient identifier
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of RiskTierChangeLogModel objects
        """
        return self.db.query(RiskTierChangeLogModel).filter(
            RiskTierChangeLogModel.patient_id == patient_id
        ).order_by(desc(RiskTierChangeLogModel.change_timestamp)).offset(skip).limit(limit).all()
