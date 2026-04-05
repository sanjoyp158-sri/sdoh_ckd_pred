# Starting the Backend API Server

The frontend needs the backend API to be running to fetch patient data.

## Quick Start

### Option 1: Start Backend in Terminal

Open a new terminal and run:

```bash
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The backend will start at: http://localhost:8000

### Option 2: Using Python directly

```bash
cd backend
python app/main.py
```

## Verify Backend is Running

Open http://localhost:8000 in your browser. You should see:

```json
{
  "name": "SDOH-CKDPred",
  "version": "0.1.0",
  "status": "running"
}
```

## Then Start Frontend

In another terminal:

```bash
cd frontend
npm run dev
```

Frontend will be at: http://localhost:3000

## Mock Data

The backend includes mock patient data, so you don't need a database:
- 3 sample patients with different risk tiers
- Mock authentication (any username/password works)
- Full SHAP explanations and patient details

## API Endpoints

- `GET /` - Root endpoint
- `GET /health` - Health check
- `POST /api/v1/auth/login` - Login (mock)
- `GET /api/v1/patients` - Get patient list
- `GET /api/v1/patients/{id}` - Get patient details
- `POST /api/v1/acknowledgments` - Acknowledge patient

## Troubleshooting

If you see "Error loading patients":
1. Make sure backend is running on port 8000
2. Check backend terminal for errors
3. Verify frontend is configured to use http://localhost:8000
