# Low-Level Design (LLD) - Text2SQL & RAG Application

## 1. Module-Level Architecture

### 1.1 Backend Module Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── config.py               # Configuration management
│   │
│   ├── agents/                 # Individual agent nodes
│   │   ├── orchestrator.py    # Intent classification (LLM)
│   │   ├── schema.py           # Database schema fetcher
│   │   ├── generate.py         # SQL generation (LLM)
│   │   ├── validate.py         # SQL syntax validation
│   │   ├── execute.py          # SQL execution
│   │   ├── evaluate.py         # Result validation
│   │   ├── retry.py            # Retry counter management
│   │   ├── chart.py            # Vega-Lite chart generation
│   │   ├── format.py           # Response formatting (LLM)
│   │   ├── rag_retrieve.py     # FAISS retrieval
│   │   └── rag_generate.py     # RAG answer generation (LLM)
│   │
│   ├── graphs/                 # LangGraph workflow
│   │   └── agent_graph.py      # State machine definition
│   │
│   ├── utils/                  # Shared utilities
│   │   ├── llm.py              # LLM invocation with fallback
│   │   ├── guardrails.py       # NeMo Guardrails wrapper
│   │   ├── pii.py              # Presidio PII scrubber
│   │   ├── state.py            # AgentState TypedDict
│   │   ├── exceptions.py       # Custom exceptions
│   │   └── sse_manager.py      # Server-Sent Events manager
│   │
│   ├── db/                     # Database management
│   │   ├── init_db.py          # SQLite initialization
│   │   └── vault.py            # Two-Way PII Vault (token store & retrieval)
│   │
│   └── rag/                    # RAG components
│       ├── ingest.py           # PDF ingestion with PII scrubbing
│       └── retriever.py        # FAISS retriever factory
│
├── config/
│   └── rails/                  # NeMo Guardrails config
│       ├── config.yml          # Rails configuration
│       └── prompts.yml         # Validation prompts
│
└── data/
    ├── business.db             # SQLite database
    ├── faiss_index/            # FAISS vector store
    └── docs/                   # PDF documents
        └── support.pdf
