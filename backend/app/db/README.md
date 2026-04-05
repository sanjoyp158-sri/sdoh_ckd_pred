# Database Persistence Layer

This directory contains the database persistence layer for the CKD Early Detection System, implementing PostgreSQL storage with AES-256 encryption at rest.

## Components

### 1. Database Configuration (`database.py`)
- SQLAlchemy engine and session management
- Connection pooling configuration
- Database initialization utilities

### 2. Encryption Service (`encryption.py`)
- AES-256-GCM encryption for data at rest
- Authenticated encryption with unique nonces per operation
- Key generation and password-based key derivation utilities

### 3. ORM Models (`models.py`)
- SQLAlchemy models for all database tables:
  - `PatientModel`: Unified patient records with encrypted sensitive fields
  - `PredictionModel`: ML prediction results and SHAP explanations
  - `RiskTierChangeLogModel`: Risk tier change history
  - `AuditLogModel`: HIPAA-compliant audit logging
  - `InterventionWorkflowModel`: Intervention workflow tracking
  - `CaseManagerModel`: Case manager information
  - `CaseRecordModel`: Case management records

### 4. Data Access Objects (`dao.py`)
- High-level CRUD operations with automatic encryption/decryption:
  - `PatientDAO`: Patient record operations
  - `PredictionDAO`: Prediction record operations
  - `AuditLogDAO`: Audit log operations
  - `RiskTierChangeLogDAO`: Risk tier change logging

## Security Features

### Encryption at Rest (AES-256)
All sensitive patient data is encrypted using AES-256-GCM:
- **Address fields**: Street and city are encrypted
- **Unique nonces**: Each encryption uses a random 96-bit nonce
- **Authenticated encryption**: GCM mode provides both confidentiality and authenticity
- **Automatic handling**: DAOs handle encryption/decryption transparently

### Key Management
```bash
# Generate a new encryption key
python3 -c "from app.db.encryption import generate_encryption_key; print(generate_encryption_key())"

# Set the key as environment variable
export ENCRYPTION_KEY="<generated-key>"
```

**Important**: Store the encryption key securely (e.g., AWS Secrets Manager, HashiCorp Vault). Never commit keys to version control.

## Database Schema

### Patients Table
Stores unified patient records with clinical, administrative, and SDOH data.

**Encrypted Fields**:
- `address_street`
- `address_city`

**Indexes**:
- `patient_id` (unique)
- `ckd_stage`
- `created_at`
- `address_zip_code`

### Predictions Table
Stores ML model predictions and SHAP explanations.

**Indexes**:
- `patient_id`
- `risk_tier`
- `prediction_date`
- Composite: `(patient_id, prediction_date)`

### Risk Tier Changes Table
Tracks changes in patient risk tier assignments.

**Indexes**:
- `patient_id`
- `change_timestamp`
- Composite: `(patient_id, change_timestamp)`

### Audit Logs Table
HIPAA-compliant audit logging for all data access.

**Indexes**:
- `user_id`
- `patient_id`
- `timestamp`
- `action`
- Composite: `(user_id, timestamp)`, `(patient_id, timestamp)`

## Usage Examples

### Initialize Database
```python
from app.db import init_db

# Create all tables
init_db()
```

### Patient CRUD Operations
```python
from app.db import get_db, PatientDAO
from app.models.patient import UnifiedPatientRecord

# Get database session
db = next(get_db())

# Create DAO
patient_dao = PatientDAO(db)

# Create patient
patient = UnifiedPatientRecord(...)
db_patient = patient_dao.create(patient)

# Retrieve patient (automatic decryption)
patient = patient_dao.get_by_id("PATIENT-001")

# Update patient
patient.clinical.egfr = 40.0
patient_dao.update(patient)

# Delete patient
patient_dao.delete("PATIENT-001")
```

### Prediction Operations
```python
from app.db import PredictionDAO
from app.models.patient import PredictionResult, RiskTier

prediction_dao = PredictionDAO(db)

# Create prediction
prediction = PredictionResult(
    patient_id="PATIENT-001",
    risk_score=0.72,
    risk_tier=RiskTier.HIGH,
    prediction_date=datetime.utcnow(),
    model_version="v1.0.0",
    processing_time_ms=450
)
prediction_dao.create(prediction)

# Get latest prediction
latest = prediction_dao.get_latest_by_patient("PATIENT-001")

# Get all predictions for patient
predictions = prediction_dao.get_by_patient("PATIENT-001", limit=10)
```

