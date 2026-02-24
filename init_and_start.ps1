<#
.SYNOPSIS
Initializes and starts the Agentic Text2SQL & RAG application.

.DESCRIPTION
This script automates the setup process:
1. Creates and activates a Python virtual environment.
2. Installs backend dependencies.
3. Initializes the SQLite database.
4. Processes documents to create RAG embeddings (FAISS index).
5. Installs frontend dependencies.
6. Starts the backend (FastAPI) and frontend (Vite) servers concurrently.
#>

$ErrorActionPreference = "Stop"
$WorkingDir = $PSScriptRoot

Write-Output "======================================================="
Write-Output "🚀 Initializing Agentic Text2SQL & RAG Application Setup"
Write-Output "======================================================="

# --- 1. Backend Setup ---
$BackendDir = Join-Path $WorkingDir "backend"
Write-Output "`n[1/6] Setting up Backend Virtual Environment..."
Set-Location $BackendDir

if (-not (Test-Path ".venv")) {
    Write-Output "Creating virtual environment in backend/.venv..."
    python -m venv .venv
}

$PythonExe = Join-Path $BackendDir ".venv\Scripts\python.exe"
$PipExe = Join-Path $BackendDir ".venv\Scripts\pip.exe"

Write-Output "`n[2/6] Installing Backend Dependencies..."
& $PipExe install -r requirements.txt -q
if ($LASTEXITCODE -ne 0) { throw "Backend dependency installation failed." }

# Set environment variables for Python scripts
$env:PYTHONPATH = $BackendDir
$env:PYTHONIOENCODING = "utf-8"

Write-Output "`n[3/6] Initializing SQLite Database..."
& $PythonExe -m app.db.init_db

Write-Output "`n[4/6] Checking RAG Embeddings & FAISS Index..."
$FaissIndexDir = Join-Path $BackendDir "data\faiss_index"
if (-not (Test-Path (Join-Path $FaissIndexDir "index.faiss"))) {
    Write-Output "FAISS index not found. Creating embeddings now..."
    & $PythonExe -m app.rag.ingest
}
else {
    Write-Output "FAISS index already exists. Skipping ingestion to save time and API tokens."
    Write-Output "To recreate it, delete the $FaissIndexDir folder or run run_ingest.ps1 manually."
}

# --- 2. Frontend Setup ---
$FrontendDir = Join-Path $WorkingDir "frontend"
Write-Output "`n[5/6] Setting up Frontend & Installing Dependencies..."
Set-Location $FrontendDir

Write-Output "Running npm install..."
npm install > $null
if ($LASTEXITCODE -ne 0) { throw "Frontend dependency installation failed." }

# --- 3. Start Servers Concurrently ---
Write-Output "`n[6/6] Starting Applications..."
Set-Location $WorkingDir

Write-Output "Starting Backend on port 8000..."
Start-Process -NoNewWindow -FilePath powershell.exe -ArgumentList "-Command `"cd backend; & .\run_app.ps1`""

Write-Output "Starting Frontend on port 5173..."
Start-Process -NoNewWindow -FilePath powershell.exe -ArgumentList "-Command `"cd frontend; npm run dev`""

Write-Output "`n✅ All services have been launched!"
Write-Output "Frontend: http://localhost:5173"
Write-Output "Backend API: http://localhost:8000"
Write-Output "======================================================="