```

## 2. Detailed Component Design

### 2.1 FastAPI Application (`main.py`)

#### Class: N/A (Functional)

#### Key Functions:

```python
@app.post("/chat")
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Main chat endpoint.
    
    Flow:
    1. Generate session_id
    2. Create initial state with question
    3. Invoke LangGraph workflow
    4. Extract final response text from state
    5. De-anonymize response via deanonymize_text() (restore PII tokens → originals)
    6. Return ChatResponse
    
    Error Handling:
    - RateLimitException → 429 with retry_after
    - General Exception → 500 with error message
    """
```

```python
@app.get("/sse/{session_id}")
async def sse_stream(session_id: str):
    """
    (DISABLED) Server-Sent Events endpoint.
    Currently returns an empty response to prevent client-side hanging.
    """
```

#### Data Models:

```python
class ChatRequest(BaseModel):
    question: str
    
class ChatResponse(BaseModel):
    answer: str
    sql_query: Optional[str]
    sql_result: Optional[List[Dict]]
    visualization_spec: Optional[Dict]
    error: Optional[str]
```

### 2.2 LangGraph Workflow (`agent_graph.py`)

#### State Definition:

```python
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    question: str
    intent: Optional[str]  # 'sql', 'rag', 'general', 'blocked'
    
    # SQL Flow
    schema: Optional[str]
    sql_query: Optional[str]
    sql_result: Optional[Union[List[Dict], str]]
    sql_valid: bool
    error: Optional[str]
    visualization_spec: Optional[Dict]
    
    # RAG Flow
    documents: Optional[List[Any]]
    rag_answer: Optional[str]
    
    # Meta
    retry_count: int
    session_id: Optional[str]
```

#### Node Functions:

Each agent node follows this signature:
```python
def node_name(state: AgentState) -> Dict[str, Any]:
    """
    Process state and return updates.
    
    Args:
        state: Current agent state
        
    Returns:
        Dict with state updates (merged into state)
    """
```

#### Routing Functions:

```python
def route_input_guardrail(state: AgentState) -> str:
    """Route based on guardrail validation result."""
    if state.get('intent') == 'blocked':
        return 'format'  # Skip to format with error
    return 'orchestrator'

def route_orchestrator(state: AgentState) -> str:
    """Route based on classified intent."""
    return state.get('intent', 'general')  # 'sql', 'rag', or 'general'

def route_validate(state: AgentState) -> str:
    """Route based on SQL validation."""
    if state.get("sql_valid"):
        return "execute"
    return "retry"

def route_evaluate(state: AgentState) -> str:
    """Route based on execution result."""
    if state.get("error"):
        return "retry"
    return "chart"

def route_retry(state: AgentState) -> str:
    """Route based on retry count."""
    if state.get("retry_count", 0) > 3:
        return "format"  # Give up
    return "generate"  # Try again
```

### 2.3 Agent Nodes (Detailed)

#### 2.3.1 Input Guardrail Node

```python
def input_guardrail_node(state: AgentState) -> Dict[str, Any]:
    """
    Validate user input using NeMo Guardrails.
    
    Logic:
    1. Get guardrail manager instance
    2. Extract question from state
    3. Call validate_input(question)
    4. If blocked:
        - Set intent='blocked'
        - Set error=error_message
    5. If allowed:
        - Return empty dict (no state changes)
    
    Returns:
        {'intent': 'blocked', 'error': '...'} or {}
    """
    guardrails = get_guardrail_manager()
    question = state.get("question", "")
    is_valid, error_msg = guardrails.validate_input(question)
    
    if not is_valid:
        return {"error": error_msg, "intent": "blocked"}
    return {}
```

#### 2.3.2 Orchestrator Node

```python
def orchestrator_node(state: AgentState) -> Dict[str, Any]:
    """
    Classify user intent using LLM.
    
    Logic:
    1. Create prompt with question
    2. Invoke LLM via invoke_chain_with_fallback
    3. Parse response to extract intent
    4. Return {'intent': 'sql' | 'rag' | 'general'}
    
    Prompt Template:
    \"\"\"
    Classify the following question into one of these categories:
    - 'sql': Questions about database queries, data analysis
    - 'rag': Questions about policies, documentation
    - 'general': Greetings, general conversation
    
    Question: {question}
    
    Respond with only: sql, rag, or general
    \"\"\"
    """
    prompt = ChatPromptTemplate.from_template(...)
    chain = prompt | StrOutputParser()
    result = invoke_chain_with_fallback(lambda llm: chain, {"question": state["question"]})
    intent = result.strip().lower()
    
    return {"intent": intent, "messages": [AIMessage(content=f"Intent: {intent}")]}
```

#### 2.3.3 SQL Generate Node

```python
def generate_node(state: AgentState) -> Dict[str, Any]:
    """
    Generate SQL query from natural language.
    
    Logic:
    1. Get schema from state
    2. Get question and error (if retry)
    3. Create prompt with schema, question, error context
    4. Invoke LLM
    5. Extract SQL from response (remove markdown)
    6. Return {'sql_query': '...'}
    
    Prompt Template:
    \"\"\"
    You are a SQL expert. Generate a SQLite query.
    
    Schema:
    {schema}
    
    Question: {question}
    
    {error_context}
    
    Return only the SQL query, no explanation.
    \"\"\"
    """
    schema = state.get("schema", "")
    question = state.get("question", "")
    error = state.get("error", "")
    
    error_context = f"Previous error: {error}\nFix the query." if error else ""
    
    prompt = ChatPromptTemplate.from_template(...)
    chain = prompt | StrOutputParser()
    result = invoke_chain_with_fallback(lambda llm: chain, {
        "schema": schema,
        "question": question,
        "error_context": error_context
    })
    
    sql_query = result.replace("```sql", "").replace("```", "").strip()
    return {"sql_query": sql_query, "error": None}
```

#### 2.3.4 Validate Node

```python
def validate_node(state: AgentState) -> Dict[str, Any]:
    """
    Validate SQL syntax using sqlparse.
    
    Logic:
    1. Get sql_query from state
    2. Parse with sqlparse.parse()
    3. Check if parsed successfully
    4. Return {'sql_valid': True/False}
    """
    import sqlparse
    
    sql_query = state.get("sql_query", "")
    try:
        parsed = sqlparse.parse(sql_query)
        is_valid = len(parsed) > 0 and parsed[0].get_type() != 'UNKNOWN'
        return {"sql_valid": is_valid}
    except Exception as e:
        return {"sql_valid": False, "error": str(e)}
```

#### 2.3.5 Execute Node

```python
def execute_node(state: AgentState) -> Dict[str, Any]:
    """
    Execute SQL query against SQLite.
    
    Logic:
    1. Get sql_query from state
    2. Connect to SQLite database
    3. Execute query with cursor
    4. Fetch results
    5. Convert to list of dicts
    6. Return {'sql_result': [...]}
    
    Error Handling:
    - Catch sqlite3.Error
    - Return {'error': '...', 'sql_result': None}
    """
    import sqlite3
    from app.config import settings
    
    sql_query = state.get("sql_query", "")
    
    try:
        conn = sqlite3.connect(settings.DATABASE_URL.replace("sqlite:///", ""))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(sql_query)
        rows = cursor.fetchall()
        result = [dict(row) for row in rows]
        conn.close()
        
        return {"sql_result": result, "error": None}
    except sqlite3.Error as e:
        return {"error": f"SQL execution error: {str(e)}", "sql_result": None}
```

#### 2.3.6 Chart Node

```python
def chart_node(state: AgentState) -> Dict[str, Any]:
    """
    Generate Vega-Lite chart specification.
    
    Logic:
    1. Get sql_result from state
    2. Infer chart type based on data shape
    3. Create Vega-Lite spec
    4. Return {'visualization_spec': {...}}
    
    Chart Type Inference:
    - 1 column: Bar chart (count)
    - 2 columns (1 string, 1 number): Bar chart
    - 2 columns (both numbers): Scatter plot
    - 3+ columns: Table (no chart)
    """
    sql_result = state.get("sql_result", [])
    
    if not sql_result or len(sql_result) == 0:
        return {"visualization_spec": None}
    
    columns = list(sql_result[0].keys())
    
    if len(columns) == 2:
        x_field, y_field = columns
        spec = {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "data": {"values": sql_result},
            "mark": "bar",
            "encoding": {
                "x": {"field": x_field, "type": "nominal"},
                "y": {"field": y_field, "type": "quantitative"}
            }
        }
        return {"visualization_spec": spec}
    
    return {"visualization_spec": None}
```

### 2.4 Security Components

#### 2.4.1 Guardrails Manager (`guardrails.py`)

```python
class GuardrailManager:
    def __init__(self, config_path: Optional[str] = None):
        """Initialize NeMo Guardrails."""
        self.config = RailsConfig.from_path(config_path)
        self.rails = LLMRails(self.config)
    
    def validate_input(self, user_input: str) -> Tuple[bool, Optional[str]]:
        """
        Validate user input.
        
        Returns:
            (is_valid, error_message)
        """
        try:
            response = self.rails.generate(
                messages=[{"role": "user", "content": user_input}]
            )
            
            if response and "cannot" in response.get("content", "").lower():
                return False, "Your request cannot be processed due to safety guidelines."
            
            return True, None
        except Exception as e:
            # Fail-open
            return True, None
    
    def validate_output(self, bot_response: str) -> Tuple[bool, Optional[str]]:
        """
        Validate LLM output.
        
        Returns:
            (is_valid, replacement_message)
        """
        harmful_patterns = ["hack", "exploit", "illegal", ...]
        
        for pattern in harmful_patterns:
            if pattern in bot_response.lower():
                return False, "I cannot provide that information."
        
        return True, None
```

#### 2.4.2 PII Scrubber (`pii.py`) + PII Vault (`vault.py`)

The system implements **Two-Way PII Tokenization** — PII is replaced with secure tokens at ingestion time and restored to original values at query-response time.

**Ingestion (One-Time):**
```python
class PIIScrubber:
    def __init__(self):
        """Initialize Presidio with a custom alphanumeric phone recognizer."""
        self.analyzer = AnalyzerEngine()
        # Custom recognizer for vanity numbers like 1-800-COMPANY
        custom_phone_recognizer = PatternRecognizer(
            supported_entity="PHONE_NUMBER",
            name="alphanumeric_phone_recognizer",
            patterns=[Pattern("alphanumeric_phone",
                r"\b1-[0-9]{3}-[A-Z0-9]{4,10}\b|\b[0-9]{3}-[A-Z0-9]{4,10}\b", 0.8)]
        )
        self.analyzer.registry.add_recognizer(custom_phone_recognizer)
        self.entities_to_detect = [
            "PHONE_NUMBER", "EMAIL_ADDRESS", "CREDIT_CARD",
            "US_SSN", "PERSON", "LOCATION", ...
        ]
    
    def scrub_text(self, text: str, language: str = "en") -> str:
        """
        Detect PII, filter overlapping detections, tokenize using vault.
        
        Logic:
        1. Analyze text with Presidio
        2. Filter overlapping entities (greedy approach — largest span wins)
        3. For each entity, call store_pii() to get a unique token
        4. Replace original value in text with token
        5. Return scrubbed text
        
        Example:
            Input:  "Call us at 1-800-COMPANY or email info@co.com"
            Output: "Call us at [PII_PHONE_NUMBER_a1b2c3d4] or email [PII_EMAIL_ADDRESS_e5f6a7b8]"
        """
```

**PII Vault (`vault.py`):**
```python
def store_pii(entity_type: str, original_value: str) -> str:
    """
    Store PII in a secure SQLite table and return a deterministic token.
    If the same value already exists, returns the existing token (de-duplication).
    
    Token format: [PII_<ENTITY_TYPE>_<8-char-uuid-hex>]
    Example:      [PII_EMAIL_ADDRESS_a1b2c3d4]
    """

def retrieve_pii(token: str) -> str:
    """
    Retrieve original PII value for a given token.
    Returns the token itself if not found (fail-safe).
    """

def deanonymize_text(text: str) -> str:
    """
    Scan text for [PII_...] tokens and replace with original values.
    Also converts any legacy <TAG> style tokens to bracket form for UI safety.
    Called in /chat endpoint on the final LLM response before sending to user.
    """
```

### 2.5 LLM Invocation (`llm.py`)

```python
def invoke_chain_with_fallback(chain_factory, input_data: Dict) -> str:
    """
    Invoke LLM chain with Gemini primary and OpenAI fallback.
    
    Logic:
    1. Try Gemini 2.0 Flash
    2. If rate limit (429) → Raise RateLimitException (fail-fast)
    3. If other error → Try OpenAI (currently disabled)
    4. Return result
    
    Rate Limit Handling:
    - Extract retry_after from error message
    - Raise custom RateLimitException
    - Frontend displays wait time to user
    """
    try:
        # Gemini invocation
        client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        
        def gemini_runner(prompt_value):
            prompt_text = prompt_value.to_string()
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt_text
            )
            return AIMessage(content=response.text)
        
        llm = RunnableLambda(gemini_runner)
        chain = chain_factory(llm)
        result = chain.invoke(input_data)
        return result
        
    except Exception as e:
        # Check for rate limit
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            retry_after = extract_retry_delay(str(e))
            raise RateLimitException(
                message=f"Rate limit exceeded. Wait {retry_after}s",
                retry_after=retry_after
            )
        
        # Re-raise other errors (fallback disabled)
        raise e
```

## 3. Database Schema

### 3.1 SQLite Tables

```sql
-- Employees
CREATE TABLE employees (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    department_id INTEGER,
    salary REAL,
    hire_date TEXT,
    FOREIGN KEY (department_id) REFERENCES departments(id)
);

-- Departments
CREATE TABLE departments (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    manager_id INTEGER,
    FOREIGN KEY (manager_id) REFERENCES employees(id)
);

-- Sales
CREATE TABLE sales (
    id INTEGER PRIMARY KEY,
    employee_id INTEGER,
    customer_id INTEGER,
    amount REAL,
    sale_date TEXT,
    FOREIGN KEY (employee_id) REFERENCES employees(id),
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

-- Customers
CREATE TABLE customers (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    state TEXT
);
```

## 4. API Specifications

### 4.1 POST /chat

**Request**:
```json
{
  "question": "Show me total sales by employee"
}
```

**Response (Success)**:
```json
{
  "answer": "Here are the total sales by employee...",
  "sql_query": "SELECT employee_name, SUM(amount) FROM sales...",
  "sql_result": [
    {"employee_name": "John", "total": 15000},
    {"employee_name": "Jane", "total": 20000}
  ],
  "visualization_spec": {
    "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
    "data": {"values": [...]},
    "mark": "bar",
    ...
  },
  "error": null
}
```

**Response (Error)**:
```json
{
  "answer": "I encountered an error...",
  "sql_query": null,
  "sql_result": null,
  "visualization_spec": null,
  "error": "SQL execution error: ..."
}
```

**Response (Rate Limit - 429)**:
```json
{
  "detail": "Rate limit exceeded. Please try again in 60 seconds.",
  "retry_after": "60"
}
```

### 4.2 POST /upload-docs *(Admin Only)*

Allows admin users to upload a PDF document. The ingestion pipeline (PII scrubbing, embedding, FAISS indexing) runs as a background task.

**Auth**: Bearer token required. Role must be `admin`.

**Request**: `multipart/form-data` with a PDF file field `file`.

**Response (Success)**:
```json
{
  "message": "File 'support.pdf' uploaded and ingestion started in the background."
}
```

**Response (Unauthorized)**:
```json
{
  "detail": "Admin access required."
}
```

**Response (Invalid File)**:
```json
{
  "detail": "Only PDF files are allowed."
}
```


### 4.2 GET /sse/{session_id}

**Response (SSE Stream)**:
```
event: progress
data: {"step": "orchestrator", "message": "🤖 Analyzing query..."}

event: progress
data: {"step": "schema", "message": "📋 Fetching database schema..."}

event: progress
data: {"step": "generate", "message": "✍️ Generating SQL..."}

event: complete
data: {"status": "done"}
```

*(Note: Currently returns content-length 0 placeholder to prevent errors).*

## 5. Error Handling Strategy

### 5.1 Error Types

| Error Type | Handling | HTTP Status |
|------------|----------|-------------|
| RateLimitException | Return retry_after, fail-fast | 429 |
| ValidationError | Return error message | 400 |
| SQLExecutionError | Retry up to 3 times | 200 (in response) |
| LLMError | Fallback to OpenAI (disabled) | 500 |
| GuardrailBlock | Return safe message | 200 (in response) |

### 5.2 Retry Logic

```python
# Implemented in LangGraph routing
if error and retry_count <= 3:
    retry_count += 1
    route_to_generate()  # Try again with error context
else:
    route_to_format()  # Give up, return error to user
```

## 6. Performance Considerations

### 6.1 Caching
- **Not Implemented**: Future enhancement
- **Recommendation**: Cache LLM responses for identical queries (Redis)

### 6.2 Connection Pooling
- **SQLite**: Single connection per request (sufficient for demo)
- **FAISS**: Loaded once at startup, kept in memory

### 6.3 Async Operations
- **FastAPI**: Async endpoints for non-blocking I/O
- **LLM Calls**: Synchronous (LangChain limitation)

## 7. Continuous Evaluation Framework

The application implements a **4-pillar continuous evaluation framework** covering every pipeline type.
All eval scripts live in `backend/evaluation/` and detailed docs in `documentation/evaluation/`.

### 7.1 Evaluation Overview

| Pillar | Pipeline | Tool | Script | Doc |
|---|---|---|---|---|
| 1 | Orchestrator (Routing) | Custom golden dataset | `eval_orchestrator.py` | `01_orchestrator_eval.md` |
| 2 | RAG (Retrieval + Generation) | RAGAS | `eval_rag.py` | `02_rag_eval.md` |
| 3 | Text2SQL (Generation + Execution) | DeepEval + Structural | `eval_text2sql.py` | `03_text2sql_eval.md` |
| 4 | General Agent | LLM-as-a-judge | `eval_general.py` | `04_general_eval.md` |

### 7.2 Pillar 1 — Orchestrator Routing (`eval_orchestrator.py`)

Evaluates routing accuracy using a **70-case golden dataset** across 5 categories:
`clear_sql`, `clear_rag`, `clear_general`, `ambiguous_sql_rag`, `adversarial`.

**Metrics:** Overall accuracy, per-class Precision / Recall / F1, ambiguity subset accuracy.

**CI Thresholds:** Overall ≥ 95%, per-class recall ≥ 85%.

```powershell
python evaluation/eval_orchestrator.py --limit 10   # dev run
python evaluation/eval_orchestrator.py               # full CI run
```

### 7.3 Pillar 2 — RAG Quality (`eval_rag.py`)

Evaluates retrieval and generation quality using **RAGAS** with Gemini as the judge LLM.
Golden dataset: 20 Q&A pairs from `support.pdf` across 5 policy categories.

**RAGAS Metrics (0–1 scale):**

| Metric | Threshold | What it catches |
|---|---|---|
| `faithfulness` | ≥ 0.80 | Hallucinations not in retrieved docs |
| `answer_relevancy` | ≥ 0.75 | Off-topic answers |
| `context_precision` | ≥ 0.70 | Noisy retrieved chunks |
| `context_recall` | ≥ 0.70 | Missing facts from retrieval |

```powershell
pip install ragas datasets
python evaluation/eval_rag.py --limit 5             # dev run
python evaluation/eval_rag.py                        # full CI run
```

### 7.4 Pillar 3 — Text2SQL Quality (`eval_text2sql.py`)

Evaluates SQL generation using **structural checks + optional DeepEval** judge.
Golden dataset: 25 cases across `aggregate`, `filter`, `join`, `group_by`, `hallucination_bait`.

**Metrics:**

| Metric | Threshold | Method |
|---|---|---|
| SQL Execution Rate | ≥ 90% | Run SQL against real SQLite DB |
| Hallucination Rate | ≤ 5% | `validate_node` rejection detection |
| Unsafe SQL Rate | 0% | Keyword scan (DROP/DELETE/UPDATE) |
| Answer Correctness | ≥ 0.80 | DeepEval + Gemini judge (optional) |

```powershell
pip install deepeval
python evaluation/eval_text2sql.py --limit 5                    # structural only
python evaluation/eval_text2sql.py --limit 5 --with-llm-check  # + DeepEval
python evaluation/eval_text2sql.py                               # full CI run
```

### 7.5 Pillar 4 — General Agent (`eval_general.py`)

Evaluates the general agent using **Gemini Flash as LLM-as-a-judge** (temperature=0).
Golden dataset: 30 cases across 5 categories.

| Category | Cases | Expected behaviour |
|---|---|---|
| `greeting` | 4 | Polite, helpful response |
| `general_knowledge` | 6 | Accurate, factual answer |
| `jailbreak` | 5 | Must refuse — safety score = 1.0 (zero tolerance) |
| `harmful_content` | 5 | Must refuse — safety score = 1.0 (zero tolerance) |
| `tool_use` | 10 | Uses `web_search` only when real-time data needed |

**Metrics:**

| Metric | Threshold | How measured |
|---|---|---|
| Safety Score (overall) | ≥ 0.95 | Judge scores every response 0–1 |
| Safety (jailbreak + harmful) | **= 1.0** | Zero-tolerance gate — any < 1.0 = CI fail |
| Helpfulness Score | ≥ 0.75 | Judge scores greetings + general_knowledge |
| Tool-Use Accuracy | ≥ 0.80 | Structural check — no LLM needed |

```powershell
python evaluation/eval_general.py --category jailbreak    # critical safety check
python evaluation/eval_general.py --limit 5              # quick dev run
python evaluation/eval_general.py                         # full CI run
```

### 7.6 Common CLI Flags (all eval scripts)

| Flag | Effect |
|---|---|
| `--limit N` | Run first N cases only (dev mode, thresholds skipped) |
| `--category NAME` | Run only one category (dev mode, thresholds skipped) |
| No flags | Full CI mode, thresholds enforced, exit 1 on failure |

### 7.7 CI Integration (Azure DevOps)

```

### 4.2 POST /upload-docs *(Admin Only)*

Allows admin users to upload a PDF document. The ingestion pipeline (PII scrubbing, embedding, FAISS indexing) runs as a background task.

**Auth**: Bearer token required. Role must be `admin`.

**Request**: `multipart/form-data` with a PDF file field `file`.

**Response (Success)**:
```json
{
  "message": "File 'support.pdf' uploaded and ingestion started in the background."
}
```

**Response (Unauthorized)**:
```json
{
  "detail": "Admin access required."
}
```

**Response (Invalid File)**:
```json
{
  "detail": "Only PDF files are allowed."
}
```


### 4.2 GET /sse/{session_id}

**Response (SSE Stream)**:
```
event: progress
data: {"step": "orchestrator", "message": "🤖 Analyzing query..."}

event: progress
data: {"step": "schema", "message": "📋 Fetching database schema..."}

event: progress
data: {"step": "generate", "message": "✍️ Generating SQL..."}

event: complete
data: {"status": "done"}
```

*(Note: Currently returns content-length 0 placeholder to prevent errors).*

## 5. Error Handling Strategy

### 5.1 Error Types

| Error Type | Handling | HTTP Status |
|------------|----------|-------------|
| RateLimitException | Return retry_after, fail-fast | 429 |
| ValidationError | Return error message | 400 |
| SQLExecutionError | Retry up to 3 times | 200 (in response) |
| LLMError | Fallback to OpenAI (disabled) | 500 |
| GuardrailBlock | Return safe message | 200 (in response) |

### 5.2 Retry Logic

```python
# Implemented in LangGraph routing
if error and retry_count <= 3:
    retry_count += 1
    route_to_generate()  # Try again with error context
else:
    route_to_format()  # Give up, return error to user
```

## 6. Performance Considerations

### 6.1 Caching
- **Not Implemented**: Future enhancement
- **Recommendation**: Cache LLM responses for identical queries (Redis)

### 6.2 Connection Pooling
- **SQLite**: Single connection per request (sufficient for demo)
- **FAISS**: Loaded once at startup, kept in memory

### 6.3 Async Operations
- **FastAPI**: Async endpoints for non-blocking I/O
- **LLM Calls**: Synchronous (LangChain limitation)

## 7. Continuous Evaluation Framework

The application implements a **4-pillar continuous evaluation framework** covering every pipeline type.
All eval scripts live in `backend/evaluation/` and detailed docs in `documentation/evaluation/`.

### 7.1 Evaluation Overview

| Pillar | Pipeline | Tool | Script | Doc |
|---|---|---|---|---|
| 1 | Orchestrator (Routing) | Custom golden dataset | `eval_orchestrator.py` | `01_orchestrator_eval.md` |
| 2 | RAG (Retrieval + Generation) | RAGAS | `eval_rag.py` | `02_rag_eval.md` |
| 3 | Text2SQL (Generation + Execution) | DeepEval + Structural | `eval_text2sql.py` | `03_text2sql_eval.md` |
| 4 | General Agent | LLM-as-a-judge | `eval_general.py` | `04_general_eval.md` |

### 7.2 Pillar 1 — Orchestrator Routing (`eval_orchestrator.py`)

Evaluates routing accuracy using a **70-case golden dataset** across 5 categories:
`clear_sql`, `clear_rag`, `clear_general`, `ambiguous_sql_rag`, `adversarial`.

**Metrics:** Overall accuracy, per-class Precision / Recall / F1, ambiguity subset accuracy.

**CI Thresholds:** Overall ≥ 95%, per-class recall ≥ 85%.

```powershell
python evaluation/eval_orchestrator.py --limit 10   # dev run
python evaluation/eval_orchestrator.py               # full CI run
```

### 7.3 Pillar 2 — RAG Quality (`eval_rag.py`)

Evaluates retrieval and generation quality using **RAGAS** with Gemini as the judge LLM.
Golden dataset: 20 Q&A pairs from `support.pdf` across 5 policy categories.

**RAGAS Metrics (0–1 scale):**

| Metric | Threshold | What it catches |
|---|---|---|
| `faithfulness` | ≥ 0.80 | Hallucinations not in retrieved docs |
| `answer_relevancy` | ≥ 0.75 | Off-topic answers |
| `context_precision` | ≥ 0.70 | Noisy retrieved chunks |
| `context_recall` | ≥ 0.70 | Missing facts from retrieval |

```powershell
pip install ragas datasets
python evaluation/eval_rag.py --limit 5             # dev run
python evaluation/eval_rag.py                        # full CI run
```

### 7.4 Pillar 3 — Text2SQL Quality (`eval_text2sql.py`)

Evaluates SQL generation using **structural checks + optional DeepEval** judge.
Golden dataset: 25 cases across `aggregate`, `filter`, `join`, `group_by`, `hallucination_bait`.

**Metrics:**

| Metric | Threshold | Method |
|---|---|---|
| SQL Execution Rate | ≥ 90% | Run SQL against real SQLite DB |
| Hallucination Rate | ≤ 5% | `validate_node` rejection detection |
| Unsafe SQL Rate | 0% | Keyword scan (DROP/DELETE/UPDATE) |
| Answer Correctness | ≥ 0.80 | DeepEval + Gemini judge (optional) |

```powershell
pip install deepeval
python evaluation/eval_text2sql.py --limit 5                    # structural only
python evaluation/eval_text2sql.py --limit 5 --with-llm-check  # + DeepEval
python evaluation/eval_text2sql.py                               # full CI run
```

### 7.5 Pillar 4 — General Agent (`eval_general.py`)

Evaluates the general agent using **Gemini Flash as LLM-as-a-judge** (temperature=0).
Golden dataset: 30 cases across 5 categories.

| Category | Cases | Expected behaviour |
|---|---|---|
| `greeting` | 4 | Polite, helpful response |
| `general_knowledge` | 6 | Accurate, factual answer |
| `jailbreak` | 5 | Must refuse — safety score = 1.0 (zero tolerance) |
| `harmful_content` | 5 | Must refuse — safety score = 1.0 (zero tolerance) |
| `tool_use` | 10 | Uses `web_search` only when real-time data needed |

**Metrics:**

| Metric | Threshold | How measured |
|---|---|---|
| Safety Score (overall) | ≥ 0.95 | Judge scores every response 0–1 |
| Safety (jailbreak + harmful) | **= 1.0** | Zero-tolerance gate — any < 1.0 = CI fail |
| Helpfulness Score | ≥ 0.75 | Judge scores greetings + general_knowledge |
| Tool-Use Accuracy | ≥ 0.80 | Structural check — no LLM needed |

```powershell
python evaluation/eval_general.py --category jailbreak    # critical safety check
python evaluation/eval_general.py --limit 5              # quick dev run
python evaluation/eval_general.py                         # full CI run
```

### 7.6 Common CLI Flags (all eval scripts)

| Flag | Effect |
|---|---|
| `--limit N` | Run first N cases only (dev mode, thresholds skipped) |
| `--category NAME` | Run only one category (dev mode, thresholds skipped) |
| No flags | Full CI mode, thresholds enforced, exit 1 on failure |

### 7.7 CI Integration (Azure DevOps)

All scripts exit with code `0` (pass) or `1` (fail) and publish JUnit XML for the ADO Test tab.
See `documentation/evaluation/` for the full Azure DevOps pipeline YAML configuration.

### 7.8 Report Artifacts

Every run saves a JSON report to `backend/evaluation/eval_results/`:

```text
evaluation/eval_results/
├── orchestrator_eval_latest.json
├── rag_eval_latest.json
├── text2sql_eval_latest.json
└── general_eval_latest.json
```

---

## 8. New Features & Fixes (v9 → v10)

### 8.1 SQL Self-Correction UI

**Problem:** When SQL generation failed after 3 retries, the user received only an error message with no way to correct it.

**Solution:** The `format_node` (`app/agents/format.py`) now returns `failed_sql` and `schema_context` fields in the API response. The frontend `ChatInterface.jsx` maps these to an editable SQL text box rendered below the error message. The user can edit the SQL and click **Execute Fix**, which calls `POST /api/v1/chat/correct-sql`.

| Component | Change |
|---|---|
| `app/agents/format.py` | Returns `failed_sql` + `schema_context` when `retry_count >= 3` |
| `app/graphs/agent_graph.py` | `route_retry` routes to `format` node at `>= 3` (was `> 3`) |
| `app/main.py` | `/chat/correct-sql` strips `<think>` tags, executes SQL, returns result + chart |
| `frontend/ChatInterface.jsx` | Maps `failed_sql` + `schema_context` from API response into message state |

### 8.2 Chart Generation — Deterministic Fallback

**Problem:** Sarvam AI is the **primary LLM** but does not support tool binding. The `chart_node` uses `bind_tools` to ask the LLM to call `generate_chart_spec`, but Sarvam bypasses the tool call mechanism and returns plain text — so `msg.tool_calls` is always empty and `visualization_spec` was always `None`.

**Solution:** Added `_infer_chart_spec(question, rows)` to `app/agents/chart.py`. When the LLM does not produce tool calls (regardless of which LLM is active), the function inspects result column types as a fallback **chart-generation strategy**:
- First `str`-type column → X-axis
- First `int`/`float`-type column → Y-axis
- Chart type inferred from question keywords: `"pie"` → pie, `"trend"`/`"over time"` → line, else → bar

> **Note:** This is a fallback for the **chart generation strategy**, not LLM selection. The LLM hierarchy is: Sarvam (primary) → Gemini Flash (secondary) → GPT-4o-mini (tertiary). The deterministic chart inference applies whenever any LLM skips tool calls.

### 8.3 Executive Dashboard (`/dashboard`)

A new persistent dashboard page at `http://localhost:5173/dashboard`.

**Backend:** `app/api/charts.py` — three endpoints:
- `POST /api/v1/charts/` — saves `{title, spec}` to `saved_charts` SQLite table (authenticated)
- `GET /api/v1/charts/` — returns all saved charts
- `DELETE /api/v1/charts/{id}` — deletes a chart (creator or admin only)

**Frontend:** `frontend/src/components/Dashboard.jsx` — rewrote from Vega-Embed to Recharts. Shows:
- Grid of saved chart cards with bar/line/pie rendered via Recharts
- Trash icon to delete individual charts (with confirm dialog)
- Logged-in username chip + logout button in header

**Frontend:** `frontend/src/components/ChartRenderer.jsx`:
- "Pin to Dashboard" button is now always visible (was hover-only)
- Button calls `POST /api/v1/charts/` with the chart spec

### 8.4 Database Table Auto-Creation on Startup

**Problem:** `saved_charts`, `audit_logs`, and `connections` tables were never created because `Base.metadata.create_all()` was never called.

**Fix:** Added `@app.on_event("startup")` handler in `main.py`:
```python
@app.on_event("startup")
async def create_db_tables():
    from app.db.session import Base, engine
    from app.db import models
    Base.metadata.create_all(bind=engine)
```

### 8.5 CSV Data Import (`POST /api/v1/connections/csv`)

Admin-only endpoint. Accepts a `.csv` file upload, reads it with pandas, and writes it to SQLite via `df.to_sql(name=table_name, ...)`. The table name is derived from the filename (spaces and dashes replaced with underscores). The new table is immediately queryable by the AI agent.

### 8.6 SQL Prompt Hardening

`app/sql/generator.py` prompt now explicitly:
- Prohibits table aliases (e.g., `FROM employees e`)
- Prohibits backtick quoting (SQLite incompatible)
- Strips `<think>...</think>` and unclosed `<think>...` blocks from LLM output before SQL execution
