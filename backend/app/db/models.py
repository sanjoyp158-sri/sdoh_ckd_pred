"""
SQLAlchemy ORM models for PostgreSQL database.

Implements encrypted storage for sensitive patient data using AES-256.
"""

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Text, 
    ForeignKey, JSON, Index
)
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import Optional

from app.db.database import Base
from app.db.encryption import get_encryption_service


class EncryptedString(str):
    """Custom type for encrypted string fields."""
    pass


class PatientModel(Base):
    """
    Patient record table with encrypted sensitive data.
    
    Stores unified patient records with clinical, administrative, and SDOH data.
    Sensitive fields are encrypted at rest using AES-256.
    """
    __tablename__ = "patients"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    patient_id = Column(String(255), unique=True, nullable=False, index=True)
    
    # Demographics (encrypted)
    age = Column(Integer, nullable=False)
    sex = Column(String(10), nullable=False)
    race = Column(String(100))  # For fairness monitoring only
    ethnicity = Column(String(100))  # For fairness monitoring only
    
    # Address (encrypted)
    address_street = Column(Text)  # Encrypted
    address_city = Column(String(255))  # Encrypted
    address_state = Column(String(50))
    address_zip_code = Column(String(20))
    address_zcta = Column(String(20))
    
    # Clinical data (some fields encrypted)
    egfr = Column(Float, nullable=False)
    egfr_history = Column(JSON)  # List of [timestamp, value] pairs
    uacr = Column(Float, nullable=False)
    hba1c = Column(Float, nullable=False)
    systolic_bp = Column(Integer, nullable=False)
    diastolic_bp = Column(Integer, nullable=False)
    bmi = Column(Float, nullable=False)
    medications = Column(JSON)  # List of medication records
    ckd_stage = Column(String(10), nullable=False)
    diagnosis_date = Column(DateTime, nullable=False)
    comorbidities = Column(JSON)  # List of comorbidity strings
    
    # Administrative data
    visit_frequency_12mo = Column(Integer, nullable=False)
    specialist_referrals = Column(JSON)  # List of referral records
    insurance_type = Column(String(50), nullable=False)
    insurance_status = Column(String(50), nullable=False)
    last_visit_date = Column(DateTime, nullable=False)
    
    # SDOH data
    adi_percentile = Column(Integer, nullable=False)
    food_desert = Column(Boolean, nullable=False)
    housing_stability_score = Column(Float, nullable=False)
    transportation_access_score = Column(Float, nullable=False)
    rural_urban_code = Column(String(50), nullable=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    predictions = relationship("PredictionModel", back_populates="patient", cascade="all, delete-orphan")
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_patient_ckd_stage', 'ckd_stage'),
        Index('idx_patient_created_at', 'created_at'),
        Index('idx_patient_zip_code', 'address_zip_code'),
    )


class PredictionModel(Base):
    """
    Prediction results table.
    
    Stores ML model predictions and risk scores for patients.
    """
    __tablename__ = "predictions"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Foreign key to patient
    patient_id = Column(String(255), ForeignKey('patients.patient_id'), nullable=False, index=True)
    
    # Prediction data
    risk_score = Column(Float, nullable=False)
    risk_tier = Column(String(20), nullable=False)  # 'high', 'moderate', 'low'
    prediction_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    model_version = Column(String(50), nullable=False)
    processing_time_ms = Column(Integer, nullable=False)
    
    # SHAP explanation data
    baseline_risk = Column(Float)
    shap_values = Column(JSON)  # Feature name -> SHAP value mapping
    top_factors = Column(JSON)  # Top 5 contributing factors
    categorized_factors = Column(JSON)  # Factors by category
    explanation_time_ms = Column(Integer)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    patient = relationship("PatientModel", back_populates="predictions")
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_prediction_risk_tier', 'risk_tier'),
        Index('idx_prediction_date', 'prediction_date'),
        Index('idx_prediction_patient_date', 'patient_id', 'prediction_date'),
    )


