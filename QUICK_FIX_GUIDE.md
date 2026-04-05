# 🔧 Quick Fix: "Error loading patients"

## The Problem

The frontend shows "Error loading patients" because it needs the backend API server running.

## The Solution (3 Steps)

### Step 1: Fix the Vite Config ✅ (Already Done)

I've updated `frontend/vite.config.ts` to proxy API calls to `http://localhost:8000` instead of `http://backend:8000`.

### Step 2: Start the Backend Server

Open a **new terminal** and run:

```bash
cd backend
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### Step 3: Restart the Frontend

If the frontend is already running, **stop it** (Ctrl+C) and restart:

```bash
cd frontend
npm run dev
```

## Test It

1. Open http://localhost:3000
2. Login with `admin` / `admin` (or any credentials)
3. You should now see 3 mock patients in the list! 🎉

## What You Should See

**Patient List:**
- Patient 001: High risk (72%), Female, 68 years, Stage 3a
- Patient 002: Moderate risk (45%), Male, 55 years, Stage 2
- Patient 003: High risk (82%), Male, 72 years, Stage 3b

Click any patient to see detailed SHAP explanations and risk factors.

## Alternative: Use the Startup Script

I've created a script that starts both servers automatically:

```bash
./start_dev.sh
```

This will start both backend and frontend in one command.

## Verify Backend is Working

Test the backend directly:

```bash
curl http://localhost:8000/health
```

Should return: `{"status":"healthy"}`

Or open in browser: http://localhost:8000

Should show:
```json
{
  "name": "SDOH-CKDPred",
  "version": "0.1.0",
  "status": "running"
}
```

## Still Having Issues?

**Check if ports are available:**
```bash
# Check port 8000 (backend)
lsof -i :8000

# Check port 3000 (frontend)
lsof -i :3000
```

**Kill processes if needed:**
```bash
lsof -ti:8000 | xargs kill -9  # Kill backend
lsof -ti:3000 | xargs kill -9  # Kill frontend
```

**Check Python version:**
```bash
python3 --version  # Should be 3.8 or higher
```

**Reinstall backend dependencies if needed:**
```bash
cd backend
pip3 install -r requirements.txt
```

## Summary

The fix was simple:
1. ✅ Updated Vite proxy config (localhost instead of Docker hostname)
2. ▶️ Start backend server on port 8000
3. ▶️ Start frontend server on port 3000
4. 🎉 Dashboard now loads patient data!

The backend includes mock data, so no database setup is needed for demo purposes.
