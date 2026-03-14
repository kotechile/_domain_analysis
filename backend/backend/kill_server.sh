#!/bin/bash
# Quick script to kill processes on port 8000

echo "Finding processes on port 8000..."
PIDS=$(lsof -ti :8000)

if [ -z "$PIDS" ]; then
    echo "✅ Port 8000 is free"
else
    echo "Killing processes: $PIDS"
    kill -9 $PIDS
    sleep 1
    if lsof -i :8000 > /dev/null 2>&1; then
        echo "❌ Some processes couldn't be killed"
    else
        echo "✅ Port 8000 is now free"
    fi
fi











