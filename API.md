# API Documentation

Complete API reference for the CKD Early Detection System.

## Base URL

- **Development**: `http://localhost:8000`
- **Production**: `https://your-domain.com`

## Authentication

The API uses JWT (JSON Web Token) authentication.

### Get Access Token

```http
POST /api/v1/auth/token
Content-Type: application/x-www-form-urlencoded

username=your_username&password=your_password
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### Using the Token

Include the token in the Authorization header:

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## Endpoints

### Health Check

#### GET /health

Check system health status.

**Authentication:** Not required

**Response:**
```json
{
  "status": "healthy"
}
```

### Root

#### GET /

Get API information.

**Authentication:** Not required

**Response:**
```json
{
  "name": "SDOH-CKDPred",
  "version": "0.1.0",
  "status": "running"
}
```

## Predictions

### Generate Prediction

#### POST /api/v1/predictions/predict

Generate CKD progression prediction for a patient.

**Authentication:** Required

**Request Body:**
```json
{
  "patient_id": "string",
  "demographics": {
    "age": 65,
    "sex": "M"
  },
  "clinical": {
    "egfr": 45.0,
    "uacr": 150.0,
    "hba1c": 7.5,
    "systolic_bp": 140,
    "diastolic_bp": 90,
    "bmi": 28.5,
    "medications": ["ACE_inhibitor", "Metformin"],
    "ckd_stage": "3a",
    "comorbidities": ["diabetes", "hypertension"]
  },
  "administrative": {
    "visit_frequency_12mo": 8,
    "insurance_type": "Medicare",
    "insurance_status": "Active"
  },
  "sdoh": {
    "adi_percentile": 75,
    "food_desert": true,
    "housing_stability_score": 0.6,
    "transportation_access_score": 0.4,
    "rural_urban_code": "rural"
  }
}
```

**Response:**
```json
{
  "patient_id": "string",
  "risk_score": 0.72,
  "risk_tier": "high",
  "prediction_date": "2024-01-15T10:30:00Z",
  "model_version": "1.0.0",
  "processing_time_ms": 245,
  "shap_explanation": {
    "baseline_risk": 0.35,
    "prediction": 0.72,
    "top_factors": [
      {
        "feature_name": "egfr",
        "feature_value": 45.0,
        "shap_value": 0.15,
        "category": "clinical",
        "direction": "increases_risk"
      },
      {
        "feature_name": "adi_percentile",
        "feature_value": 75,
        "shap_value": 0.12,
        "category": "sdoh",
        "direction": "increases_risk"
      },
      {
        "feature_name": "uacr",
        "feature_value": 150.0,
        "shap_value": 0.08,
        "category": "clinical",
        "direction": "increases_risk"
      },
      {
        "feature_name": "food_desert",
        "feature_value": true,
        "shap_value": 0.05,
        "category": "sdoh",
        "direction": "increases_risk"
      },
      {
        "feature_name": "hba1c",
        "feature_value": 7.5,
        "shap_value": 0.04,
        "category": "clinical",
        "direction": "increases_risk"
      }
    ],
    "computation_time_ms": 180
  },
  "intervention_workflow": {
    "workflow_id": "wf-12345",
    "initiated": true,
    "initiated_at": "2024-01-15T10:30:05Z"
  }
}
```

**Performance:**
- Prediction: < 500ms (Requirement 2.4)
- SHAP Explanation: < 200ms (Requirement 3.5)

### Get Prediction History

#### GET /api/v1/predictions/{patient_id}

Get prediction history for a patient.

**Authentication:** Required

**Parameters:**
- `patient_id` (path): Patient identifier

**Query Parameters:**
- `limit` (optional): Number of predictions to return (default: 10)
- `offset` (optional): Pagination offset (default: 0)

**Response:**
```json
{
  "patient_id": "string",
  "predictions": [
    {
      "risk_score": 0.72,
      "risk_tier": "high",
      "prediction_date": "2024-01-15T10:30:00Z",
      "model_version": "1.0.0"
    }
  ],
  "total": 1
}
```

### Get SHAP Explanation

#### GET /api/v1/predictions/{patient_id}/explanation

Get detailed SHAP explanation for the latest prediction.

**Authentication:** Required

**Parameters:**
- `patient_id` (path): Patient identifier

**Response:**
```json
{
  "patient_id": "string",
  "baseline_risk": 0.35,
  "prediction": 0.72,
  "shap_values": {
    "egfr": 0.15,
    "adi_percentile": 0.12,
    "uacr": 0.08,
    "food_desert": 0.05,
    "hba1c": 0.04,
    "...": "..."
  },
  "top_factors": [...],
  "categorized_factors": {
    "clinical": [...],
    "administrative": [...],
    "sdoh": [...]
  }
}
```

## Dashboard

### List All Patients

#### GET /api/v1/dashboard/patients

Get list of all patients with risk scores.

**Authentication:** Required

**Query Parameters:**
- `risk_tier` (optional): Filter by risk tier (high, moderate, low)
- `ckd_stage` (optional): Filter by CKD stage (2, 3a, 3b)
- `date_from` (optional): Filter predictions from date (ISO 8601)
- `date_to` (optional): Filter predictions to date (ISO 8601)
- `limit` (optional): Number of results (default: 50)
- `offset` (optional): Pagination offset (default: 0)

**Response:**
```json
{
  "patients": [
    {
      "patient_id": "string",
      "risk_score": 0.72,
      "risk_tier": "high",
      "prediction_date": "2024-01-15T10:30:00Z",
      "ckd_stage": "3a",
      "age": 65,
      "acknowledged": false
    }
  ],
  "total": 100,
  "filters": {
    "risk_tier": "high",
    "ckd_stage": null,
    "date_from": null,
    "date_to": null
  }
}
```

### Get Patient Details

#### GET /api/v1/dashboard/patients/{patient_id}

Get detailed patient information with SHAP explanations.

**Authentication:** Required

**Parameters:**
- `patient_id` (path): Patient identifier

**Response:**
```json
{
  "patient_id": "string",
  "demographics": {...},
  "clinical": {...},
  "administrative": {...},
  "sdoh": {...},
  "prediction": {
    "risk_score": 0.72,
    "risk_tier": "high",
    "prediction_date": "2024-01-15T10:30:00Z"
  },
  "shap_explanation": {...},
  "intervention_status": {
    "workflow_id": "wf-12345",
    "status": "in_progress",
    "steps": [...]
  }
}
```

### List High-Risk Patients

#### GET /api/v1/dashboard/high-risk

Get list of high-risk patients requiring intervention.

**Authentication:** Required

**Query Parameters:**
- `acknowledged` (optional): Filter by acknowledgment status (true/false)
- `limit` (optional): Number of results (default: 50)
- `offset` (optional): Pagination offset (default: 0)

**Response:**
```json
{
  "patients": [
    {
      "patient_id": "string",
      "risk_score": 0.72,
      "prediction_date": "2024-01-15T10:30:00Z",
      "top_risk_factors": [...],
      "intervention_status": "in_progress",
      "acknowledged": false,
      "acknowledged_by": null,
      "acknowledged_at": null
    }
  ],
  "total": 25
}
```

### Acknowledge High-Risk Alert

#### POST /api/v1/dashboard/acknowledge/{patient_id}

Record provider acknowledgment of high-risk alert.

**Authentication:** Required

**Parameters:**
- `patient_id` (path): Patient identifier

**Request Body:**
```json
{
  "provider_id": "string",
  "notes": "string (optional)"
}
```

**Response:**
```json
{
  "patient_id": "string",
  "acknowledged": true,
  "acknowledged_by": "provider-123",
  "acknowledged_at": "2024-01-15T11:00:00Z"
}
```

## Error Responses

### 400 Bad Request

```json
{
  "detail": "Invalid request data",
  "errors": [
    {
      "field": "clinical.egfr",
      "message": "eGFR must be between 0 and 200"
    }
  ]
}
```

### 401 Unauthorized

```json
{
  "detail": "Not authenticated"
}
```

### 403 Forbidden

```json
{
  "detail": "Not enough permissions"
}
```

### 404 Not Found

```json
{
  "detail": "Patient not found"
}
```

### 422 Validation Error

```json
{
  "detail": [
    {
      "loc": ["body", "clinical", "egfr"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### 500 Internal Server Error

```json
{
  "detail": "Internal server error",
  "error_id": "err-12345"
}
```

## Rate Limiting

- **Rate Limit**: 100 requests per minute per user
- **Headers**:
  - `X-RateLimit-Limit`: Maximum requests per window
  - `X-RateLimit-Remaining`: Remaining requests in current window
  - `X-RateLimit-Reset`: Time when the rate limit resets (Unix timestamp)

## Data Models

### Risk Tiers

- **high**: risk_score > 0.65 (triggers intervention workflow)
- **moderate**: 0.35 ≤ risk_score ≤ 0.65 (monitoring)
- **low**: risk_score < 0.35 (routine care)

### CKD Stages

- **2**: eGFR 60-89 mL/min/1.73m²
- **3a**: eGFR 45-59 mL/min/1.73m²
- **3b**: eGFR 30-44 mL/min/1.73m²

### Insurance Types

- Medicare
- Medicaid
- Commercial
- Uninsured

### Medication Categories

- ACE_inhibitor
- ARB
- Diuretic
- Beta_blocker
- Calcium_channel_blocker
- Statin
- Metformin
- Insulin
- SGLT2_inhibitor

## Performance Metrics

Expected response times:

- **Prediction**: < 500ms (Requirement 2.4)
- **SHAP Explanation**: < 200ms (Requirement 3.5)
- **Dashboard Queries**: < 100ms
- **Authentication**: < 50ms

## Security

### HTTPS/TLS

All production endpoints use HTTPS with TLS 1.3 (Requirement 13.2).

### Data Encryption

- **At Rest**: AES-256 encryption (Requirement 13.1)
- **In Transit**: TLS 1.3 with strong cipher suites

### Audit Logging

All API requests are logged with:
- User ID
- Timestamp
- Endpoint accessed
- Request parameters
- Response status

## Interactive Documentation

When the server is running, visit:

- **Swagger UI**: `https://your-domain.com/docs`
- **ReDoc**: `https://your-domain.com/redoc`
- **OpenAPI Schema**: `https://your-domain.com/openapi.json`

## Code Examples

### Python

```python
import requests

# Authenticate
response = requests.post(
    "https://your-domain.com/api/v1/auth/token",
    data={"username": "user", "password": "pass"}
)
token = response.json()["access_token"]

# Make prediction
headers = {"Authorization": f"Bearer {token}"}
patient_data = {
    "patient_id": "test-001",
    "clinical": {"egfr": 45.0, "uacr": 150.0, "hba1c": 7.5},
    # ... other fields
}
response = requests.post(
    "https://your-domain.com/api/v1/predictions/predict",
    headers=headers,
    json=patient_data
)
prediction = response.json()
print(f"Risk Score: {prediction['risk_score']}")
```

### cURL

```bash
# Authenticate
TOKEN=$(curl -X POST "https://your-domain.com/api/v1/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user&password=pass" | jq -r '.access_token')

# Make prediction
curl -X POST "https://your-domain.com/api/v1/predictions/predict" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @patient_data.json
```

### JavaScript

```javascript
// Authenticate
const authResponse = await fetch('https://your-domain.com/api/v1/auth/token', {
  method: 'POST',
  headers: {'Content-Type': 'application/x-www-form-urlencoded'},
  body: 'username=user&password=pass'
});
const { access_token } = await authResponse.json();

// Make prediction
const predictionResponse = await fetch('https://your-domain.com/api/v1/predictions/predict', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${access_token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(patientData)
});
const prediction = await predictionResponse.json();
console.log('Risk Score:', prediction.risk_score);
```

## Support

For API support:
- GitHub Issues: https://github.com/sanjoyp158-sri/sdoh_ckd_pred/issues
- Documentation: See README.md and DEPLOYMENT.md
