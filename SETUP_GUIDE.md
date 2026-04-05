# 🚀 CKD Early Detection System - Setup Guide

Complete setup instructions for external reviewers and developers.

## 📋 Prerequisites

- **Python 3.8+** (for backend)
- **Node.js 16+** and npm (for frontend)
- **Git** (to clone the repository)

## 🔧 Quick Setup (5 minutes)

### Step 1: Clone the Repository

```bash
git clone https://github.com/sanjoyp158-sri/sdoh_ckd_pred.git
cd sdoh_ckd_pred
```

### Step 2: Set Up Python Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### Step 3: Install Backend Dependencies

```bash
cd backend
pip install -r requirements.txt
cd ..
```

### Step 4: Install Frontend Dependencies

```bash
cd frontend
npm install
cd ..
```

## ▶️ Running the Application

You need **TWO terminals** running simultaneously:

### Terminal 1: Start Backend Server

```bash
cd backend
../.venv/bin/python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Expected output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Application startup complete.
```

**Verify backend is running:**
```bash
curl http://localhost:8000/health
# Should return: {"status":"healthy"}
```

### Terminal 2: Start Frontend Server

```bash
cd frontend
npm run dev
```

**Expected output:**
```
VITE v5.0.7  ready in XXX ms
➜  Local:   http://localhost:3000/
```

## 🌐 Access the Application

1. Open your browser to: **http://localhost:3000**
2. **Login with ANY credentials** (demo mode enabled):
   - Username: `admin` (or any text)
   - Password: `admin` (or any text)
3. You'll see the Patient Risk Dashboard with 3 mock patients

## 📊 What You'll See

### Patient List Dashboard
- **3 mock patients** with different risk levels
- **Filters**: Risk tier, CKD stage, date range
- **Sortable columns**: Click headers to sort
- **Color-coded risk badges**:
  - 🔴 Red = High Risk (>65%)
  - 🟡 Yellow = Moderate Risk (35-65%)
  - 🟢 Green = Low Risk (<35%)

### Patient Detail View (Click any patient)
- **Risk Assessment**: Score, tier, prediction date
- **Demographics**: Age, sex
- **Clinical Indicators**: eGFR, UACR, HbA1c, BP, BMI, CKD stage
- **Administrative Metrics**: Visit frequency, insurance, referrals
- **SDOH Indicators**: ADI percentile, food desert, housing, transportation
- **SHAP Analysis Chart**: Top 6 risk factors with color-coded categories:
  - 🔵 Blue = Clinical factors
  - 🟣 Purple = Administrative factors
  - 🌸 Pink = SDOH factors
- **Acknowledge Button**: Mark patient as reviewed

## 🧪 Mock Data Included

The system includes 3 sample patients (no database required):

| Patient ID | Risk Score | Risk Tier | Age | Sex | CKD Stage | eGFR |
|------------|------------|-----------|-----|-----|-----------|------|
| patient-001 | 72% | High | 68 | F | 3a | 28.5 |
| patient-002 | 45% | Moderate | 55 | M | 2 | 65.2 |
| patient-003 | 82% | High | 72 | M | 3b | 22.1 |

## 🔍 Testing Features

### 1. Test Filtering
- Select "High Risk" from Risk Tier dropdown → Should show 2 patients
- Select "Stage 3a" from CKD Stage → Should show 1 patient
- Clear filters to see all patients again

### 2. Test Sorting
- Click "Risk Score" column header → Patients sort by risk
- Click again → Reverse sort order

### 3. Test Patient Detail
- Click on any patient row
- Verify all sections load (demographics, clinical, SDOH, SHAP chart)
- Check SHAP chart shows 6 factors in 3 colors

### 4. Test Acknowledgment
- Click "Acknowledge Review" button on a patient
- Status should change to "✓ Acknowledged"
- Return to patient list → Status shows "Acknowledged"

## 🛠️ Troubleshooting

### "Error loading patients" after login
**Cause**: Backend isn't running or not accessible

**Solution**:
1. Check backend terminal for errors
2. Verify backend is running: `curl http://localhost:8000/health`
3. Restart backend if needed

### "Invalid credentials" error
**Cause**: Backend not running (frontend can't reach login API)

**Solution**: Start the backend server first

### Blank screen after login
**Cause**: Frontend/backend API mismatch (should be fixed in latest code)

**Solution**: 
1. Pull latest code: `git pull origin main`
2. Restart both servers

### Port already in use
**Solution**:
```bash
# Kill process on port 8000 (backend)
lsof -ti:8000 | xargs kill -9

# Kill process on port 3000 (frontend)
lsof -ti:3000 | xargs kill -9
```

### Backend dependencies fail to install
**Solution**:
```bash
# Upgrade pip first
pip install --upgrade pip

# Try installing again
pip install -r backend/requirements.txt
```

### Frontend dependencies fail to install
**Solution**:
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

## 📁 Project Structure

```
sdoh_ckd_pred/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/            # API endpoints (auth, dashboard, predictions)
│   │   ├── core/           # Config, security, audit logging
│   │   ├── db/             # Database models and DAOs
│   │   ├── ml/             # ML models and analytics
│   │   ├── models/         # Pydantic models
│   │   └── services/       # Business logic services
│   ├── tests/              # Comprehensive test suite
│   └── requirements.txt    # Python dependencies
├── frontend/               # React + TypeScript frontend
│   ├── src/
│   │   ├── components/     # Reusable UI components
│   │   ├── pages/          # Page components
│   │   ├── services/       # API client services
│   │   ├── stores/         # State management (Zustand)
│   │   └── types/          # TypeScript type definitions
│   └── package.json        # Node dependencies
├── docker-compose.yml      # Docker deployment config
├── README.md              # Project overview
└── SETUP_GUIDE.md         # This file
```

## 🧪 Running Tests

### Backend Tests
```bash
cd backend
pytest
```

### Frontend Tests (if configured)
```bash
cd frontend
npm test
```

## 🐳 Docker Deployment (Optional)

For production deployment:

```bash
docker-compose up -d
```

This starts:
- Backend on port 8000
- Frontend on port 3000
- PostgreSQL database
- Redis cache

## 📚 Additional Documentation

- **README.md** - Project overview and architecture
- **API.md** - API endpoint documentation
- **DEPLOYMENT.md** - Production deployment guide
- **SIMPLE_START.md** - Quick start commands
- **LOGIN_CREDENTIALS.md** - Authentication details

## ✅ Verification Checklist

Use this checklist to verify the system is working:

- [ ] Backend starts without errors
- [ ] Frontend starts without errors
- [ ] Can access http://localhost:3000
- [ ] Can login with any credentials
- [ ] Patient list shows 3 patients
- [ ] Can filter by risk tier
- [ ] Can sort by clicking column headers
- [ ] Can click patient row to see details
- [ ] Patient detail page loads completely
- [ ] SHAP chart shows 6 factors in 3 colors
- [ ] Can acknowledge a patient
- [ ] Acknowledgment status persists

## 🆘 Support

If you encounter issues:

1. Check the troubleshooting section above
2. Review the terminal output for error messages
3. Ensure you're using the latest code: `git pull origin main`
4. Check that all prerequisites are installed

## 🎉 Success!

If you can see the patient dashboard and click through to patient details with the SHAP chart, the system is working correctly!

---

**Repository**: https://github.com/sanjoyp158-sri/sdoh_ckd_pred.git

**Last Updated**: April 5, 2026
