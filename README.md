# Agenthic Text2SQL & RAG

A production-grade, modular Agentic application using React (Frontend) and FastAPI (Backend).

## Architecture

- **Frontend**: React, Vite, TailwindCSS, Recharts.
- **Backend**: FastAPI, LangGraph, LangChain.
- **Agent**: Orchestrator node routing to SQL (Text2SQL) or RAG (Document Search).
- **Data**: SQLite (Business Data), ChromaDB (Vector Store).

## Prerequisites
- Python 3.10+
- Node.js 18+
- OpenAI API Key

## Setup

### 1. Backend

1. Navigate to backend:
   ```bash
   cd backend
   ```
2. Create virtual env (optional but recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure Environment:
   - Edit `.env` and add your `OPENAI_API_KEY`.
5. Initialize Data:
   ```bash
   # Initialize SQLite DB
   python -m app.db.init_db
   
   # Create dummy PDF (if needed)
   python -m app.utils.create_pdf
   
   # Ingest PDF to FAISS Vector Store
   uv run --python .venv -m app.rag.ingest --cwd backend
   ```
6. Run Server:
   ```bash
   uvicorn app.main:app --reload
   ```
   Server runs on `http://localhost:8000`.

### 2. Frontend

1. Navigate to frontend:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Run Development Server:
   ```bash
   npm run dev
   ```
   App runs on `http://localhost:5173`.

## Usage

1. Open the Frontend URL.
2. **Text2SQL**: Ask "Show me total sales by employee" or "Which department has the highest salary?".
3. **RAG**: Ask "What is the return policy?".
4. The Agent Orchestrator will route your request and show steps/results.