### Audit Logging
```python
from app.db import AuditLogDAO

audit_dao = AuditLogDAO(db)

# Log data access
audit_dao.create(
    user_id="provider123",
    action="read",
    resource="patient_record",
    patient_id="PATIENT-001",
    data_elements=["demographics", "clinical"],
    ip_address="192.168.1.1",
    success=True
)

# Query audit logs
logs = audit_dao.get_by_patient("PATIENT-001")
user_logs = audit_dao.get_by_user("provider123")
```

### Risk Tier Change Logging
```python
from app.db import RiskTierChangeLogDAO
from app.models.patient import RiskTier

tier_log_dao = RiskTierChangeLogDAO(db)

# Log tier change
tier_log_dao.create(
    patient_id="PATIENT-001",
    previous_tier=RiskTier.MODERATE,
    new_tier=RiskTier.HIGH,
    risk_score=0.72
)

# Get change history
history = tier_log_dao.get_by_patient("PATIENT-001")
```

## Environment Variables

Required environment variables:

```bash
# Database connection
DATABASE_URL="postgresql://user:password@localhost:5432/ckd_prediction"

# Encryption key (256-bit, base64-encoded)
ENCRYPTION_KEY="<base64-encoded-key>"
```

## Database Initialization

### Using Python Script
```bash
cd backend
python3 app/db/init_db.py
```

### Using Alembic Migrations (Recommended for Production)
```bash
# Initialize Alembic
alembic init alembic

# Create migration
alembic revision --autogenerate -m "Initial schema"

# Apply migration
alembic upgrade head
```

## Testing

Run database tests:
```bash
cd backend
python3 -m pytest tests/unit/test_database_persistence.py -v
```

Tests cover:
- Encryption/decryption functionality
- CRUD operations for all DAOs
- Automatic encryption of sensitive fields
- Data integrity and retrieval accuracy

## Performance Considerations

### Connection Pooling
- Pool size: 10 connections
- Max overflow: 20 connections
- Pre-ping enabled for connection health checks

### Indexes
All tables have appropriate indexes for common query patterns:
- Primary key indexes on all tables
- Foreign key indexes for relationships
- Composite indexes for common filter combinations
- Timestamp indexes for temporal queries

### Query Optimization
- Use `limit` and `skip` parameters for pagination
- Filter by indexed columns when possible
- Use `get_latest_by_patient()` instead of fetching all predictions

## Compliance

### HIPAA Requirements
✅ **Encryption at Rest**: AES-256-GCM encryption for sensitive data  
✅ **Audit Logging**: All data access logged with user, timestamp, and data elements  
✅ **Access Control**: Role-based access control (implemented at API layer)  
✅ **Data Integrity**: Authenticated encryption prevents tampering  

### Data Retention
- Patient records: Retained per organizational policy
- Predictions: Retained for model monitoring and validation
- Audit logs: Retained for 7 years (HIPAA requirement)
- Risk tier changes: Retained indefinitely for historical analysis

## Troubleshooting

### Connection Issues
```python
# Test database connection
from app.db import engine
with engine.connect() as conn:
    result = conn.execute("SELECT 1")
    print("Database connection successful!")
```

### Encryption Key Issues
```python
# Verify encryption key is set
import os
key = os.getenv("ENCRYPTION_KEY")
if not key:
    print("ERROR: ENCRYPTION_KEY not set")
else:
    print(f"Encryption key configured (length: {len(key)} chars)")
```

### Migration Issues
```bash
# Reset database (WARNING: destroys all data)
python3 -c "from app.db import Base, engine; Base.metadata.drop_all(engine); Base.metadata.create_all(engine)"
```

## Future Enhancements

- [ ] Implement database connection retry logic
- [ ] Add read replicas for query scaling
- [ ] Implement database backup automation
- [ ] Add encryption key rotation support
- [ ] Implement soft deletes for patient records
- [ ] Add full-text search for patient records
- [ ] Implement database sharding for horizontal scaling
