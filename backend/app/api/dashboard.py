"""
Dashboard API endpoints for provider interface.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from typing import List, Optional
from datetime import datetime

from app.models.api import (
    PatientListFilters,
    PatientListResponse,
    PatientSummary,
    PatientDetail,
    AcknowledgmentRequest,
    AcknowledgmentResponse,
    RiskTierEnum,
    ClinicalValues,
    AdministrativeMetrics,
    SDOHIndicators,
    FactorResponse,
    ErrorResponse
)
from app.core.security import get_current_user, require_role
from app.core.audit import audit_logger
from app.models.api import User


router = APIRouter(prefix="/patients", tags=["dashboard"])


# Mock databases (in production, use real database)
PATIENTS_DB = {}
ACKNOWLEDGMENTS_DB = {}


def create_mock_patients():
    """Create mock patient data for demonstration."""
    mock_patients = [
        PatientSummary(
            patient_id="patient-001",
            age=68,
            sex="F",
            ckd_stage="3a",
            risk_score=0.72,
            risk_tier=RiskTierEnum.HIGH,
            prediction_date=datetime(2024, 1, 15, 10, 30),
            egfr=28.5,
            acknowledged=False
        ),
        PatientSummary(
            patient_id="patient-002",
            age=55,
            sex="M",
            ckd_stage="2",
            risk_score=0.45,
            risk_tier=RiskTierEnum.MODERATE,
            prediction_date=datetime(2024, 1, 14, 14, 20),
            egfr=65.2,
            acknowledged=False
        ),
        PatientSummary(
            patient_id="patient-003",
            age=72,
            sex="M",
            ckd_stage="3b",
            risk_score=0.82,
            risk_tier=RiskTierEnum.HIGH,
            prediction_date=datetime(2024, 1, 13, 9, 15),
            egfr=22.1,
            acknowledged=True
        ),
    ]
    
    for patient in mock_patients:
        PATIENTS_DB[patient.patient_id] = patient
    
    return mock_patients


# Initialize mock data
create_mock_patients()


@router.get(
    "",
    response_model=PatientListResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"}
    }
)
async def get_patient_list(
    request: Request,
    risk_tier: Optional[RiskTierEnum] = Query(None, description="Filter by risk tier"),
    ckd_stage: Optional[str] = Query(None, description="Filter by CKD stage"),
    date_from: Optional[datetime] = Query(None, description="Filter from date"),
    date_to: Optional[datetime] = Query(None, description="Filter to date"),
    limit: int = Query(100, ge=1, le=1000, description="Max results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_user: User = Depends(require_role(["provider", "admin", "case_manager"]))
):
    """
    Get list of patients with filtering and pagination.
    
    Supports filtering by:
    - Risk tier (high, moderate, low)
    - CKD stage (2, 3a, 3b)
    - Date range
    
    Args:
        risk_tier: Optional risk tier filter
        ckd_stage: Optional CKD stage filter
        date_from: Optional start date filter
        date_to: Optional end date filter
        limit: Maximum number of results
        offset: Offset for pagination
        current_user: Authenticated user
        
    Returns:
        PatientListResponse with filtered patients
    """
    # Audit log
    audit_logger.log_access(
        user_id=current_user.user_id,
        username=current_user.username,
        action="read",
        resource_type="patient_list",
        resource_id="all",
        data_elements=["patient_summary"],
        ip_address=request.client.host if request.client else None,
        success=True
    )
    
    # Get all patients
    all_patients = list(PATIENTS_DB.values())
    
    # Apply filters
    filtered_patients = all_patients
    
    if risk_tier:
        filtered_patients = [p for p in filtered_patients if p.risk_tier == risk_tier]
    
    if ckd_stage:
        filtered_patients = [p for p in filtered_patients if p.ckd_stage == ckd_stage]
    
    if date_from:
        filtered_patients = [p for p in filtered_patients if p.prediction_date >= date_from]
    
    if date_to:
        filtered_patients = [p for p in filtered_patients if p.prediction_date <= date_to]
    
    # Sort by prediction date (most recent first)
    filtered_patients.sort(key=lambda x: x.prediction_date, reverse=True)
    
    # Apply pagination
    total = len(filtered_patients)
    paginated_patients = filtered_patients[offset:offset + limit]
    
    return PatientListResponse(
        patients=paginated_patients,
        total=total,
        limit=limit,
        offset=offset
    )


@router.get(
    "/{patient_id}",
    response_model=PatientDetail,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "Patient not found"}
    }
)
async def get_patient_detail(
    request: Request,
    patient_id: str,
    current_user: User = Depends(require_role(["provider", "admin", "case_manager"]))
):
    """
    Get detailed patient information including SHAP explanations.
    
    Args:
        patient_id: Patient identifier
        current_user: Authenticated user
        
    Returns:
        PatientDetail with complete patient information
        
    Raises:
        HTTPException: If patient not found
    """
    # Audit log
    audit_logger.log_access(
        user_id=current_user.user_id,
        username=current_user.username,
        action="read",
        resource_type="patient",
        resource_id=patient_id,
        data_elements=["patient_detail", "clinical", "administrative", "sdoh", "shap_values"],
        ip_address=request.client.host if request.client else None,
        success=True
    )
    
    # Check if patient exists
    patient_summary = PATIENTS_DB.get(patient_id)
    if not patient_summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id} not found"
        )
    
    # Get acknowledgment info
    ack = ACKNOWLEDGMENTS_DB.get(patient_id)
    
    # Create detailed patient response (mock data)
    patient_detail = PatientDetail(
        patient_id=patient_id,
        age=patient_summary.age,
        sex=patient_summary.sex,
        risk_score=patient_summary.risk_score,
        risk_tier=patient_summary.risk_tier,
        prediction_date=patient_summary.prediction_date,
        model_version="v1.0.0",
        clinical=ClinicalValues(
            egfr=patient_summary.egfr,
            uacr=450.0,
            hba1c=7.2,
            systolic_bp=145,
            diastolic_bp=88,
            bmi=28.5,
            ckd_stage=patient_summary.ckd_stage
        ),
        administrative=AdministrativeMetrics(
            visit_frequency_12mo=8,
            specialist_referrals_count=2,
            insurance_type="Medicare",
            insurance_status="Active"
        ),
        sdoh=SDOHIndicators(
            adi_percentile=92,
            food_desert=True,
            housing_stability_score=0.45,
            transportation_access_score=0.32
        ),
        top_factors=[
            FactorResponse(
                feature_name="egfr",
                feature_value=str(patient_summary.egfr),
                shap_value=0.15,
                category="clinical",
                direction="increases_risk"
            ),
            FactorResponse(
                feature_name="adi_percentile",
                feature_value="92",
                shap_value=0.08,
                category="sdoh",
                direction="increases_risk"
            ),
            FactorResponse(
                feature_name="uacr",
                feature_value="450",
                shap_value=0.07,
                category="clinical",
                direction="increases_risk"
            ),
            FactorResponse(
                feature_name="food_desert",
                feature_value="True",
                shap_value=0.05,
                category="sdoh",
                direction="increases_risk"
            ),
            FactorResponse(
                feature_name="hba1c",
                feature_value="7.2",
                shap_value=0.04,
                category="clinical",
                direction="increases_risk"
            )
        ],
        acknowledged=ack is not None if ack else patient_summary.acknowledged,
        acknowledged_by=ack.get("provider_id") if ack else None,
        acknowledged_at=ack.get("acknowledged_at") if ack else None
    )
    
    return patient_detail


@router.post(
    "/acknowledgments",
    response_model=AcknowledgmentResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "Patient not found"}
    }
)
async def acknowledge_patient(
    request: Request,
    ack_request: AcknowledgmentRequest,
    current_user: User = Depends(require_role(["provider", "admin"]))
):
    """
    Acknowledge a high-risk patient alert.
    
    Records that a provider has reviewed and acknowledged a high-risk
    patient, including timestamp and optional notes.
    
    Args:
        ack_request: Acknowledgment details
        current_user: Authenticated user (provider or admin)
        
    Returns:
        AcknowledgmentResponse confirming the acknowledgment
        
    Raises:
        HTTPException: If patient not found
    """
    patient_id = ack_request.patient_id
    
    # Check if patient exists
    if patient_id not in PATIENTS_DB:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id} not found"
        )
    
    # Create acknowledgment
    acknowledged_at = datetime.now()
    ACKNOWLEDGMENTS_DB[patient_id] = {
        "patient_id": patient_id,
        "provider_id": ack_request.provider_id,
        "acknowledged_at": acknowledged_at,
        "notes": ack_request.notes
    }
    
    # Update patient summary
    if patient_id in PATIENTS_DB:
        PATIENTS_DB[patient_id].acknowledged = True
    
    # Audit log
    audit_logger.log_access(
        user_id=current_user.user_id,
        username=current_user.username,
        action="write",
        resource_type="acknowledgment",
        resource_id=patient_id,
        data_elements=["acknowledgment"],
        ip_address=request.client.host if request.client else None,
        success=True
    )
    
    return AcknowledgmentResponse(
        patient_id=patient_id,
        provider_id=ack_request.provider_id,
        acknowledged_at=acknowledged_at,
        success=True
    )