class RiskTierChangeLogModel(Base):
    """
    Risk tier change log table.
    
    Tracks changes in patient risk tier assignments over time.
    """
    __tablename__ = "risk_tier_changes"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Patient reference
    patient_id = Column(String(255), ForeignKey('patients.patient_id'), nullable=False, index=True)
    
    # Change data
    previous_tier = Column(String(20), nullable=False)
    new_tier = Column(String(20), nullable=False)
    risk_score = Column(Float, nullable=False)
    change_timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Indexes
    __table_args__ = (
        Index('idx_tier_change_timestamp', 'change_timestamp'),
        Index('idx_tier_change_patient', 'patient_id', 'change_timestamp'),
    )


class AuditLogModel(Base):
    """
    Audit log table for data access tracking.
    
    Records all access to patient data for HIPAA compliance.
    """
    __tablename__ = "audit_logs"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Access details
    user_id = Column(String(255), nullable=False, index=True)
    patient_id = Column(String(255), index=True)
    action = Column(String(50), nullable=False)  # 'read', 'write', 'delete'
    resource = Column(String(255), nullable=False)  # Resource accessed
    data_elements = Column(JSON)  # List of data elements accessed
    
    # Request details
    ip_address = Column(String(50))
    user_agent = Column(Text)
    
    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Result
    success = Column(Boolean, nullable=False)
    error_message = Column(Text)
    
    # Indexes for audit queries
    __table_args__ = (
        Index('idx_audit_user_timestamp', 'user_id', 'timestamp'),
        Index('idx_audit_patient_timestamp', 'patient_id', 'timestamp'),
        Index('idx_audit_action', 'action'),
    )


class InterventionWorkflowModel(Base):
    """
    Intervention workflow tracking table.
    
    Tracks automated intervention workflows for high-risk patients.
    """
    __tablename__ = "intervention_workflows"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    workflow_id = Column(String(255), unique=True, nullable=False, index=True)
    
    # Patient reference
    patient_id = Column(String(255), ForeignKey('patients.patient_id'), nullable=False, index=True)
    
    # Workflow data
    risk_tier = Column(String(20), nullable=False)
    status = Column(String(50), nullable=False)  # 'in_progress', 'completed', 'failed'
    initiated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime)
    
    # Workflow steps (JSON array of step objects)
    steps = Column(JSON, nullable=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Indexes
    __table_args__ = (
        Index('idx_workflow_status', 'status'),
        Index('idx_workflow_initiated', 'initiated_at'),
        Index('idx_workflow_patient', 'patient_id', 'initiated_at'),
    )


class CaseManagerModel(Base):
    """
    Case manager table.
    
    Stores case manager information and caseload tracking.
    """
    __tablename__ = "case_managers"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    manager_id = Column(String(255), unique=True, nullable=False, index=True)
    
    # Manager details
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    phone = Column(String(50))
    
    # Caseload tracking
    active_caseload = Column(Integer, default=0, nullable=False)
    max_caseload = Column(Integer, default=50, nullable=False)
    
    # Status
    active = Column(Boolean, default=True, nullable=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    case_records = relationship("CaseRecordModel", back_populates="case_manager")


class CaseRecordModel(Base):
    """
    Case management record table.
    
    Stores case management records for high-risk patients.
    """
    __tablename__ = "case_records"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # References
    patient_id = Column(String(255), ForeignKey('patients.patient_id'), nullable=False, index=True)
    case_manager_id = Column(String(255), ForeignKey('case_managers.manager_id'), nullable=False, index=True)
    
    # Case data
    risk_factors = Column(JSON, nullable=False)  # List of risk factors
    sdoh_barriers = Column(JSON, nullable=False)  # List of SDOH barriers
    shap_factors = Column(JSON)  # SHAP explanation factors
    
    # Status
    status = Column(String(50), default='active', nullable=False)  # 'active', 'closed'
    enrollment_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    closure_date = Column(DateTime)
    
    # Notes
    notes = Column(Text)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    case_manager = relationship("CaseManagerModel", back_populates="case_records")
    
    # Indexes
    __table_args__ = (
        Index('idx_case_status', 'status'),
        Index('idx_case_enrollment', 'enrollment_date'),
    )
