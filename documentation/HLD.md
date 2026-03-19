# High-Level Design (HLD) - Text2SQL & RAG Application

## 1. System Overview

The application is an intelligent agent-based system that processes natural language queries and routes them to appropriate handlers (SQL generation or document retrieval) with built-in security guardrails and PII protection.

### 1.1 Key Components

```mermaid
graph TB
    subgraph Client["Client Layer"]
        WebUI[React Web UI]
        SSE["SSE Client - Active"]
    end
    
    subgraph API["API Gateway Layer"]
        FastAPI[FastAPI Server]
        Auth[Authentication]
        CORS[CORS Middleware]
    end
    
    subgraph Security["Security Layer"]
        InputGuard["Input Guardrails - NeMo"]
        OutputGuard["Output Guardrails - NeMo"]
        PIIDetect["PII Detection - Presidio"]
        ABAC["ABAC - Policy Decision Point"]
        SemanticRBAC["Semantic RBAC - Role-Filtered Schema"]
        DLP["DLP Masking - SQL Result Scrubber"]
    end
    
    subgraph Orchestration["Orchestration Layer"]
        LangGraph[LangGraph State Machine]
        Orchestrator[Intent Classifier]
    end
    
    subgraph Processing["Processing Layer"]
        SQL[SQL Pipeline]
        RAG[RAG Pipeline]
        General[General Response]
    end
    
    subgraph LLM["LLM Layer"]
        Sarvam["Sarvam AI - Primary"]
        Gemini["Google Gemini 2.0 - Secondary"]
        OpenAI["OpenAI GPT-4o - Tertiary Fallback"]
    end
    
    subgraph Data["Data Layer"]
        SQLite[(SQLite - Business Data)]
        FAISS[(FAISS - Vector Store)]
        Embeddings[Google Embeddings]
    end
    
    WebUI --> FastAPI
    FastAPI --> InputGuard
    InputGuard --> LangGraph
    LangGraph --> Orchestrator
    
    Orchestrator --> SQL
    Orchestrator --> RAG
    Orchestrator --> General
    
    SQL --> Sarvam
    RAG --> Sarvam
    General --> Sarvam
    
    Sarvam -.fallback.-> Gemini
    Gemini -.fallback.-> OpenAI
    
    SQL --> SQLite
    RAG --> FAISS
    FAISS --> Embeddings
    
    SQL --> OutputGuard
    RAG --> OutputGuard
    General --> OutputGuard
    
    OutputGuard --> FastAPI
    
    PIIDetect -.scrubs before.-> FAISS
```

## 2. Architecture Principles

### 2.1 Design Patterns
- **State Machine Pattern**: LangGraph manages agent flow
- **Strategy Pattern**: Different handlers for SQL/RAG/General
- **Chain of Responsibility**: Guardrails → Orchestrator → Handlers
- **Retry Pattern**: Automatic retry with exponential backoff for SQL generation
- **Observer Pattern**: SSE for real-time progress updates (active, streams per agent step).

### 2.2 Security-First Design
- **Defense in Depth**: Multiple layered security controls (guardrails, AST validation, ABAC, DLP, Semantic RBAC)
- **Fail-Safe Defaults**: Guardrails fail-open; sqlglot degrades gracefully to regex if unavailable
- **Least Privilege**: Minimal data exposure via PII anonymization, ABAC, and role-filtered schema injection
- **Zero Trust Execution**: Every SQL query passes through AST validation → ABAC PDP → DLP masking before the LLM sees results

## 3. Component Responsibilities

### 3.1 Frontend (React)
**Responsibility**: User interface and real-time updates

**Key Features**:
- Natural language query input
- Real-time agent step visualization via SSE
- SQL result display with charts (Recharts)
- RAG answer rendering
- Error handling and user feedback

**Technology Stack**:
- React 18 + Vite
- TailwindCSS for styling
- Recharts for visualization
- EventSource API (Active — receives per-step agent progress via SSE)

### 3.2 API Gateway (FastAPI)
**Responsibility**: HTTP request handling and routing

**Endpoints**:
- `POST /chat` - Main chat endpoint (creates SSE session, streams agent steps)
- `GET /sse/{session_id}` - Server-Sent Events stream (active)
- `GET /health` - Health check
- `POST /upload-docs` - Upload PDF document (admin only)

**Features**:
- CORS middleware for cross-origin requests
- Session management
- Error handling and logging
- OpenTelemetry instrumentation

### 3.3 Security Layer

#### Input Guardrails (NeMo)
**Responsibility**: Validate user inputs before processing

**Checks**:
- Jailbreak attempt detection
- Content moderation (inappropriate/harmful content)
- Topic adherence (SQL/document-related queries)

