# 🚀 Running in Kiro Terminal

Since you want to run this from Kiro, here's the simplest approach:

## Step 1: Start Backend (Terminal 1)

Open Kiro's terminal and run:

```bash
cd backend && ../.venv/bin/python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Application startup complete.
```

**Leave this terminal running!**

## Step 2: Start Frontend (Terminal 2)

Open a **second** Kiro terminal (or use your system terminal) and run:

```bash
cd frontend && npm run dev
```

You should see:
```
VITE v5.0.7  ready in XXX ms
➜  Local:   http://localhost:3000/
```

**Leave this terminal running too!**

## Step 3: Open in Browser

Open your browser to: **http://localhost:3000**

Login with any credentials (e.g., `admin` / `admin`)

You should now see 3 mock patients! 🎉

## Alternative: Run Script (Single Terminal)

If you want both in one terminal:

```bash
./run_servers.sh
```

This starts both servers in the background. You'll see the PIDs printed - save them to stop later:

```bash
kill <BACKEND_PID> <FRONTEND_PID>
```

## Verify Backend is Running

In another terminal:

```bash
curl http://localhost:8000/health
```

Should return: `{"status":"healthy"}`

## Stop Servers

Press `Ctrl+C` in each terminal where the servers are running.

Or if using the script, kill the PIDs:

```bash
# Find processes
lsof -i :8000  # Backend
lsof -i :3000  # Frontend

# Kill them
kill <PID>
```

## Troubleshooting

**"Address already in use":**
```bash
# Kill existing processes
lsof -ti:8000 | xargs kill -9  # Backend
lsof -ti:3000 | xargs kill -9  # Frontend
```

**Backend won't start:**
```bash
# Check Python and dependencies
cd backend
../.venv/bin/python --version
../.venv/bin/python -c "import fastapi, uvicorn; print('OK')"
```

**Frontend won't start:**
```bash
# Reinstall dependencies
cd frontend
npm install
```
