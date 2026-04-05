"""
ML-specific data models for model metrics and versioning.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional


@dataclass
class SubgroupMetrics:
    """Performance metrics for a specific demographic subgroup."""
    subgroup_name: str
    sample_size: int
    auroc: float
    sensitivity: float
    specificity: float
    ppv: float  # Positive predictive value
    npv: float  # Negative predictive value


@dataclass
class ModelMetrics:
    """Comprehensive model performance metrics."""
    auroc: float
    sensitivity: float
    specificity: float
    ppv: float  # Positive predictive value
    npv: float  # Negative predictive value
    subgroup_metrics: Dict[str, SubgroupMetrics]  # By race/ethnicity
    training_date: datetime
    model_version: str


@dataclass
class ModelRegistryEntry:
    """Model registry entry for versioning and tracking."""
    model_id: str
    model_version: str
    model_path: str
    metrics: ModelMetrics
    created_at: datetime
    is_production: bool
    previous_version: Optional[str] = None
    deployment_date: Optional[datetime] = None
    ab_test_percentage: float = 0.0  # 0-100, percentage of traffic for A/B testing
