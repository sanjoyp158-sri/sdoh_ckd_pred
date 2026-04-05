"""
Patient data models based on design document.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple
from enum import Enum


class RiskTier(Enum):
    """Risk tier classification based on prediction score."""
    HIGH = "high"  # score > 0.65
    MODERATE = "moderate"  # 0.35 <= score <= 0.65
    LOW = "low"  # score < 0.35


@dataclass
class Address:
    """Patient address information."""
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    zcta: Optional[str] = None  # ZIP Code Tabulation Area


@dataclass
class Demographics:
    """Patient demographic information."""
    age: int
    sex: str  # 'M', 'F'
    race: Optional[str] = None  # Not used in model, only for fairness monitoring
    ethnicity: Optional[str] = None  # Not used in model, only for fairness monitoring
    address: Optional[Address] = None


@dataclass
class Medication:
    """Medication record."""
    name: str
    category: str  # 'ACE_inhibitor', 'ARB', 'SGLT2_inhibitor', 'GLP1_agonist', etc.
    start_date: Optional[datetime] = None
    active: bool = True


@dataclass
class ClinicalRecord:
    """Clinical data for CKD patient."""
    egfr: float  # mL/min/1.73m²
    egfr_history: List[Tuple[datetime, float]]  # For slope calculation
    uacr: float  # mg/g
    hba1c: float  # %
    systolic_bp: int  # mmHg
    diastolic_bp: int  # mmHg
    bmi: float  # kg/m²
    medications: List[Medication]
    ckd_stage: str  # '2', '3a', '3b'
    diagnosis_date: datetime
    comorbidities: List[str]  # Diabetes, hypertension, CVD


@dataclass
class Referral:
    """Specialist referral record."""
    specialty: str
    date: datetime
    completed: bool
    reason: Optional[str] = None


@dataclass
class AdministrativeRecord:
    """Healthcare utilization and administrative data."""
    visit_frequency_12mo: int  # Number of visits in last 12 months
    specialist_referrals: List[Referral]
    insurance_type: str  # 'Medicare', 'Medicaid', 'Commercial', 'Uninsured'
    insurance_status: str  # 'Active', 'Inactive'
    last_visit_date: datetime


@dataclass
class SDOHRecord:
    """Social Determinants of Health data."""
    adi_percentile: int  # 1-100, higher = more disadvantaged
    food_desert: bool  # True if >1 mile from grocery store (urban) or >10 miles (rural)
    housing_stability_score: float  # 0-1, lower = less stable
    transportation_access_score: float  # 0-1, higher = better access
    rural_urban_code: str  # RUCA code


@dataclass
class UnifiedPatientRecord:
    """Complete patient record combining all data sources."""
    patient_id: str
    demographics: Demographics
    clinical: ClinicalRecord
    administrative: AdministrativeRecord
    sdoh: SDOHRecord
    created_at: datetime
    updated_at: datetime


@dataclass
class PredictionResult:
    """ML prediction result."""
    patient_id: str
    risk_score: float  # 0-1
    risk_tier: RiskTier
    prediction_date: datetime
    model_version: str
    processing_time_ms: int


@dataclass
class Factor:
    """Individual risk factor from SHAP explanation."""
    feature_name: str
    feature_value: any
    shap_value: float  # Contribution to prediction
    category: str  # 'clinical', 'administrative', 'sdoh'
    direction: str  # 'increases_risk', 'decreases_risk'


@dataclass
class CategorizedFactors:
    """Risk factors categorized by type."""
    clinical: List[Factor]
    administrative: List[Factor]
    sdoh: List[Factor]


@dataclass
class SHAPExplanation:
    """SHAP-based explanation for prediction."""
    patient_id: str
    baseline_risk: float  # Population average risk
    prediction: float  # Individual risk score
    shap_values: dict  # Feature name -> SHAP value
    top_factors: List[Factor]  # Top 5 contributing factors
    categorized_factors: CategorizedFactors
    computation_time_ms: int
