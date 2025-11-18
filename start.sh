#!/bin/bash

# RAG Commander - Multi-Service Startup Script
# Starts both FastAPI backend and Streamlit frontend

set -e

echo "Starting RAG Commander..."

# Use Railway's PORT or default ports
STREAMLIT_PORT=${PORT:-8501}
FASTAPI_PORT=${FASTAPI_PORT:-8080}

echo "Ports: Streamlit=$STREAMLIT_PORT, FastAPI=$FASTAPI_PORT"

# Start FastAPI in background
echo "Starting FastAPI backend on port $FASTAPI_PORT..."
uvicorn src.fastapi.main_api:app \
    --host 0.0.0.0 \
    --port $FASTAPI_PORT \
    --workers 1 \
    --log-level info &

FASTAPI_PID=$!
echo "FastAPI started (PID: $FASTAPI_PID)"

# Wait for FastAPI to be ready
echo "Waiting for FastAPI to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:$FASTAPI_PORT/ > /dev/null 2>&1; then
        echo "FastAPI is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "FastAPI failed to start within 30 seconds"
        exit 1
    fi
    sleep 1
done

# Set FastAPI URL for Streamlit to use
export FASTAPI_URL="http://localhost:$FASTAPI_PORT"

# Start Streamlit in foreground
echo "Starting Streamlit frontend on port $STREAMLIT_PORT..."
streamlit run src/streamlit/web.py \
    --server.address 0.0.0.0 \
    --server.port $STREAMLIT_PORT \
    --server.headless true \
    --server.enableCORS false \
    --browser.gatherUsageStats false

# If Streamlit exits, kill FastAPI
echo "Streamlit stopped, cleaning up..."
kill $FASTAPI_PID 2>/dev/null || true
