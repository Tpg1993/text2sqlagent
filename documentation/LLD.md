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
│   │   └── init_db.py          # SQLite initialization
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
    4. Extract final response from state
    5. Return ChatResponse
    
    Error Handling:
    - RateLimitException → 429 with retry_after
    - General Exception → 500 with error message
    """
```

```python
@app.get("/sse/{session_id}")
async def sse_stream(session_id: str):
    """
    Server-Sent Events endpoint for real-time updates.
    
    Flow:
    1. Create EventSourceResponse
    2. Subscribe to SSE manager for session_id
    3. Stream progress events as they occur
    4. Close on completion or timeout
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

#### 2.4.2 PII Scrubber (`pii.py`)

```python
class PIIScrubber:
    def __init__(self):
        """Initialize Presidio engines."""
        self.analyzer = AnalyzerEngine()
        self.anonymizer = AnonymizerEngine()
        self.entities_to_detect = [
            "PHONE_NUMBER", "EMAIL_ADDRESS", "CREDIT_CARD",
            "US_SSN", "PERSON", "LOCATION", ...
        ]
    
    def scrub_text(self, text: str, language: str = "en") -> str:
        """
        Detect and anonymize PII.
        
        Logic:
        1. Analyze text with Presidio
        2. Get list of detected entities
        3. Anonymize with placeholder replacement
        4. Return scrubbed text
        
        Example:
            Input: "Call me at 555-0100"
            Output: "Call me at <PHONE_NUMBER>"
        """
        results = self.analyzer.analyze(
            text=text,
            entities=self.entities_to_detect,
            language=language
        )
        
        anonymized_result = self.anonymizer.anonymize(
            text=text,
            analyzer_results=results,
            operators={
                "DEFAULT": OperatorConfig("replace", {"new_value": "<{entity_type}>"})
            }
        )
        
        return anonymized_result.text
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

## 7. Testing Strategy

### 7.1 Unit Tests
- Test each agent node in isolation
- Mock LLM responses
- Test routing logic

### 7.2 Integration Tests
- Test full SQL flow end-to-end
- Test full RAG flow end-to-end
- Test guardrail blocking

### 7.3 E2E Tests
- Test via HTTP API
- Verify SSE events
- Test error scenarios
