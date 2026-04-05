"""
API request and response models using Pydantic.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime
from enum import Enum


class RiskTierEnum(str, Enum):
    """Risk tier classification."""
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"


# ============================================================================
# Prediction API Models
# ============================================================================

class PredictionRequest(BaseModel):
    """Request model for CKD progression prediction."""
    patient_id: str = Field(..., description="Unique patient identifier")
    
    class Config:
        json_schema_extra = {
            "example": {
                "patient_id": "patient-12345"
            }
        }


class FactorResponse(BaseModel):
    """Individual risk factor in SHAP explanation."""
    feature_name: str
    feature_value: str
    shap_value: float
    category: str  # 'clinical', 'administrative', 'sdoh'
    direction: str  # 'increases_risk', 'decreases_risk'


class PredictionResponse(BaseModel):
    """Response model for CKD progression prediction."""
    patient_id: str
    risk_score: float = Field(..., ge=0.0, le=1.0, description="Risk score between 0 and 1")
    risk_tier: RiskTierEnum
    prediction_date: datetime
    model_version: str
    processing_time_ms: int
    top_factors: List[FactorResponse] = Field(default_factory=list, description="Top 5 contributing factors")
    
    class Config:
        json_schema_extra = {
            "example": {
                "patient_id": "patient-12345",
                "risk_score": 0.72,
                "risk_tier": "high",
                "prediction_date": "2024-01-15T10:30:00",
                "model_version": "v1.0.0",
                "processing_time_ms": 450,
                "top_factors": [
                    {
                        "feature_name": "egfr",
                        "feature_value": "28.5",
                        "shap_value": 0.15,
                        "category": "clinical",
                        "direction": "increases_risk"
                    }
                ]
            }
        }


# ============================================================================
# Dashboard API Models
# ============================================================================

class PatientListFilters(BaseModel):
    """Filters for patient list query."""
    risk_tier: Optional[RiskTierEnum] = Field(None, description="Filter by risk tier")
    ckd_stage: Optional[str] = Field(None, description="Filter by CKD stage (2, 3a, 3b)")
    date_from: Optional[datetime] = Field(None, description="Filter predictions from this date")
    date_to: Optional[datetime] = Field(None, description="Filter predictions to this date")
    limit: int = Field(100, ge=1, le=1000, description="Maximum number of results")
    offset: int = Field(0, ge=0, description="Offset for pagination")
    
    @validator('ckd_stage')
    def validate_ckd_stage(cls, v):
        if v is not None and v not in ['2', '3a', '3b']:
            raise ValueError("CKD stage must be one of: 2, 3a, 3b")
        return v


class PatientSummary(BaseModel):
    """Summary information for patient list."""
    patient_id: str
    age: int
    sex: str
    ckd_stage: str
    risk_score: float
    risk_tier: RiskTierEnum
    prediction_date: datetime
    egfr: float
    acknowledged: bool = False
    
    class Config:
        json_schema_extra = {
            "example": {
                "patient_id": "patient-12345",
                "age": 68,
                "sex": "F",
                "ckd_stage": "3a",
                "risk_score": 0.72,
                "risk_tier": "high",
                "prediction_date": "2024-01-15T10:30:00",
                "egfr": 28.5,
                "acknowledged": False
            }
        }


class PatientListResponse(BaseModel):
    """Response model for patient list."""
    patients: List[PatientSummary]
    total: int
    limit: int
    offset: int


class ClinicalValues(BaseModel):
    """Clinical measurements for patient detail."""
    egfr: float
    uacr: float
    hba1c: float
    systolic_bp: int
    diastolic_bp: int
    bmi: float
    ckd_stage: str


class AdministrativeMetrics(BaseModel):
    """Administrative metrics for patient detail."""
    visit_frequency_12mo: int
    specialist_referrals_count: int
    insurance_type: str
    insurance_status: str


class SDOHIndicators(BaseModel):
    """SDOH indicators for patient detail."""
    adi_percentile: int
    food_desert: bool
    housing_stability_score: float
    transportation_access_score: float


class PatientDetail(BaseModel):
    """Detailed patient information."""
    patient_id: str
    age: int
    sex: str
    risk_score: float
    risk_tier: RiskTierEnum
    prediction_date: datetime
    model_version: str
    clinical: ClinicalValues
    administrative: AdministrativeMetrics
    sdoh: SDOHIndicators
    top_factors: List[FactorResponse]
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None


class AcknowledgmentRequest(BaseModel):
    """Request to acknowledge a high-risk alert."""
    patient_id: str = Field(..., description="Patient ID to acknowledge")
    provider_id: str = Field(..., description="Provider ID making the acknowledgment")
    notes: Optional[str] = Field(None, description="Optional notes")
    
    class Config:
        json_schema_extra = {
            "example": {
                "patient_id": "patient-12345",
                "provider_id": "provider-789",
                "notes": "Scheduled follow-up appointment"
            }
        }


class AcknowledgmentResponse(BaseModel):
    """Response for acknowledgment."""
    patient_id: str
    provider_id: str
    acknowledged_at: datetime
    success: bool = True


# ============================================================================
# Authentication Models
# ============================================================================

class Token(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Data encoded in JWT token."""
    username: Optional[str] = None
    user_id: Optional[str] = None
    role: Optional[str] = None


class UserLogin(BaseModel):
    """User login credentials."""
    username: str
    password: str


class User(BaseModel):
    """User model."""
    user_id: str
    username: str
    email: Optional[str] = None
    role: str  # 'provider', 'admin', 'case_manager'
    active: bool = True


# ============================================================================
# Error Models
# ============================================================================

class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
