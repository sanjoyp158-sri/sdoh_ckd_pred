#!/bin/bash

# Simple script to run both backend and frontend servers
# Run this in your Kiro terminal

echo "🚀 Starting CKD Early Detection System..."
echo ""

# Start backend
echo "📦 Starting Backend API on port 8000..."
cd backend
../.venv/bin/python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

# Wait for backend
echo "⏳ Waiting for backend to start..."
sleep 3

# Check backend
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Backend running at http://localhost:8000"
else
    echo "⚠️  Backend may still be starting..."
fi

echo ""

# Start frontend
echo "🎨 Starting Frontend on port 3000..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ Servers started!"
echo ""
echo "📍 Backend:  http://localhost:8000"
echo "📍 Frontend: http://localhost:3000"
echo ""
echo "Backend PID: $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"
echo ""
echo "To stop servers:"
echo "  kill $BACKEND_PID $FRONTEND_PID"
echo ""
echo "Press Ctrl+C to stop (may need to kill PIDs manually)"

# Keep script running
wait
