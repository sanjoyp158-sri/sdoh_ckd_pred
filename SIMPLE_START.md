# ✅ Simple Start Guide - Just 2 Commands!

## You Need 2 Terminals Running

### Terminal 1 - Backend (Port 8000)
```bash
cd backend && ../.venv/bin/python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Wait for: `Application startup complete.`

### Terminal 2 - Frontend (Port 3000)
```bash
cd frontend && npm run dev
```

Wait for: `Local: http://localhost:3000/`

## Then Open Browser

Go to: **http://localhost:3000**

Login with **ANY** username and password:
- admin / admin ✅
- test / test ✅
- doctor / password ✅
- literally anything works! ✅

## What You'll See

After login, you'll see 3 mock patients:
- Patient 001: High risk (72%), Female, 68 years
- Patient 002: Moderate risk (45%), Male, 55 years
- Patient 003: High risk (82%), Male, 72 years

Click any patient to see detailed risk factors and SHAP explanations!

## Troubleshooting

**"Invalid credentials" error:**
- Backend isn't running - check Terminal 1
- Run: `curl http://localhost:8000/health` (should return `{"status":"healthy"}`)

**"Error loading patients" error:**
- Backend isn't running on port 8000
- Or frontend isn't proxying correctly

**Port already in use:**
```bash
lsof -ti:8000 | xargs kill -9  # Kill backend
lsof -ti:3000 | xargs kill -9  # Kill frontend
```

## Stop Servers

Press `Ctrl+C` in each terminal.

---

That's it! Just 2 terminals, 2 commands, and you're done! 🎉
