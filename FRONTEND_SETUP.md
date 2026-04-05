# Frontend Setup and Preview Guide

## Quick Start

### Option 1: Development Mode (Recommended for Preview)

1. **Install dependencies:**
```bash
cd frontend
npm install
```

2. **Start development server:**
```bash
npm run dev
```

3. **Open in browser:**
- The app will be available at: http://localhost:3000
- You'll see the login page first

### Option 2: Docker (Full Stack)

```bash
# From project root
docker-compose up
```

Then visit: http://localhost:3000

## What You'll See

### 1. Login Page
- Clean, modern login interface
- Purple gradient background
- Username/password fields
- "CKD Early Detection System" branding

### 2. Patient List Dashboard
- Filterable table with all patients
- Color-coded risk tiers:
  - 🔴 RED = High Risk (>0.65)
  - 🟡 YELLOW = Moderate Risk (0.35-0.65)
  - 🟢 GREEN = Low Risk (<0.35)
- Sortable columns (risk score, eGFR, date)
- Filter by: Risk Tier, CKD Stage, Date Range
- Search by Patient ID

### 3. Patient Detail View
- Risk score gauge with color coding
- SHAP waterfall chart showing top 5 risk factors
- Clinical indicators (eGFR, UACR, HbA1c, BP, BMI)
- Administrative metrics (visits, insurance)
- SDOH indicators (ADI, food desert, housing, transportation)
- eGFR trend timeline chart
- Provider acknowledgment button

## Features

✅ Responsive design
✅ Real-time data updates
✅ Interactive charts (Recharts)
✅ Color-coded risk visualization
✅ Filtering and sorting
✅ Provider acknowledgment tracking

## Tech Stack

- React 18 + TypeScript
- Vite (fast build tool)
- TanStack Query (data fetching)
- Zustand (state management)
- Recharts (data visualization)
- React Router (navigation)

## Notes

- The frontend is configured to proxy API requests to the backend at http://backend:8000
- For development without backend, the app will show loading states
- Mock authentication is enabled for preview (any username/password works)
