"""
Database initialization script.

Creates all tables and sets up initial data.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.db.database import Base, engine, SessionLocal
from app.db.models import (
    PatientModel, PredictionModel, RiskTierChangeLogModel,
    AuditLogModel, InterventionWorkflowModel, CaseManagerModel, CaseRecordModel
)
from app.db.encryption import generate_encryption_key
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_tables():
    """Create all database tables."""
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully!")


def verify_encryption_key():
    """Verify that encryption key is set."""
    encryption_key = os.getenv("ENCRYPTION_KEY")
    if not encryption_key:
        logger.warning("=" * 80)
        logger.warning("WARNING: ENCRYPTION_KEY environment variable is not set!")
        logger.warning("Generate a new key using:")
        logger.warning("  python -c 'from app.db.encryption import generate_encryption_key; print(generate_encryption_key())'")
        logger.warning("=" * 80)
        return False
    return True


def init_database():
    """Initialize database with tables and verify configuration."""
    logger.info("Initializing CKD Prediction System database...")
    
    # Verify encryption key
    if not verify_encryption_key():
        logger.error("Database initialization aborted: encryption key not configured")
        return False
    
    # Create tables
    try:
        create_tables()
    except Exception as e:
        logger.error(f"Failed to create tables: {e}")
        return False
    
    logger.info("Database initialization complete!")
    return True


if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)
