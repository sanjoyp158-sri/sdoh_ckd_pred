"""
Database package for CKD prediction system.

Provides database models, DAOs, encryption, and session management.
"""

from app.db.database import Base, engine, SessionLocal, get_db, init_db
from app.db.encryption import (
    EncryptionService,
    get_encryption_service,
    generate_encryption_key,
    derive_key_from_password
)
from app.db.models import (
    PatientModel,
    PredictionModel,
    RiskTierChangeLogModel,
    AuditLogModel,
    InterventionWorkflowModel,
    CaseManagerModel,
    CaseRecordModel
)
from app.db.dao import (
    PatientDAO,
    PredictionDAO,
    AuditLogDAO,
    RiskTierChangeLogDAO
)

__all__ = [
    # Database
    'Base',
    'engine',
    'SessionLocal',
    'get_db',
    'init_db',
    # Encryption
    'EncryptionService',
    'get_encryption_service',
    'generate_encryption_key',
    'derive_key_from_password',
    # Models
    'PatientModel',
    'PredictionModel',
    'RiskTierChangeLogModel',
    'AuditLogModel',
    'InterventionWorkflowModel',
    'CaseManagerModel',
    'CaseRecordModel',
    # DAOs
    'PatientDAO',
    'PredictionDAO',
    'AuditLogDAO',
    'RiskTierChangeLogDAO',
]
