# SDOH-CKDPred: AI-Enabled Early Detection of CKD in Underserved Communities

An AI-enabled early detection system for Chronic Kidney Disease (CKD) that integrates clinical data with Social Determinants of Health (SDOH) to predict disease progression and trigger automated interventions.

## Overview

SDOH-CKDPred predicts CKD progression from Stage 2-3 to Stage 4-5 within 24 months using XGBoost with SHAP explainability. The system automatically triggers interventions for high-risk patients including telehealth consultations, home blood draws, and case management enrollment.

## Key Features

- **ML-Driven Predictions**: XGBoost classifier with AUROC ≥ 0.87
- **Explainable AI**: SHAP-based explanations for clinical trust
- **Risk Stratification**: Three-tier system (high >0.65, moderate 0.35-0.65, low <0.35)
- **Automated Interventions**: Telehealth scheduling, home blood draws, case management
- **Health Equity**: Fairness monitoring across racial/ethnic subgroups
- **Cost-Effectiveness**: Target BCR of 3.75:1
- **HIPAA Compliant**: Encryption at rest (AES-256) and in transit (TLS 1.3)
- **Production Ready**: Docker deployment with health checks and monitoring

## Architecture

The system follows a layered architecture with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────┐
│                    Nginx (TLS 1.3)                      │
│              Reverse Proxy & Load Balancer              │
└─────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────┐
│                  FastAPI Backend                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │   API Layer  │  │  ML Analytics │  │ Intervention │ │
│  │              │  │    Engine     │  │   Workflow   │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ Data Integ.  │  │     SHAP      │  │     Risk     │ │
│  │    Layer     │  │  Explainer    │  │ Stratifier   │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┴───────────────────┐
        │                                       │
┌───────────────┐                      ┌────────────────┐
│  PostgreSQL   │                      │     Redis      │
│  (Encrypted)  │                      │    (Cache)     │
└───────────────┘                      └────────────────┘
```

### Security Features

**Encryption at Rest (Requirement 13.1)**:
- AES-256 encryption for sensitive patient data in PostgreSQL
- Encrypted database volumes
- Secure key management via environment variables

**Encryption in Transit (Requirement 13.2)**:
- TLS 1.3 only (no fallback to older versions)
- Strong cipher suites (AES-GCM, ChaCha20-Poly1305)
- Perfect Forward Secrecy with 4096-bit DH parameters
- HSTS enabled with preload
- OCSP stapling for certificate validation

**Application Security**:
- JWT-based authentication
- Role-based access control (RBAC)
- Password hashing with bcrypt
- SQL injection prevention via SQLAlchemy ORM
- XSS protection headers
- CSRF protection
- Rate limiting
- Audit logging for all data access

**Container Security**:
- Non-root user in containers
- Minimal base images (Alpine Linux)
- No exposed database ports in production
- Health checks for all services
- Resource limits and restart policies

## Technology Stack

- **Backend**: Python 3.11+, FastAPI
- **Frontend**: React 18+, TypeScript
- **Database**: PostgreSQL 15+
- **Cache**: Redis 7+
- **ML**: XGBoost, SHAP, scikit-learn
- **Testing**: pytest, Hypothesis (property-based testing)
- **Deployment**: Docker, docker-compose

## Project Structure

```
sdoh_ckd_pred/
├── backend/                 # FastAPI backend application
│   ├── app/
│   │   ├── api/            # API endpoints
│   │   ├── core/           # Core configuration
│   │   ├── models/         # Data models
│   │   ├── services/       # Business logic
│   │   ├── ml/             # ML engine and SHAP
│   │   └── db/             # Database layer
│   ├── tests/              # Backend tests
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/               # React frontend application
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── pages/         # Page components
│   │   ├── services/      # API clients
│   │   └── utils/         # Utilities
│   ├── package.json
│   └── Dockerfile
├── ml_pipeline/           # Model training pipeline
│   ├── data/              # Training data
│   ├── models/            # Trained models
│   ├── scripts/           # Training scripts
│   └── notebooks/         # Jupyter notebooks
├── docker-compose.yml     # Docker orchestration
├── .env.example           # Environment variables template
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+ (for frontend, if applicable)
- Docker and Docker Compose
- PostgreSQL 15+ (if running without Docker)
- Redis 7+ (if running without Docker)

### Quick Start with Docker (Recommended)

1. Clone the repository:
```bash
git clone https://github.com/sanjoyp158-sri/sdoh_ckd_pred.git
cd sdoh_ckd_pred
```

2. Run the production setup script:
```bash
./scripts/setup-production.sh
```

This script will:
- Check prerequisites
- Generate secure encryption keys
- Create and configure `.env` file
- Set up SSL certificates (optional)
- Configure file permissions

