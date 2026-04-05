"""
Unit tests for database persistence layer.

Tests CRUD operations, encryption, and DAO functionality.
"""

import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

from app.db.database import Base
from app.db.encryption import EncryptionService, generate_encryption_key
from app.db.dao import PatientDAO, PredictionDAO, AuditLogDAO, RiskTierChangeLogDAO
from app.models.patient import (
    UnifiedPatientRecord, Demographics, Address, ClinicalRecord,
    AdministrativeRecord, SDOHRecord, Medication, Referral,
    PredictionResult, RiskTier
)


# Test database URL (in-memory SQLite for testing)
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture
def test_db():
    """Create test database session."""
    # Create test engine
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Create session
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestSessionLocal()
    
    yield session
    
    # Cleanup
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def encryption_service():
    """Create encryption service with test key."""
    # Generate a test encryption key
    test_key = generate_encryption_key()
    os.environ["ENCRYPTION_KEY"] = test_key
    return EncryptionService(test_key)


@pytest.fixture
def sample_patient():
    """Create sample patient record for testing."""
    address = Address(
        street="123 Main St",
        city="Springfield",
        state="IL",
        zip_code="62701",
        zcta="62701"
    )
    
    demographics = Demographics(
        age=65,
        sex="M",
        race="White",
        ethnicity="Non-Hispanic",
        address=address
    )
    
    medications = [
        Medication(
            name="Lisinopril",
            category="ACE_inhibitor",
            start_date=datetime(2020, 1, 1),
            active=True
        )
    ]
    
    clinical = ClinicalRecord(
        egfr=45.0,
        egfr_history=[(datetime(2023, 1, 1), 50.0), (datetime(2023, 6, 1), 45.0)],
        uacr=150.0,
        hba1c=7.2,
        systolic_bp=140,
        diastolic_bp=85,
        bmi=28.5,
        medications=medications,
        ckd_stage="3a",
        diagnosis_date=datetime(2020, 1, 1),
        comorbidities=["Diabetes", "Hypertension"]
    )
    
    referrals = [
        Referral(
            specialty="Nephrology",
            date=datetime(2023, 3, 1),
            completed=True,
            reason="CKD management"
        )
    ]
    
    administrative = AdministrativeRecord(
        visit_frequency_12mo=8,
        specialist_referrals=referrals,
        insurance_type="Medicare",
        insurance_status="Active",
        last_visit_date=datetime(2023, 11, 1)
    )
    
    sdoh = SDOHRecord(
        adi_percentile=65,
        food_desert=False,
        housing_stability_score=0.7,
        transportation_access_score=0.6,
        rural_urban_code="urban"
    )
    
    return UnifiedPatientRecord(
        patient_id="TEST-001",
        demographics=demographics,
        clinical=clinical,
        administrative=administrative,
        sdoh=sdoh,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


class TestEncryption:
    """Test encryption service."""
    
    def test_encrypt_decrypt_string(self, encryption_service):
        """Test basic string encryption and decryption."""
        plaintext = "Sensitive patient data"
        
        # Encrypt
        ciphertext = encryption_service.encrypt(plaintext)
        assert ciphertext != plaintext
        assert len(ciphertext) > 0
        
        # Decrypt
        decrypted = encryption_service.decrypt(ciphertext)
        assert decrypted == plaintext
    
    def test_encrypt_empty_string(self, encryption_service):
        """Test encryption of empty string."""
        plaintext = ""
        ciphertext = encryption_service.encrypt(plaintext)
        assert ciphertext == ""
        
        decrypted = encryption_service.decrypt(ciphertext)
        assert decrypted == ""
    
    def test_encrypt_unicode(self, encryption_service):
        """Test encryption of unicode characters."""
        plaintext = "Patient: José García 日本語"
        
        ciphertext = encryption_service.encrypt(plaintext)
        decrypted = encryption_service.decrypt(ciphertext)
        
        assert decrypted == plaintext
    
    def test_different_ciphertexts_for_same_plaintext(self, encryption_service):
        """Test that same plaintext produces different ciphertexts (due to random nonce)."""
        plaintext = "Same data"
        
        ciphertext1 = encryption_service.encrypt(plaintext)
        ciphertext2 = encryption_service.encrypt(plaintext)
        
        # Ciphertexts should be different (different nonces)
        assert ciphertext1 != ciphertext2
        
        # But both should decrypt to same plaintext
        assert encryption_service.decrypt(ciphertext1) == plaintext
        assert encryption_service.decrypt(ciphertext2) == plaintext
    
    def test_decrypt_invalid_data_raises_error(self, encryption_service):
        """Test that decrypting invalid data raises error."""
        with pytest.raises(ValueError):
            encryption_service.decrypt("invalid_base64_data!!!")


class TestPatientDAO:
    """Test PatientDAO CRUD operations."""
    
    def test_create_patient(self, test_db, sample_patient):
        """Test creating a patient record."""
        dao = PatientDAO(test_db)
        
        # Create patient
        db_patient = dao.create(sample_patient)
        
        assert db_patient.id is not None
        assert db_patient.patient_id == sample_patient.patient_id
        assert db_patient.egfr == sample_patient.clinical.egfr
        assert db_patient.adi_percentile == sample_patient.sdoh.adi_percentile
    
    def test_get_patient_by_id(self, test_db, sample_patient):
        """Test retrieving patient by ID."""
        dao = PatientDAO(test_db)
        
        # Create patient
        dao.create(sample_patient)
        
        # Retrieve patient
        retrieved = dao.get_by_id(sample_patient.patient_id)
        
        assert retrieved is not None
        assert retrieved.patient_id == sample_patient.patient_id
        assert retrieved.demographics.age == sample_patient.demographics.age
        assert retrieved.clinical.egfr == sample_patient.clinical.egfr
        assert retrieved.sdoh.adi_percentile == sample_patient.sdoh.adi_percentile
    
    def test_get_nonexistent_patient(self, test_db):
        """Test retrieving non-existent patient returns None."""
        dao = PatientDAO(test_db)
        
        retrieved = dao.get_by_id("NONEXISTENT")
        
        assert retrieved is None
    
    def test_update_patient(self, test_db, sample_patient):
        """Test updating patient record."""
        dao = PatientDAO(test_db)
        
        # Create patient
        dao.create(sample_patient)
        
        # Update patient
        sample_patient.clinical.egfr = 40.0
        sample_patient.demographics.age = 66
        
        updated = dao.update(sample_patient)
        
        assert updated is not None
        assert updated.egfr == 40.0
        assert updated.age == 66
        
        # Verify update persisted
        retrieved = dao.get_by_id(sample_patient.patient_id)
        assert retrieved.clinical.egfr == 40.0
        assert retrieved.demographics.age == 66
    
    def test_delete_patient(self, test_db, sample_patient):
        """Test deleting patient record."""
        dao = PatientDAO(test_db)
        
        # Create patient
        dao.create(sample_patient)
        
        # Delete patient
        result = dao.delete(sample_patient.patient_id)
        assert result is True
        
        # Verify deletion
        retrieved = dao.get_by_id(sample_patient.patient_id)
        assert retrieved is None
    
    def test_delete_nonexistent_patient(self, test_db):
        """Test deleting non-existent patient returns False."""
        dao = PatientDAO(test_db)
        
        result = dao.delete("NONEXISTENT")
        assert result is False
    
    def test_get_all_patients(self, test_db, sample_patient):
        """Test retrieving all patients."""
        dao = PatientDAO(test_db)
        
        # Create multiple patients
        patient1 = sample_patient
        dao.create(patient1)
        
        patient2 = sample_patient
        patient2.patient_id = "TEST-002"
        dao.create(patient2)
        
        # Retrieve all
        patients = dao.get_all()
        
        assert len(patients) == 2
        assert any(p.patient_id == "TEST-001" for p in patients)
        assert any(p.patient_id == "TEST-002" for p in patients)
    
    def test_address_encryption(self, test_db, sample_patient):
        """Test that sensitive address fields are encrypted."""
        dao = PatientDAO(test_db)
        
        # Create patient
        db_patient = dao.create(sample_patient)
        
        # Address fields should be encrypted in database
        assert db_patient.address_street != sample_patient.demographics.address.street
        assert db_patient.address_city != sample_patient.demographics.address.city
        
        # But should decrypt correctly when retrieved
        retrieved = dao.get_by_id(sample_patient.patient_id)
        assert retrieved.demographics.address.street == sample_patient.demographics.address.street
        assert retrieved.demographics.address.city == sample_patient.demographics.address.city


class TestPredictionDAO:
    """Test PredictionDAO operations."""
    
    def test_create_prediction(self, test_db, sample_patient):
        """Test creating a prediction record."""
        # First create patient
        patient_dao = PatientDAO(test_db)
        patient_dao.create(sample_patient)
        
        # Create prediction
        prediction = PredictionResult(
            patient_id=sample_patient.patient_id,
            risk_score=0.72,
            risk_tier=RiskTier.HIGH,
            prediction_date=datetime.utcnow(),
            model_version="v1.0.0",
            processing_time_ms=450
        )
        
        prediction_dao = PredictionDAO(test_db)
        db_prediction = prediction_dao.create(prediction)
        
        assert db_prediction.id is not None
        assert db_prediction.patient_id == sample_patient.patient_id
        assert db_prediction.risk_score == 0.72
        assert db_prediction.risk_tier == "high"
    
    def test_get_predictions_by_patient(self, test_db, sample_patient):
        """Test retrieving predictions for a patient."""
        # Create patient
        patient_dao = PatientDAO(test_db)
        patient_dao.create(sample_patient)
        
        # Create multiple predictions
        prediction_dao = PredictionDAO(test_db)
        
        for i in range(3):
            prediction = PredictionResult(
                patient_id=sample_patient.patient_id,
                risk_score=0.7 + i * 0.05,
                risk_tier=RiskTier.HIGH,
                prediction_date=datetime.utcnow(),
                model_version="v1.0.0",
                processing_time_ms=450
            )
            prediction_dao.create(prediction)
        
        # Retrieve predictions
        predictions = prediction_dao.get_by_patient(sample_patient.patient_id)
        
        assert len(predictions) == 3
    
    def test_get_latest_prediction(self, test_db, sample_patient):
        """Test retrieving latest prediction for a patient."""
        # Create patient
        patient_dao = PatientDAO(test_db)
        patient_dao.create(sample_patient)
        
        # Create predictions
        prediction_dao = PredictionDAO(test_db)
        
        prediction1 = PredictionResult(
            patient_id=sample_patient.patient_id,
            risk_score=0.70,
            risk_tier=RiskTier.HIGH,
            prediction_date=datetime(2023, 1, 1),
            model_version="v1.0.0",
            processing_time_ms=450
        )
        prediction_dao.create(prediction1)
        
        prediction2 = PredictionResult(
            patient_id=sample_patient.patient_id,
            risk_score=0.75,
            risk_tier=RiskTier.HIGH,
            prediction_date=datetime(2023, 6, 1),
            model_version="v1.0.0",
            processing_time_ms=450
        )
        prediction_dao.create(prediction2)
        
        # Get latest
        latest = prediction_dao.get_latest_by_patient(sample_patient.patient_id)
        
        assert latest is not None
        assert latest.risk_score == 0.75


class TestAuditLogDAO:
    """Test AuditLogDAO operations."""
    
    def test_create_audit_log(self, test_db):
        """Test creating audit log entry."""
        dao = AuditLogDAO(test_db)
        
        log = dao.create(
            user_id="user123",
            action="read",
            resource="patient_record",
            patient_id="TEST-001",
            data_elements=["demographics", "clinical"],
            ip_address="192.168.1.1",
            success=True
        )
        
        assert log.id is not None
        assert log.user_id == "user123"
        assert log.action == "read"
        assert log.patient_id == "TEST-001"
        assert log.success is True
    
    def test_get_audit_logs_by_patient(self, test_db):
        """Test retrieving audit logs for a patient."""
        dao = AuditLogDAO(test_db)
        
        # Create multiple logs
        for i in range(3):
            dao.create(
                user_id=f"user{i}",
                action="read",
                resource="patient_record",
                patient_id="TEST-001",
                success=True
            )
        
        # Retrieve logs
        logs = dao.get_by_patient("TEST-001")
        
        assert len(logs) == 3


class TestRiskTierChangeLogDAO:
    """Test RiskTierChangeLogDAO operations."""
    
    def test_create_tier_change_log(self, test_db, sample_patient):
        """Test logging risk tier change."""
        # Create patient
        patient_dao = PatientDAO(test_db)
        patient_dao.create(sample_patient)
        
        # Log tier change
        dao = RiskTierChangeLogDAO(test_db)
        log = dao.create(
            patient_id=sample_patient.patient_id,
            previous_tier=RiskTier.MODERATE,
            new_tier=RiskTier.HIGH,
            risk_score=0.72
        )
        
        assert log.id is not None
        assert log.patient_id == sample_patient.patient_id
        assert log.previous_tier == "moderate"
        assert log.new_tier == "high"
        assert log.risk_score == 0.72
    
    def test_get_tier_change_history(self, test_db, sample_patient):
        """Test retrieving tier change history."""
        # Create patient
        patient_dao = PatientDAO(test_db)
        patient_dao.create(sample_patient)
        
        # Create multiple tier changes
        dao = RiskTierChangeLogDAO(test_db)
        
        dao.create(
            patient_id=sample_patient.patient_id,
            previous_tier=RiskTier.LOW,
            new_tier=RiskTier.MODERATE,
            risk_score=0.45
        )
        
        dao.create(
            patient_id=sample_patient.patient_id,
            previous_tier=RiskTier.MODERATE,
            new_tier=RiskTier.HIGH,
            risk_score=0.72
        )
        
        # Retrieve history
        history = dao.get_by_patient(sample_patient.patient_id)
        
        assert len(history) == 2
        # Should be ordered by timestamp descending
        assert history[0].new_tier == "high"
        assert history[1].new_tier == "moderate"
