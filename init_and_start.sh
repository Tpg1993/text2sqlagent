#!/bin/bash
# SYNOPSIS
# Initializes and starts the Agentic Text2SQL & RAG application.
#
# DESCRIPTION
# This script automates the setup process for Linux/macOS:
# 1. Creates and activates a Python virtual environment.
# 2. Installs backend dependencies.
# 3. Initializes the SQLite database.
# 4. Processes documents to create RAG embeddings (FAISS index).
# 5. Installs frontend dependencies.
# 6. Starts the backend (FastAPI) and frontend (Vite) servers concurrently.

set -e  # Exit on error
WORKING_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "======================================================="
echo "🚀 Initializing Agentic Text2SQL & RAG Application Setup"
echo "======================================================="

# --- 1. Backend Setup ---
BACKEND_DIR="$WORKING_DIR/backend"
echo -e "\n[1/6] Setting up Backend Virtual Environment..."
cd "$BACKEND_DIR"

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment in backend/.venv..."
    python3 -m venv .venv
fi

PYTHON_EXE="$BACKEND_DIR/.venv/bin/python"

echo -e "\n[2/6] Installing Backend Dependencies..."
uv pip install -r requirements.txt -q
if [ $? -ne 0 ]; then
    echo "ERROR: Backend dependency installation failed." >&2
    exit 1
fi

# Set environment variables for Python scripts
export PYTHONPATH="$BACKEND_DIR"
export PYTHONIOENCODING="utf-8"

echo -e "\n[3/6] Checking SQLite Database..."
DATABASE_FILE="$BACKEND_DIR/data/sales.db"
if [ ! -f "$DATABASE_FILE" ]; then
    echo "Database not found. Initializing with sample data..."
    $PYTHON_EXE -m app.db.init_db
else
    echo "Database already exists. Skipping initialization to preserve existing data."
    echo "To reset it, delete $DATABASE_FILE and run this script again."
fi

echo -e "\n[4/6] Checking RAG Embeddings & FAISS Index..."
FAISS_INDEX_DIR="$BACKEND_DIR/data/faiss_index"
if [ ! -f "$FAISS_INDEX_DIR/index.faiss" ]; then
    echo "FAISS index not found. Creating embeddings now..."
    $PYTHON_EXE -m app.rag.ingest
else
    echo "FAISS index already exists. Skipping ingestion to save time and API tokens."
    echo "To recreate it, delete the $FAISS_INDEX_DIR folder or run the ingest script manually."
fi

# --- 2. Frontend Setup ---
FRONTEND_DIR="$WORKING_DIR/frontend"
echo -e "\n[5/6] Setting up Frontend & Installing Dependencies..."
cd "$FRONTEND_DIR"

echo "Running npm install..."
npm install > /dev/null
if [ $? -ne 0 ]; then
    echo "ERROR: Frontend dependency installation failed." >&2
    exit 1
fi

# --- 3. Start Servers Concurrently ---
echo -e "\n[6/6] Starting Applications..."
cd "$WORKING_DIR"

echo "Starting Backend on port 8000..."
cd "$BACKEND_DIR"
$PYTHON_EXE -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
cd "$WORKING_DIR"

echo "Starting Frontend on port 5173..."
cd "$FRONTEND_DIR"
npm run dev &
FRONTEND_PID=$!
cd "$WORKING_DIR"

echo -e "\n✅ All services have been launched!"
echo "Frontend: http://localhost:5173"
echo "Backend API: http://localhost:8000"
echo "======================================================="
echo "Press Ctrl+C to stop both servers."

# Stop background processes cleanly on Ctrl+C
trap "echo 'Stopping servers...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM

wait
