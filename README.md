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
- Node.js 18+
- Docker and Docker Compose
- PostgreSQL 15+
- Redis 7+

### Installation

1. Clone the repository:
```bash
git clone https://github.com/sanjoyp158-sri/sdoh_ckd_pred.git
cd sdoh_ckd_pred
```

2. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Start services with Docker:
```bash
docker-compose up -d
```

4. Access the application:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## Development

### Backend Development

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend Development

```bash
cd frontend
npm install
npm start
```

### Running Tests

```bash
# Backend tests
cd backend
pytest

# Property-based tests
pytest -m property_test

# Frontend tests
cd frontend
npm test
```

## Documentation

- [Requirements Document](.kiro/specs/ckd-early-detection-system/requirements.md)
- [Design Document](.kiro/specs/ckd-early-detection-system/design.md)
- [Implementation Tasks](.kiro/specs/ckd-early-detection-system/tasks.md)
- [API Documentation](http://localhost:8000/docs) (when running)

## Research Paper

This implementation is based on the research paper:
"AI-Enabled Early Detection of Chronic Kidney Disease in Underserved Communities Using Social Determinants of Health: Development and Pilot Simulation Study"

## License

[Add your license here]

## Citation

If you use this system, please cite the original research paper and the data sources (USRDS, CDC PLACES, ADI, USDA, Census ACS).

## Contact

[Add contact information]