3. Place your trained ML model:
```bash
# Copy your trained model to the models directory
cp /path/to/your/sdoh_ckdpred_final.json models/
```

4. Start the services:
```bash
# Development mode (with hot reload)
docker-compose up -d

# Production mode (with TLS 1.3 and security hardening)
docker-compose -f docker-compose.prod.yml up -d
```

5. Verify deployment:
```bash
# Check service health
docker-compose ps

# Test health endpoint
curl -k https://localhost/health

# View logs
docker-compose logs -f
```

6. Access the application:
- Backend API: https://localhost/api/v1
- API Documentation: https://localhost/docs
- Health Check: https://localhost/health

### Manual Setup (Without Docker)

If you prefer to run services manually:

1. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

2. Install backend dependencies:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Start PostgreSQL and Redis:
```bash
# Start PostgreSQL
sudo systemctl start postgresql

# Start Redis
sudo systemctl start redis
```

4. Run database migrations:
```bash
cd backend
alembic upgrade head
```

5. Start the backend:
```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### SSL/TLS Configuration

For production deployments with TLS 1.3 (Requirement 13.2):

```bash
# Generate SSL certificates
./scripts/generate-ssl-certs.sh

# Or use Let's Encrypt
sudo certbot certonly --standalone -d your-domain.com
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem nginx/ssl/cert.pem
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem nginx/ssl/key.pem
```

## Deployment

For comprehensive deployment instructions, including:
- Security configuration
- SSL/TLS setup with TLS 1.3
- Database encryption at rest (Requirement 13.1)
- Production best practices
- Monitoring and troubleshooting
- Backup and recovery

See **[DEPLOYMENT.md](DEPLOYMENT.md)** for the complete deployment guide.

## Documentation

- [Requirements Document](.kiro/specs/ckd-early-detection-system/requirements.md)
- [Design Document](.kiro/specs/ckd-early-detection-system/design.md)
- [Implementation Tasks](.kiro/specs/ckd-early-detection-system/tasks.md)
- [Deployment Guide](DEPLOYMENT.md) - **Comprehensive production deployment instructions**
- [API Documentation](http://localhost:8000/docs) (when running)

## API Endpoints

### Authentication
- `POST /api/v1/auth/login` - User authentication
- `POST /api/v1/auth/token` - Get access token

### Predictions
- `POST /api/v1/predictions/predict` - Generate CKD progression prediction
- `GET /api/v1/predictions/{patient_id}` - Get prediction history
- `GET /api/v1/predictions/{patient_id}/explanation` - Get SHAP explanation

### Dashboard
- `GET /api/v1/dashboard/patients` - List all patients with risk scores
- `GET /api/v1/dashboard/patients/{patient_id}` - Get patient details
- `GET /api/v1/dashboard/high-risk` - List high-risk patients
- `POST /api/v1/dashboard/acknowledge/{patient_id}` - Acknowledge high-risk alert

### Health & Monitoring
- `GET /health` - Health check endpoint
- `GET /` - API status and version

For detailed API documentation with request/response schemas, visit `/docs` when the server is running.

## Testing

### Backend Tests

```bash
cd backend

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test types
pytest tests/unit/              # Unit tests
pytest tests/integration/       # Integration tests
pytest tests/property/          # Property-based tests

# Run tests for specific components
pytest tests/unit/test_xgboost_classifier.py
pytest tests/property/test_properties_ml_analytics.py
```

### Property-Based Testing

The system uses Hypothesis for property-based testing to verify correctness properties:

```bash
# Run all property tests
pytest tests/property/ -v

# Run with more examples (thorough testing)
pytest tests/property/ --hypothesis-profile=thorough

# Run specific property test
pytest tests/property/test_properties_risk_stratification.py -v
```

### Testing Deployment

```bash
# Test Docker build
docker-compose build

# Test services start correctly
docker-compose up -d
docker-compose ps

# Test health endpoints
curl -k https://localhost/health

# Test prediction endpoint (requires auth token)
curl -k -X POST https://localhost/api/v1/predictions/predict \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-token>" \
  -d '{
    "patient_id": "test-001",
    "clinical": {
      "egfr": 45.0,
      "uacr": 150.0,
      "hba1c": 7.5
    }
  }'

# View logs
docker-compose logs -f backend
```

## Research Paper

This implementation is based on the research paper:
"AI-Enabled Early Detection of Chronic Kidney Disease in Underserved Communities Using Social Determinants of Health: Development and Pilot Simulation Study"

## License

[Add your license here]

## Citation

If you use this system, please cite the original research paper and the data sources (USRDS, CDC PLACES, ADI, USDA, Census ACS).

## Contact

[Add contact information]
