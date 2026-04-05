"""
Prediction API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List, Optional
import time
from datetime import datetime
import logging

from app.models.api import (
    PredictionRequest,
    PredictionResponse,
    FactorResponse,
    RiskTierEnum,
    ErrorResponse
)
from app.models.patient import UnifiedPatientRecord, RiskTier
from app.core.security import get_current_user, require_role
from app.core.audit import audit_logger
from app.models.api import User
from app.core.config import settings
from app.db.database import get_db
from app.db.dao import PredictionDAO

# Import services
from app.services.data_integration import DataIntegrationLayer
from app.ml.analytics_engine import MLAnalyticsEngine
from app.ml.shap_explainer import SHAPExplainer
from app.services.risk_stratification import RiskStratificationModule
from app.services.intervention_workflow import InterventionWorkflowEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/predictions", tags=["predictions"])


# Singleton service instances
_data_integration: Optional[DataIntegrationLayer] = None
_ml_engine: Optional[MLAnalyticsEngine] = None
_shap_explainer: Optional[SHAPExplainer] = None
_risk_stratification: Optional[RiskStratificationModule] = None
_intervention_engine: Optional[InterventionWorkflowEngine] = None


def get_data_integration() -> DataIntegrationLayer:
    """Get or create DataIntegrationLayer singleton."""
    global _data_integration
    if _data_integration is None:
        _data_integration = DataIntegrationLayer()
    return _data_integration


def get_ml_engine() -> MLAnalyticsEngine:
    """Get or create MLAnalyticsEngine singleton."""
    global _ml_engine
    if _ml_engine is None:
        _ml_engine = MLAnalyticsEngine()
        # Try to load model from settings, but don't fail if not available
        try:
            if settings.MODEL_PATH:
                _ml_engine.load_model(settings.MODEL_PATH)
        except Exception as e:
            logger.warning(f"Could not load ML model: {e}")
    return _ml_engine


def get_shap_explainer() -> SHAPExplainer:
    """Get or create SHAPExplainer singleton."""
    global _shap_explainer
    if _shap_explainer is None:
        # SHAP explainer needs the ML engine's model
        ml_engine = get_ml_engine()
        if ml_engine._classifier is None:
            logger.warning("ML model not loaded. SHAP explainer cannot be initialized.")
            return None
        
        feature_names = ml_engine.get_feature_names()
        _shap_explainer = SHAPExplainer(
            model=ml_engine._classifier._model,
            feature_names=feature_names
        )
    return _shap_explainer


def get_risk_stratification() -> RiskStratificationModule:
    """Get or create RiskStratificationModule singleton."""
    global _risk_stratification
    if _risk_stratification is None:
        _risk_stratification = RiskStratificationModule()
    return _risk_stratification


def get_intervention_engine() -> InterventionWorkflowEngine:
    """Get or create InterventionWorkflowEngine singleton."""
    global _intervention_engine
    if _intervention_engine is None:
        _intervention_engine = InterventionWorkflowEngine()
    return _intervention_engine


def convert_risk_tier(tier: RiskTier) -> RiskTierEnum:
    """Convert internal RiskTier to API RiskTierEnum."""
    return RiskTierEnum(tier.value)


def convert_factors_to_response(factors: List) -> List[FactorResponse]:
    """Convert Factor objects to FactorResponse models."""
    return [
        FactorResponse(
            feature_name=f.feature_name,
            feature_value=str(f.feature_value),
            shap_value=f.shap_value,
            category=f.category,
            direction=f.direction
        )
        for f in factors
    ]


@router.post(
    "/predict",
    response_model=PredictionResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "Patient not found"},
        500: {"model": ErrorResponse, "description": "Prediction failed"}
    }
)
async def predict_ckd_progression(
    request: Request,
    prediction_request: PredictionRequest,
    current_user: User = Depends(require_role(["provider", "admin"])),
    db: Session = Depends(get_db)
):
    """
    Generate CKD progression risk prediction for a patient.
    
    This endpoint:
    1. Retrieves patient data via DataIntegrationLayer
    2. Generates risk prediction using MLAnalyticsEngine
    3. Computes SHAP explanations via SHAPExplainer
    4. Stratifies patient into risk tier via RiskStratificationModule
    5. Stores prediction in database
    6. Triggers intervention workflow for HIGH risk patients
    7. Logs the prediction for audit
    
    Args:
        prediction_request: Patient ID to predict
        current_user: Authenticated user (provider or admin role required)
        db: Database session
        
    Returns:
        PredictionResponse with risk score, tier, and explanations
        
    Raises:
        HTTPException: If patient not found or prediction fails
    """
    start_time = time.time()
    patient_id = prediction_request.patient_id
    
    try:
        # Get service instances
        data_integration = get_data_integration()
        ml_engine = get_ml_engine()
        shap_explainer = get_shap_explainer()
        risk_stratification = get_risk_stratification()
        intervention_engine = get_intervention_engine()
        
        # Check if ML model is loaded
        if ml_engine._classifier is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="ML model not loaded. Service unavailable."
            )
        
        # 1. Fetch patient data
        logger.info(f"Fetching patient data for {patient_id}")
        patient = await data_integration.get_unified_patient_record(patient_id)
        
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient {patient_id} not found"
            )
        
        # 2. Generate ML prediction
        logger.info(f"Generating prediction for {patient_id}")
        prediction_result = ml_engine.predict_progression_risk(patient)
        
        # Check prediction latency requirement (< 500ms)
        prediction_time_ms = int((time.time() - start_time) * 1000)
        if prediction_time_ms > settings.PREDICTION_TIMEOUT_MS:
            logger.warning(
                f"Prediction latency {prediction_time_ms}ms exceeds "
                f"SLA of {settings.PREDICTION_TIMEOUT_MS}ms"
            )
        
        # 3. Compute SHAP explanations
        logger.info(f"Computing SHAP explanations for {patient_id}")
        shap_start = time.time()
        
        if shap_explainer is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="SHAP explainer not available. Service unavailable."
            )
        
        # Extract features for SHAP
        features_df = ml_engine.extract_features(patient)
        features_array = features_df.values[0]  # Get first row as array
        feature_values = features_df.iloc[0].to_dict()  # Get as dictionary
        
        shap_explanation = shap_explainer.explain_prediction(
            patient=patient,
            prediction=prediction_result.risk_score,
            features=features_array,
            feature_values=feature_values
        )
        shap_time_ms = int((time.time() - shap_start) * 1000)
        
        # Check SHAP latency requirement (< 200ms)
        if shap_time_ms > settings.SHAP_TIMEOUT_MS:
            logger.warning(
                f"SHAP explanation latency {shap_time_ms}ms exceeds "
                f"SLA of {settings.SHAP_TIMEOUT_MS}ms"
            )
        
        # 4. Stratify risk tier
        logger.info(f"Stratifying risk tier for {patient_id}")
        risk_tier = risk_stratification.stratify(prediction_result.risk_score)
        
        # 5. Store prediction in database
        logger.info(f"Storing prediction for {patient_id}")
        prediction_dao = PredictionDAO(db)
        db_prediction = prediction_dao.create(prediction_result, shap_explanation)
        
        # 6. Trigger intervention workflow for HIGH risk patients
        if risk_tier == RiskTier.HIGH:
            logger.info(f"Initiating intervention workflow for HIGH risk patient {patient_id}")
            try:
                workflow = await intervention_engine.initiate_workflow(
                    patient=patient,
                    risk_score=prediction_result.risk_score,
                    risk_tier=risk_tier
                )
                # Execute workflow asynchronously (don't block response)
                # In production, this would be handled by a background task queue
                await intervention_engine.execute_workflow(workflow, patient)
                logger.info(f"Intervention workflow {workflow.workflow_id} initiated")
            except Exception as workflow_error:
                # Log but don't fail the prediction
                logger.error(
                    f"Failed to initiate intervention workflow for {patient_id}: {workflow_error}"
                )
        
        # Calculate total processing time
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        # Build response
        prediction_response = PredictionResponse(
            patient_id=patient_id,
            risk_score=prediction_result.risk_score,
            risk_tier=convert_risk_tier(risk_tier),
            prediction_date=prediction_result.prediction_date,
            model_version=prediction_result.model_version,
            processing_time_ms=processing_time_ms,
            top_factors=convert_factors_to_response(shap_explanation.top_factors)
        )
        
        # 7. Audit log
        audit_logger.log_access(
            user_id=current_user.user_id,
            username=current_user.username,
            action="predict",
            resource_type="prediction",
            resource_id=patient_id,
            data_elements=["risk_score", "risk_tier", "shap_values"],
            ip_address=request.client.host if request.client else None,
            success=True
        )
        
        logger.info(
            f"Prediction completed for {patient_id}: "
            f"risk_score={prediction_result.risk_score:.3f}, "
            f"risk_tier={risk_tier.value}, "
            f"processing_time={processing_time_ms}ms"
        )
        
        return prediction_response
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Audit log failure
        audit_logger.log_access(
            user_id=current_user.user_id,
            username=current_user.username,
            action="predict",
            resource_type="prediction",
            resource_id=patient_id,
            ip_address=request.client.host if request.client else None,
            success=False,
            error_message=str(e)
        )
        
        logger.error(f"Prediction failed for {patient_id}: {e}", exc_info=True)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction failed: {str(e)}"
        )


@router.get(
    "/{patient_id}",
    response_model=PredictionResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "Prediction not found"}
    }
)
async def get_prediction(
    request: Request,
    patient_id: str,
    current_user: User = Depends(require_role(["provider", "admin", "case_manager"])),
    db: Session = Depends(get_db)
):
    """
    Retrieve existing prediction for a patient.
    
    Args:
        patient_id: Patient identifier
        current_user: Authenticated user
        db: Database session
        
    Returns:
        PredictionResponse with risk score and explanations
        
    Raises:
        HTTPException: If prediction not found
    """
    try:
        # Retrieve from database
        prediction_dao = PredictionDAO(db)
        db_prediction = prediction_dao.get_latest_by_patient(patient_id)
        
        if not db_prediction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Prediction not found for patient {patient_id}"
            )
        
        # Convert database model to response
        top_factors = []
        if db_prediction.top_factors:
            top_factors = [
                FactorResponse(
                    feature_name=f["feature_name"],
                    feature_value=f["feature_value"],
                    shap_value=f["shap_value"],
                    category=f["category"],
                    direction=f["direction"]
                )
                for f in db_prediction.top_factors
            ]
        
        prediction_response = PredictionResponse(
            patient_id=db_prediction.patient_id,
            risk_score=db_prediction.risk_score,
            risk_tier=RiskTierEnum(db_prediction.risk_tier),
            prediction_date=db_prediction.prediction_date,
            model_version=db_prediction.model_version,
            processing_time_ms=db_prediction.processing_time_ms,
            top_factors=top_factors
        )
        
        # Audit log
        audit_logger.log_access(
            user_id=current_user.user_id,
            username=current_user.username,
            action="read",
            resource_type="prediction",
            resource_id=patient_id,
            data_elements=["risk_score", "risk_tier", "shap_values"],
            ip_address=request.client.host if request.client else None,
            success=True
        )
        
        return prediction_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve prediction for {patient_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve prediction: {str(e)}"
        )
