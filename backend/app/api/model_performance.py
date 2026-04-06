"""
Model Performance API endpoint.
Serves evaluation metrics from the pipeline outputs for the frontend dashboard.
"""

import os
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Optional
import csv

from app.core.security import get_current_user
from app.models.api import User

router = APIRouter(prefix="/model-performance", tags=["model-performance"])

PIPELINE_OUTPUTS = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "ckd_pipeline", "outputs"
)


class MetricRow(BaseModel):
    model: str
    cohort: str
    AUROC: float
    AUROC_95CI: Optional[str] = None
    AUPRC: float
    Brier: float
    Sensitivity: float
    Specificity: float
    PPV: float
    NPV: float
    F1: float


class SubgroupRow(BaseModel):
    subgroup: str
    N: int
    AUROC: float
    AUROC_95CI: Optional[str] = None
    PPV: float
    Sensitivity: float
    F1: float


class ShapFeature(BaseModel):
    feature: str
    shap_pct: float
    category: str


class ModelPerformanceResponse(BaseModel):
    performance_metrics: List[MetricRow]
    subgroup_equity: List[SubgroupRow]
    shap_importance: List[ShapFeature]
    model_comparison: List[dict]


def read_csv_safe(filename: str) -> List[dict]:
    filepath = os.path.join(PIPELINE_OUTPUTS, filename)
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r") as f:
        return list(csv.DictReader(f))


@router.get("", response_model=ModelPerformanceResponse)
async def get_model_performance(current_user: User = Depends(get_current_user)):
    """Return model evaluation metrics for the dashboard."""

    # Performance metrics (Table 2)
    perf_raw = read_csv_safe("table2_performance_metrics.csv")
    performance = []
    for row in perf_raw:
        performance.append(MetricRow(
            model=row.get("Model", ""),
            cohort=row.get("Cohort", ""),
            AUROC=float(row.get("AUROC", 0)),
            AUROC_95CI=row.get("AUROC_95CI", ""),
            AUPRC=float(row.get("AUPRC", 0)),
            Brier=float(row.get("Brier", 0)),
            Sensitivity=float(row.get("Sensitivity", 0)),
            Specificity=float(row.get("Specificity", 0)),
            PPV=float(row.get("PPV", 0)),
            NPV=float(row.get("NPV", 0)),
            F1=float(row.get("F1", 0)),
        ))

    # Subgroup equity (Table 3)
    sub_raw = read_csv_safe("table3_subgroup_performance.csv")
    subgroups = []
    for row in sub_raw:
        subgroups.append(SubgroupRow(
            subgroup=row.get("Subgroup", ""),
            N=int(float(row.get("N", 0))),
            AUROC=float(row.get("AUROC", 0)),
            AUROC_95CI=row.get("AUROC_95CI", ""),
            PPV=float(row.get("PPV", 0)),
            Sensitivity=float(row.get("Sensitivity", 0)),
            F1=float(row.get("F1", 0)),
        ))

    # SHAP feature importance (top 15)
    shap_raw = read_csv_safe("shap_feature_importance.csv")
    shap_features = []
    for row in shap_raw[:15]:
        shap_features.append(ShapFeature(
            feature=row.get("feature", ""),
            shap_pct=round(float(row.get("shap_pct", 0)), 2),
            category=row.get("category", ""),
        ))

    # Model comparison
    comparison = read_csv_safe("model_comparison.csv")

    return ModelPerformanceResponse(
        performance_metrics=performance,
        subgroup_equity=subgroups,
        shap_importance=shap_features,
        model_comparison=comparison,
    )
