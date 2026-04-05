# 🚀 Start the Frontend Dashboard

## ⚠️ IMPORTANT: You Need Both Backend and Frontend Running

The frontend requires the backend API to fetch patient data. Follow these steps:

## Option 1: Start Both Servers Automatically (Recommended)

Run the startup script from the project root:

```bash
./start_dev.sh
```

This will start both backend (port 8000) and frontend (port 3000) automatically.

## Option 2: Start Manually (Two Terminals)

### Terminal 1 - Start Backend First ⚡

```bash
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Wait until you see: `Application startup complete.`

### Terminal 2 - Start Frontend 🎨

```bash
cd frontend
npm run dev
```

## Access the Application 🌐

Once both servers are running:

1. Open your browser to: **http://localhost:3000**
2. Login with any credentials (e.g., `admin` / `admin`)
3. You should see the patient list with 3 mock patients

## Verify Backend is Running ✅

Before starting the frontend, verify the backend is working:

```bash
curl http://localhost:8000/health
```

Should return: `{"status":"healthy"}`

## What You'll See

### 1. 🔐 Login Page
- Beautiful purple gradient background
- Clean, modern login form
- Enter any username/password (mock auth enabled)
- Click "Sign In"

### 2. 📊 Patient Dashboard
After login, you'll see:

**Patient List View:**
- Table with 3 mock patients
- **Color-coded risk badges:**
  - 🔴 **RED** = High Risk (>65%)
  - 🟡 **YELLOW** = Moderate Risk (35-65%)
  - 🟢 **GREEN** = Low Risk (<35%)
- **Filters:**
  - Risk Tier dropdown
  - CKD Stage dropdown
  - Date range pickers
- **Sortable columns:**
  - Click column headers to sort
  - Patient ID, Risk Score, eGFR, Prediction Date

**Click any patient row to see details →**

### 3. 👤 Patient Detail View
Comprehensive patient information:

**Risk Assessment Card:**
- Large circular risk score gauge
- Color-coded risk tier badge
- Acknowledge Review button

**SHAP Analysis Chart:**
- Horizontal bar chart showing top 5 risk factors
- Color-coded by category:
  - 🔵 Blue = Clinical factors
  - 🟣 Purple = Administrative factors
  - 🌸 Pink = SDOH factors

**Clinical Indicators:**
- eGFR (kidney function)
- UACR (kidney damage marker)
- HbA1c (diabetes control)
- Blood Pressure
- BMI

**Administrative Metrics:**
- Visit frequency (last 12 months)
- Insurance type

**SDOH Indicators:**
- ADI Percentile (neighborhood disadvantage)
- Food Desert status
- Housing Stability score
- Transportation Access score

## Mock Data Included 📦

The backend includes 3 sample patients:
- **Patient 001**: High risk (72%), Stage 3a, Female, 68 years
- **Patient 002**: Moderate risk (45%), Stage 2, Male, 55 years  
- **Patient 003**: High risk (82%), Stage 3b, Male, 72 years

## Troubleshooting 🔧

**"Error loading patients"** means the backend isn't running:
1. Check if backend is running: `curl http://localhost:8000/health`
2. Start backend first, then frontend
3. Check backend terminal for errors
4. Make sure you're using the updated `vite.config.ts` (proxy to localhost:8000)

**Port already in use:**
- Backend (8000): `lsof -ti:8000 | xargs kill -9`
- Frontend (3000): `lsof -ti:3000 | xargs kill -9`

**To stop the servers:**
- Press `Ctrl + C` in each terminal

Enjoy exploring the CKD Early Detection System dashboard! 🎉