**Flow**:
```
User Input → NeMo Validation → [PASS: Continue] or [BLOCK: Return error]
```

#### Output Guardrails (NeMo)
**Responsibility**: Validate LLM responses before returning to user

**Checks**:
- Harmful content detection
- Inappropriate response filtering
- Safety compliance

**Flow**:
```
LLM Response → NeMo Validation → [PASS: Return] or [BLOCK: Replace with safe message]
```

#### PII Detection (Presidio)
**Responsibility**: Anonymize sensitive data before storage

**Detected Entities**:
- Email addresses, phone numbers
- SSNs, credit cards, passports
- Names, locations, dates
- IP addresses, URLs

**Flow**:
```
PDF Document → Split → PII Scrubber → Anonymized Text → Embeddings → FAISS
```

### 3.4 Orchestration Layer (LangGraph)

**Responsibility**: Route queries to appropriate handlers

**State Machine**:
- Entry: Input Guardrail
- Decision: Orchestrator (LLM-based intent classification)
- Routes: SQL / RAG / General
- Exit: Output Guardrail

**State Management**:
- Shared `AgentState` TypedDict
- Immutable state updates
- Conditional routing based on state

### 3.5 Processing Pipelines

#### SQL Pipeline
**Steps**:
1. **Schema Fetcher** — Injects role-filtered schema (Semantic RBAC — `user` only sees safe tables)
2. **SQL Generator** (LLM) — Converts NL to SQL using only the permitted schema
3. **Validator** — AST parsing via `sqlglot` (blocks DROP/INSERT, multi-statement injection, subquery table hiding)
4. **HITL Check** — Sensitive table queries routed to approval_pending; admin must approve via API
5. **Executor** — ABAC Policy Decision Point evaluated per-table before executing against SQLite
6. **Masking** (DLP) — PII scrubbed from result rows before LLM sees them (Presidio + vault)
7. **Evaluator** — Validates result quality
8. **Chart Generator** — Creates Vega-Lite spec
9. **Formatter** (LLM) — Natural language response (tokens de-anonymized by `deanonymize_text()` in main.py)

**Retry Logic**:
- Max 3 retries on validation/execution errors
- Error context passed to LLM for correction

#### RAG Pipeline
**Steps**:
1. **Retriever** - FAISS similarity search (k=3)
2. **RAG Generator** (LLM) - Answer from context
3. **Formatter** (LLM) - Natural language response

#### General Pipeline
**Steps**:
1. **Formatter** (LLM) - Direct response generation

### 3.6 LLM Layer

**Provider Chain** (configurable via `LLM_PROVIDER` env var, tries each in order on failure):

1. **Primary: Sarvam AI** (`sarvam-m`)
   - Indian multilingual LLM
   - OpenAI-compatible API endpoint
   - Used when `SARVAM_API_KEY` is set

2. **Secondary: Google Gemini 2.0 Flash**
   - Fast inference, cost-effective
   - Good reasoning capabilities
   - Used when `GOOGLE_API_KEY` is set

3. **Tertiary Fallback: OpenAI GPT-4o-mini**
   - Final safety net
   - Used when `OPENAI_API_KEY` is set

**Fallback Logic**: Each provider is tried in sequence. On any error, the next provider in the chain is attempted. If all fail, a `RateLimitException` is raised with a `retry_after` hint.

**Usage Points**:
- Orchestrator (intent classification)
- SQL Generator (NL → SQL)
- RAG Generator (context → answer)
- Formatter (result → NL)

### 3.7 Data Layer

#### SQLite Database
**Purpose**: Business data storage

**Schema**:
- `employees` - Employee records
- `sales` - Sales transactions
- `departments` - Department info
- `customers` - Customer data

#### FAISS Vector Store
**Purpose**: Document embeddings for RAG

**Features**:
- Fast similarity search
- Local storage (no external dependencies)
- Google text-embedding-004 model

**Ingestion Process**:
```
PDF → Load → Split (1000 chars, 200 overlap) → PII Scrub → Embed → Store
```

## 4. Data Flow

### 4.1 SQL Query Flow
```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant A as API
    participant IG as Input Guard
    participant O as Orchestrator
    participant S as SQL Pipeline
    participant DB as SQLite
    participant OG as Output Guard
    
    U->>F: "Show sales by employee"
    F->>A: POST /chat
    A->>IG: Validate input
    IG->>O: Input valid
    O->>O: Classify intent = 'sql'
    O->>S: Route to SQL
    S->>S: Fetch schema
    S->>S: Generate SQL (LLM)
    S->>S: Validate syntax
    S->>DB: Execute query
    DB-->>S: Results
    S->>S: Generate chart
    S->>S: Format response (LLM)
    S->>OG: Validate output
    OG->>A: Output valid
    A->>F: Result + Chart
    F->>U: Display results + chart
```

