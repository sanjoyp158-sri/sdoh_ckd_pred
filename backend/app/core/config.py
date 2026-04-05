"""
Core configuration settings for SDOH-CKDPred application.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    APP_NAME: str = "SDOH-CKDPred"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    
    # API
    API_V1_PREFIX: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = "postgresql://ckd_user:ckd_password@localhost:5432/ckd_db"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # ML Model
    MODEL_PATH: str = "models/sdoh_ckdpred_final.json"
    MODEL_VERSION: str = "1.0.0"
    
    # Risk Thresholds (from paper - Youden's J statistic optimization)
    RISK_THRESHOLD_HIGH: float = 0.65
    RISK_THRESHOLD_MODERATE: float = 0.35
    
    # Performance SLAs
    PREDICTION_TIMEOUT_MS: int = 500
    SHAP_TIMEOUT_MS: int = 200
    INTERVENTION_INITIATION_HOURS: int = 1
    
    # Cost-Effectiveness
    TARGET_BCR: float = 3.75
    COST_STAGE5_PER_YEAR: int = 89000
    COST_STAGE3_PER_YEAR: int = 20000
    
    # Fairness Monitoring
    MAX_AUROC_DISPARITY: float = 0.05
    
    # CORS
    CORS_ORIGINS: list = ["http://localhost:3000"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
