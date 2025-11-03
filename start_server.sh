#!/bin/bash

# Script to start the Essay Evaluation API with proper asyncio configuration
# This avoids uvloop conflicts that cause "Can't patch loop" errors

echo "🚀 Starting Essay Evaluation API Server"
echo "📋 Configuration:"
echo "   - Using standard asyncio loop (not uvloop)"
echo "   - Local template reading enabled"
echo "   - Host: 0.0.0.0"
echo "   - Port: 8080"
echo ""

# Kill any existing processes on port 8080
echo "🔍 Checking for existing processes on port 8080..."
lsof -ti:8080 | xargs kill -9 2>/dev/null || echo "   No existing processes found"

# Start the server with asyncio loop
echo "🏁 Starting server..."
uvicorn api:app --host 0.0.0.0 --port 8080 --loop asyncio --reload

# Alternative command if the above doesn't work:
# python3 main.py