### 4.2 RAG Query Flow
```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant A as API
    participant IG as Input Guard
    participant O as Orchestrator
    participant R as RAG Pipeline
    participant V as FAISS
    participant OG as Output Guard
    
    U->>F: "What is the refund policy?"
    F->>A: POST /chat
    A->>IG: Validate input
    IG->>O: Input valid
    O->>O: Classify intent = 'rag'
    O->>R: Route to RAG
    R->>V: Similarity search
    V-->>R: Top 3 documents
    R->>R: Generate answer (LLM)
    R->>R: Format response (LLM)
    R->>OG: Validate output
    OG->>A: Output valid
    A->>F: Result
    F->>U: Display answer
```

## 5. Non-Functional Requirements

### 5.1 Performance
- **Response Time**: < 5s for SQL queries, < 3s for RAG
- **Throughput**: 10 concurrent users
- **LLM Latency**: ~1-2s per call (Gemini)

### 5.2 Scalability
- **Horizontal**: Stateless API allows multiple instances
- **Vertical**: SQLite suitable for < 100GB data
- **FAISS**: In-memory, scales to millions of vectors

### 5.3 Security
- **Input Validation**: NeMo Guardrails (jailbreak, content moderation)
- **SQL Validation**: `sqlglot` AST (blocks DROP, multi-statement injection, subquery table hiding)
- **Output Filtering**: NeMo Guardrails + PII de-anonymization via vault
- **Data Privacy**: PII scrubbing at RAG ingestion AND at SQL result masking (Presidio)
- **Access Control**: ABAC (deny-first policy per table) + Semantic RBAC (role-filtered schema)
- **HITL**: Human-in-the-loop approval for sensitive table queries
- **API Security**: CORS, JWT, rate limiting

### 5.4 Reliability
- **Retry Logic**: 3 retries for SQL generation
- **Fallback LLM**: OpenAI (disabled, can be enabled)
- **Fail-Safe Guardrails**: Fail-open on initialization errors
- **Error Handling**: Graceful degradation

### 5.5 Observability
- **Tracing**: OpenTelemetry for all agent nodes
- **Logging**: Structured logs for debugging
- **Monitoring**: SSE for real-time progress
- **Metrics**: LLM call counts, latencies (future)

## 6. Deployment Architecture

### 6.1 Development
```
Frontend: localhost:5173 (Vite dev server)
Backend: localhost:8000 (Uvicorn)
Database: SQLite file (./data/business.db)
Vector Store: FAISS file (./data/faiss_index)
```

### 6.2 Production (Recommended)
```
Frontend: Vercel / Netlify (static hosting)
Backend: Docker container on Cloud Run / ECS
Database: SQLite → PostgreSQL (for multi-user)
Vector Store: FAISS → Pinecone / Weaviate (for scale)
LLM: Google Gemini API (managed)
Observability: LangSmith / Datadog
```

## 7. Technology Decisions

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Frontend Framework | React | Industry standard, rich ecosystem |
| Build Tool | Vite | Fast HMR, modern tooling |
| Styling | TailwindCSS | Utility-first, rapid development |
| Backend Framework | FastAPI | Async support, auto docs, Python |
| Agent Framework | LangGraph | State machine for agents, LangChain integration |
| Guardrails | NeMo | NVIDIA-backed, flexible configuration |
| PII Detection | Presidio | Microsoft-backed, comprehensive entity detection |
| Primary LLM | Gemini 2.0 | Fast, cost-effective, good reasoning |
| Vector DB | FAISS | Local, fast, no external dependencies |
| Business DB | SQLite | Simple, embedded, sufficient for demo |
| Embeddings | Google text-embedding-004 | High quality, cost-effective |

## 8. Future Enhancements

### 8.1 Short-term (Completed)
- [x] Add authentication (JWT)
- [x] Implement rate limiting
- [x] Add conversation history
- [x] ABAC + Semantic RBAC security
- [x] AST SQL validation (sqlglot)
- [x] DLP masking node for SQL results
- [x] HITL approval workflow for sensitive queries

### 8.2 Medium-term
- [ ] Migrate to PostgreSQL for production
- [ ] Add caching layer (Redis)
- [ ] Implement A/B testing for LLM models
- [ ] Add more chart types

### 8.3 Long-term
- [ ] Multi-database support
- [ ] Custom model fine-tuning
- [ ] Advanced analytics dashboard
- [ ] Mobile app (React Native)
