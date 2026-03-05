# Interview Q&A — Text2SQL & RAG Agentic System

This document contains interview questions and detailed answers for all aspects of the Text2SQL & RAG Agentic System. It is structured from **broad architectural questions** down to **deep technical dives**, covering every pillar of the solution.

---

## Table of Contents

1. [Traditional APIs vs Agentic APIs](#1-traditional-apis-vs-agentic-apis)
2. [System Overview & Architecture](#2-system-overview--architecture)
3. [LangGraph — State Machine & Orchestration](#3-langgraph--state-machine--orchestration)
4. [Text2SQL Pipeline](#4-text2sql-pipeline)
5. [RAG Pipeline](#5-rag-pipeline)
6. [Security — Guardrails, RBAC & Zero-Trust](#6-security--guardrails-rbac--zero-trust)
7. [PII Detection & Two-Way Tokenization](#7-pii-detection--two-way-tokenization)
8. [LLM Layer — Fallback & Rate Limiting](#8-llm-layer--fallback--rate-limiting)
9. [Evaluation Framework](#9-evaluation-framework)
10. [Observability & Reliability](#10-observability--reliability)
11. [Frontend & Real-Time Streaming](#11-frontend--real-time-streaming)
12. [Design Decisions & Trade-offs](#12-design-decisions--trade-offs)

---

## 1. Traditional APIs vs Agentic APIs

---

### Q1. What is the fundamental difference between a traditional REST API and the agentic API you deployed here?

**Answer:**

A **traditional REST API** is purely **reactive and deterministic in both flow AND logic**. It follows a fixed input→output contract: the client sends a request to a specific endpoint (e.g., `/get_sales`), the server executes hardcoded logic (e.g., `SELECT * FROM sales`), and returns a fixed structure. 

In our Agentic API, while the **graph structure (the flow) is deterministic** for security (e.g., Generate ALWAYS goes to Validate), the **logic within the nodes is generative and semantic**. 

| Dimension | Traditional API | Agentic API (This System) |
|---|---|---|
| **Routing** | URL-based routing (Explicit) | Semantic intent routing by LLM (Implicit) |
| **Logic / Execution** | Hardcoded code (e.g., ORM queries) | Generative (LLM writes the SQL query on-the-fly based on schema) |
| **State** | External state (DB/Redis). Request itself is stateless. | **Cognitive State** (`AgentState`) evolves step-by-step *during* the request. |
| **Error Handling** | Fails and returns 400/500 to client | **Self-correction**: Fails, catches error, asks LLM to fix it, and retries automatically. |
| **Data Extraction** | Relies on predefined parameters | Uses reasoning to extract arguments from unstructured natural language. |

**To summarize the nuance:** Yes, traditional APIs can have state and rate-limiting. But if a traditional API's database query fails, it just returns an error. When our Agentic API's query fails, the `retry_node` feeds the SQL error *back to the LLM* to reason about the mistake and generate a new query, all before the user ever sees a response. That self-correcting cognitive loop is what makes it "agentic".

---

### Q2. Why did you choose an agentic approach instead of a simple API that routes to `/sql` or `/rag` endpoints?

**Answer:**

A traditional routing approach (e.g., separate `/sql` and `/rag` endpoints) would require the **client** to know which endpoint to call — meaning the user would have to explicitly tag their query. That is a poor UX, especially for business users asking natural language questions.

The agentic approach offers:

1. **Semantic Intent Detection**: The LLM-based Orchestrator understands meaning, not syntax. "How many employees left last year?" correctly routes to SQL, while "What is the refund policy?" routes to RAG — without the user doing anything.

2. **Composability**: Steps are independent nodes. We can add a new agent (e.g., a "Planner" for complex multi-step queries) without rewriting the routing logic.

3. **Self-Correction via Retry Loop**: If the generated SQL fails validation, the agent retries with error context — something impossible in a traditional REST call.

4. **Security as a First-Class Citizen**: Input/output guardrails and RBAC are woven into the graph as mandatory nodes, not optional middleware bolted on after the fact.

---

### Q3. What are the risks or downsides of an agentic system compared to a traditional API?

**Answer:**

Agentic systems introduce unique challenges:

- **Latency**: Multiple LLM calls (orchestrator, generator, formatter) add up. Traditional APIs return in milliseconds; our system targets <5s for SQL queries.
- **Non-determinism**: The same question can produce different intents or SQL queries across requests. This makes testing harder.
- **Cost**: Each LLM call costs tokens. A single chat request may invoke 3–5 LLM calls.
- **Debuggability**: If the system fails, which node failed? LangGraph's OpenTelemetry tracing and SSE step-by-step events help here.
- **Prompt Injection Risk**: The LLM is now part of the execution path, making it an attack surface (e.g., "Ignore previous instructions"). We mitigate this with NeMo Guardrails and RBAC enforcement.
- **Tool Hallucination**: The agent could "hallucinate" table names. We mitigate this with SQL static analysis and schema whitelisting in the validate node.

The key engineering principle we applied: **minimize LLM autonomy, maximize structural determinism**. The LangGraph flow is hardcoded — the LLM classifies intent and generates queries, but it never decides what node to run next.

---

## 2. System Overview & Architecture

---

### Q4. Can you walk me through the high-level architecture of the system?

**Answer:**

The system has five layers:

1. **Client Layer**: React frontend with real-time Server-Sent Events (SSE) for progress visualization. Built with React 18 + Vite + TailwindCSS + Recharts.

2. **API Gateway**: FastAPI server exposing `/chat`, `/sse/{session_id}`, `/upload-docs`, and `/health`. Handles CORS, session management, and OpenTelemetry instrumentation.

3. **Security Layer**: NeMo Guardrails for input/output validation, Microsoft Presidio for PII detection, and a custom RBAC system enforced via a Security Manager decorator on every agent node.

4. **Orchestration & Processing Layer**: LangGraph state machine with intent classification routing to three pipelines:
   - **SQL Pipeline**: Schema → Generate → Validate → Execute → Evaluate → Chart → Format
   - **RAG Pipeline**: Retrieve (FAISS) → RAG Generate → Format
   - **General Pipeline**: Format (direct LLM response)

5. **Data Layer**: SQLite (business data with `employees`, `sales`, `departments`, `customers` tables) and FAISS vector store (PDF document embeddings using Google `text-embedding-004`).

LLM providers: Sarvam AI (primary) → Google Gemini 2.0 Flash (fallback) → OpenAI GPT-4o-mini (tertiary).

---

### Q5. Why did you use FastAPI instead of Flask or Django?

**Answer:**

- **Async-first**: FastAPI is built on `asyncio` and `Starlette`, allowing non-blocking I/O for SSE streams and concurrent requests without threads.
- **Auto-documentation**: Swagger UI (`/docs`) and ReDoc (`/redoc`) are auto-generated from Pydantic models — critical for stakeholder demos.
- **Type Safety**: Pydantic `BaseModel` for request/response schemas enforces contract validation at the boundary.
- **Performance**: FastAPI is one of the fastest Python frameworks (comparable to Go for I/O-bound workloads).
- **SSE Support**: Native support for `StreamingResponse` and async generators, enabling real-time agent step updates.

Flask would have required `flask-async` and manual OpenAPI definitions. Django would be too heavyweight for a microservice.

---

### Q6. What is `AgentState` and why is it a `TypedDict`?

**Answer:**

`AgentState` is the shared data structure that flows through every LangGraph node. It carries all context needed to process a query end-to-end:

```python
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    question: str
    intent: Optional[str]      # 'sql', 'rag', 'general', 'blocked'
    schema: Optional[str]
    sql_query: Optional[str]
    sql_result: Optional[Union[List[Dict], str]]
    sql_valid: bool
    error: Optional[str]
    visualization_spec: Optional[Dict]
    documents: Optional[List[Any]]
    rag_answer: Optional[str]
    retry_count: int
    session_id: Optional[str]
```

Using `TypedDict` instead of a regular `dict` provides:
- **Static type checking**: Mypy or Pyright catches mistakes at development time.
- **Schema enforcement**: Prevents ad-hoc keys from being silently added by hallucinating agents (mitigates "parameter pollution" attacks).
- **Documentation**: The state definition is self-documenting.

The `Annotated[List, operator.add]` on `messages` tells LangGraph to **append** to the messages list (reducer function) instead of overwriting it — enabling immutable append-only message history.

---

## 3. LangGraph — State Machine & Orchestration

---

### Q7. Why LangGraph over a simple Python if-else routing function?

**Answer:**

A simple if-else in Python would work for three routes, but LangGraph provides:

1. **Visual Explainability**: The graph can be rendered as a diagram, making it easy to explain to stakeholders what the system does.
2. **Retry Loops**: Implementing "go back to `generate` if `validate` fails, up to 3 times" with if-else requires manual state management. LangGraph's conditional edges handle this naturally.
3. **Parallel Nodes**: Future enhancement — nodes can run in parallel (e.g., fetch schema and validate guardrails simultaneously).
4. **Auditability**: Each node is a discrete, testable Python function. You can unit-test `validate_node` in isolation.
5. **OpenTelemetry Integration**: LangGraph auto-instruments spans for each node, giving us distributed traces per request.
6. **LangSmith Compatibility**: Integrates with LangSmith for production monitoring without code changes.

---

### Q8. Explain the routing logic — how does the system decide which pipeline to run?

**Answer:**

Routing happens via **conditional edge functions** in the LangGraph state machine. There are four routing decision points:

```
[input_guardrail] --route_input_guardrail--> [orchestrator] OR [format]
[orchestrator]    --route_orchestrator------> [schema] OR [retrieve] OR [format]
[validate]        --route_validate----------> [execute] OR [retry]
[evaluate]        --route_evaluate----------> [chart] OR [retry]
[retry]           --route_retry-------------> [generate] OR [format]
```

- **`route_input_guardrail`**: If `intent == 'blocked'`, skip to `format` with error. Otherwise, proceed.
- **`route_orchestrator`**: The Orchestrator LLM returns one of `['sql', 'rag', 'general']`. LangGraph maps this to the correct next node.
- **`route_validate`**: If `sql_valid == True`, go to `execute`. If `False`, go to `retry`.
- **`route_evaluate`**: If `error` exists in state, go to `retry`. Otherwise, generate chart.
- **`route_retry`**: If `retry_count > 3`, give up and go to `format`. Otherwise, go back to `generate` with error context.

This is entirely **LLM-free routing** (except the Orchestrator). All other decisions are based on Boolean state fields — deterministic and auditable.

---

### Q9. How does the SQL retry loop work in detail?

**Answer:**

The retry loop is a cycle in the LangGraph graph:

```
generate → validate → [invalid] → retry → [count <= 3] → generate (again)
                              → execute → evaluate → [error] → retry
```

**State changes on each retry iteration:**

1. `validate_node` sets `sql_valid = False` and populates `error`.
2. `retry_node` increments `retry_count`.
3. `route_retry` checks if `retry_count <= 3`. If so, routes back to `generate`.
4. `generate_node` now reads `error` from state and includes it in the prompt:

```
Previous error: near "FORM": syntax error
Fix the query.
```

5. The LLM receives the broken SQL + error message and attempts to correct it.

This is **error-driven self-correction** — the LLM learns from its own mistakes within the same request. If all 3 retries fail, `format_node` receives the last error and returns it gracefully to the user.

---

## 4. Text2SQL Pipeline

---

### Q10. Walk me through the complete SQL pipeline from a user question to a chart.

**Answer:**

Given the question: *"Show me total sales by employee for Q1 2024"*

1. **Schema Node** (`schema.py`): Queries SQLite's `sqlite_master` to fetch CREATE TABLE statements for all tables. Returns the schema string to state.

2. **Generate Node** (`generate.py`): Calls LLM with prompt: `[Schema] + [Question] + [Error context if retry]`. Extracts SQL from the response, stripping markdown fences (` ```sql ... ``` `).

3. **Validate Node** (`validate.py`): Uses `sqlparse.parse()` to check syntax. Blocks any `DROP`, `DELETE`, `ALTER`, `UPDATE` statements (read-only enforcement).

4. **Execute Node** (`execute.py`): Opens a SQLite connection, runs the query with `cursor.execute()`, fetches all rows, converts to `List[Dict]`. Catches `sqlite3.Error` for retry.

5. **Evaluate Node** (`evaluate.py`): Checks if result is non-empty and reasonable. Sets `error` if suspicious.

6. **Chart Node** (`chart.py`): Inspects column types. For 2 columns (1 categorical, 1 numeric), generates a Vega-Lite bar chart spec. Returned in `visualization_spec`.

7. **Format Node** (`format.py`): Calls LLM to narrate the results and chart in plain English. Returns the final `answer`.

8. **Output Guardrail**: Validates the formatted response. If safe, the API returns `{answer, sql_query, sql_result, visualization_spec}`.

---

### Q11. How do you prevent SQL injection in your system?

**Answer:**

Multiple layers of defense:

1. **Read-Only Enforcement**: `validate_node` statically scans the generated SQL for `DROP`, `DELETE`, `ALTER`, `UPDATE`, `INSERT`, `TRUNCATE`. Only `SELECT` is allowed through.

2. **Schema Whitelisting**: Before any schema tool call, the `table_name` argument is validated against the actual list of tables in `sqlite_master`. A hallucinated table like `users_v2` is rejected immediately.

3. **LLM-Generated SQL as Prepared Statements (Conceptual)**: Since the LLM generates the full SQL string, we treat it as untrusted input and run it through `sqlparse` validation before execution. Future enhancement: use parameterized queries for any user-provided string values.

4. **Ephemeral Connections**: Each request opens and immediately closes a SQLite connection — no persistent connections that could be compromised.

5. **Input Guardrails**: NeMo Guardrails blocks prompt injection attempts before they even reach the SQL pipeline.

---

### Q12. What happens when the LLM generates a SQL query that references a table that doesn't exist?

**Answer:**

This is the **"hallucinated table" problem**. The system handles it at two levels:

- **Tool-Level**: The `get_table_schema` and `get_sample_rows` tools validate table names against the live database schema before executing. An unknown table raises an error immediately.

- **Execute-Level**: Even if validation passes syntactically, SQLite will throw `sqlite3.OperationalError: no such table: ...`. This error is caught in `execute_node`, placed into `state["error"]`, and triggers the retry loop. On the next generation attempt, the LLM receives: `Previous error: no such table: orders. Available tables: employees, sales, departments, customers.`

This combination of structural validation + retry-with-context makes the system self-correcting for this class of error.

---

### Q13. How does the chart generation work?

**Answer:**

The `chart_node` uses **heuristic column analysis** to determine the appropriate Vega-Lite chart type:

- **2 columns (1 string + 1 number)** → Horizontal or vertical bar chart
- **2 columns (both numbers)** → Scatter plot
- **1 column** → Count bar chart
- **3+ columns or complex types** → No chart (table display only)

A Vega-Lite JSON spec is generated with the SQL result embedded as inline data (`{"values": [...]}`). The React frontend renders this using the `vega-embed` library. Recharts is used as a fallback for simpler charts.

The chart spec is returned as `visualization_spec` in the API response and rendered client-side — the backend does not generate images, keeping the API stateless.

---

## 5. RAG Pipeline

---

### Q14. Explain how the RAG pipeline works end-to-end.

**Answer:**

**Ingestion (Offline):**
1. PDF is uploaded via `/upload-docs` (admin only).
2. `ingest.py` loads the PDF using `PyPDFLoader`.
3. Text is split into chunks (1000 chars, 200 overlap) using `RecursiveCharacterTextSplitter`.
4. Each chunk is passed through `PIIScrubber.scrub_text()` — PII replaced with tokens.
5. Tokenized chunks are embedded using Google `text-embedding-004`.
6. Embeddings stored in FAISS (`faiss_index/` directory).

**Query Time (Online):**
1. `rag_retrieve.py` converts the user's question into an embedding.
2. FAISS performs a cosine similarity search, returning the top `k=3` document chunks.
3. Retrieved chunks are placed into `state["documents"]`.
4. `rag_generate.py` calls LLM with prompt: `[Context Documents] + [Question]` → generates an answer strictly grounded in the retrieved context.
5. `format_node` polishes the answer.
6. `deanonymize_text()` restores PII tokens before returning to user.

---

### Q15. Why FAISS instead of a managed vector database like Pinecone?

**Answer:**

For the current scope (demo/POC), FAISS is optimal:

- **Zero cost**: No external API calls or subscriptions.
- **No network latency**: In-memory, loaded at startup.
- **Simplicity**: Single `FAISS.save_local()` / `FAISS.load_local()` call.
- **Sufficient scale**: Handles millions of vectors in memory.

For production at scale, the recommendation is to migrate to Pinecone or Weaviate:
- Persistent storage with no in-memory requirement
- Multi-tenancy support
- Built-in metadata filtering
- Horizontal scalability

This migration path is documented in the HLD under `6.2 Production (Recommended)`.

---

### Q16. What embedding model are you using and why?

**Answer:**

**Google `text-embedding-004`** is used for both document ingestion and query embedding.

Why:
- **High quality**: Consistently ranks in top tiers on the MTEB (Massive Text Embedding Benchmark).
- **Cost-effective**: Much cheaper than OpenAI `text-embedding-ada-002` with comparable quality.
- **Consistency**: Using the same model for ingestion and retrieval ensures the embedding space is identical — a critical requirement for cosine similarity to be meaningful.
- **Integration**: Since Gemini is the primary LLM, using Google embeddings keeps us within a single provider's rate limits and API key.

---

### Q17. How does the RAG system handle questions where the answer is not in the documents?

**Answer:**

The system has two defense layers:

1. **Prompt Grounding**: The RAG generator prompt explicitly instructs the LLM: *"Answer only based on the provided context. If the information is not in the context, say you don't know."* This reduces hallucination.

2. **Faithfulness Evaluation (CI)**: The RAGAS evaluation framework runs `faithfulness` scores on the golden dataset. Any answer that contradicts or goes beyond the retrieved context scores low on faithfulness. Our CI threshold is ≥ 0.80.

If `context_recall` is low (retrieved chunks don't contain the relevant facts), the system will still attempt to answer. A future enhancement is to add a "confidence score" node that returns "I couldn't find enough information in our documents" when retrieval similarity scores are below a threshold.

---

## 6. Security — Guardrails, RBAC & Zero-Trust

---

### Q18. How does NeMo Guardrails work in this system?

**Answer:**

NeMo Guardrails (by NVIDIA) is a framework for adding safety rails to LLM-based applications using a DSL called Colang. In this system it runs at two points:

**Input Guardrail (before Orchestrator):**
- Receives the raw user question.
- Runs it through configured `rails` (defined in `config/rails/config.yml` and `prompts.yml`).
- Checks for: jailbreak attempts, harmful content, off-topic queries, prompt injection patterns.
- If detected: sets `intent = 'blocked'` and short-circuits to `format_node` with a refusal message.
- **Fail-open design**: If NeMo itself errors, the request is **allowed through** (availability over security) — appropriate for a demo system.

**Output Guardrail (after pipelines):**
- Validates the LLM-generated response.
- Scans for harmful patterns, toxic content, unintended data exposure.
- If flagged: replaces the response with a safe fallback message.

---

### Q19. Explain the RBAC system and how it prevents privilege escalation.

**Answer:**

Each agent node has an assigned `AgentIdentity` with a specific **Role** and a set of **Permissions**:

| Agent | Role | Key Permission |
|---|---|---|
| `generate` | `sql_writer` | `GENERATE_SQL` |
| `execute` | `db_admin` | `EXECUTE_SQL` |
| `retrieve` | `knowledge_seeker` | `READ_VECTOR_DB` |
| `orchestrator` | `router` | `ROUTE_REQUEST` |

The `SecurityManager.enforce()` decorator wraps **every node function**. Before the node runs, it:
1. Reads the agent's identity and role from the global registry.
2. Checks the `SecurityPolicy` to verify the role has permission for the requested action.
3. If permission is missing: raises `SecurityException` and halts execution immediately.

**Key principle**: The `generate` agent can produce a SQL string but cannot execute it. The `execute` agent can run SQL but cannot generate it. This separation ensures that even if the LLM in `generate` is manipulated to produce a malicious query, it still cannot execute — because execution requires a different agent identity.

---

### Q20. What is the "Zero-Trust" model and how is it applied here?

**Answer:**

Zero-Trust means: **"Never trust, always verify"** — even internal components are not trusted by default.

In this system:
- Every node execution is intercepted by `SecurityManager.enforce()` — no code runs without identity verification.
- `AgentState` is a `TypedDict` — no runtime schema mutations allowed.
- Messages are append-only (`operator.add` reducer) — no agent can rewrite history to inject fake user commands.
- SQL validation rejects any query that isn't a pure `SELECT` — the database is never trusted to catch bad queries itself.
- SSRF firewall on web search blocks `localhost`, `127.0.0.1`, `file://`, and private IP ranges — the agent cannot use itself to scan internal infrastructure.
- Ephemeral state per request — cross-request data leakage is structurally impossible.

---

### Q21. What is "Deterministic Graph Flow" and why is it a security measure?

**Answer:**

In fully autonomous (ReAct-style) agents, the LLM itself decides what tool to call next, in what order, and with what arguments. This creates two risks:
1. **Tool-Use Hallucinations**: The LLM might call `execute_sql("DROP TABLE employees")` if manipulated.
2. **Step Skipping**: The LLM might skip the `validate` step and go directly to `execute`.

In this system, the LangGraph flow is **hardcoded**: `Orchestrator → Generate → Validate → Execute`. The LLM **cannot choose** to skip validation or call a tool out of sequence. It only generates content (SQL, answer text) — all control flow decisions are structural (Python code), not semantic (LLM decisions).

This is a key architectural security decision that makes the system auditable and resistant to prompt injection attacks that try to hijack the execution path.

---

## 7. PII Detection & Two-Way Tokenization

---

### Q22. Explain the Two-Way PII Tokenization system end-to-end.

**Answer:**

The system uses a **vault-based tokenization** approach rather than one-way redaction:

**At Ingestion (PDF Upload):**
1. `PIIScrubber.scrub_text()` runs Microsoft Presidio's `AnalyzerEngine` on each document chunk.
2. Detected PII entities (EMAIL, PHONE, NAME, LOCATION, SSN, etc.) are identified with their character spans.
3. Overlapping detections are resolved greedily (largest span wins) to prevent double-replacement.
4. For each detected entity, `store_pii(entity_type, original_value)` is called:
   - Generates a deterministic token: `[PII_EMAIL_ADDRESS_a1b2c3d4]`
   - Stores `{token: original_value}` in the `pii_vault` SQLite table.
   - If the same value has been seen before, returns the existing token (deduplication).
5. Original value in the text is replaced with the token.
6. **Only tokenized text is embedded into FAISS.**

**At Query Time (Chat Response):**
1. The LLM retrieves context from FAISS (which contains only tokens, not real PII).
2. The LLM generates an answer that may reference tokens (e.g., "Contact us at `[PII_EMAIL_ADDRESS_a1b2c3d4]`").
3. After the LLM responds, `deanonymize_text()` scans the response for `[PII_...]` patterns.
4. Each token is looked up in `pii_vault` and replaced with the original value.
5. The restored response is sent to the user.

**Net effect**: Real PII never enters the LLM's context window or the vector database. The LLM only sees tokens. Users see the real values in the final response.

---

### Q23. Why use bracket notation `[PII_...]` instead of angle brackets `<PII_...>`?

**Answer:**

HTML parsers in browsers interpret `<TAG>` as HTML tags. If the LLM response containing `<PII_EMAIL_ADDRESS_a1b2c3d4>` is rendered in a React component, the browser's HTML parser will silently **strip** the tag, treating it as an unknown HTML element. The token disappears and `deanonymize_text()` can't find it to restore the original value.

Bracket notation `[PII_EMAIL_ADDRESS_a1b2c3d4]` has no special meaning in HTML and is rendered as literal text, ensuring the regex in `deanonymize_text()` can always find and replace it.

---

### Q24. What custom PII detection capability did you add beyond Presidio's defaults?

**Answer:**

Presidio's default phone number recognizer only matches standard numeric phone formats (e.g., `555-123-4567`, `+1 (800) 555-1234`). It misses **vanity/alphanumeric phone numbers** like `1-800-COMPANY` or `800-GET-HELP`.

A custom `PatternRecognizer` was added:

```python
custom_phone_recognizer = PatternRecognizer(
    supported_entity="PHONE_NUMBER",
    name="alphanumeric_phone_recognizer",
    patterns=[Pattern(
        "alphanumeric_phone",
        r"\b1-[0-9]{3}-[A-Z0-9]{4,10}\b|\b[0-9]{3}-[A-Z0-9]{4,10}\b",
        0.8   # confidence score
    )]
)
self.analyzer.registry.add_recognizer(custom_phone_recognizer)
```

This is registered with Presidio's recognizer registry before document ingestion. The `0.8` confidence score means Presidio needs ≥80% confidence before treating the match as PII — preventing false positives on product codes that happen to match the pattern.

---

## 8. LLM Layer — Fallback & Rate Limiting

---

### Q25. Describe the LLM fallback chain and why it's designed this way.

**Answer:**

The LLM provider chain is:

```
Sarvam AI (sarvam-m) → Google Gemini 2.0 Flash → OpenAI GPT-4o-mini
```

**Design reasoning:**

- **Sarvam AI** is the primary because it's an Indian multilingual model with an OpenAI-compatible API — directly relevant for our target user base and a good showcase of multi-provider support.
- **Gemini 2.0 Flash** is the reliable secondary — fast, cheap, excellent reasoning, same provider as our embeddings (reducing API key complexity).
- **OpenAI GPT-4o-mini** is the emergency tertiary fallback — universal availability guarantees the system stays up even if both primary providers are down.

The `invoke_chain_with_fallback()` function in `llm.py` tries each provider in sequence. Any non-rate-limit error causes a silent fallback to the next provider. Rate limit errors (HTTP 429 / `RESOURCE_EXHAUSTED`) are **fail-fast**: a `RateLimitException` is raised immediately with a `retry_after` value extracted from the error message, and the user is told to wait rather than burning more quota on fallbacks.

---

### Q26. How does the system handle LLM rate limits?

**Answer:**

The rate limit handling has three parts:

1. **Detection**: The `invoke_chain_with_fallback()` function catches exceptions and checks for `"429"` or `"RESOURCE_EXHAUSTED"` in the error string.

2. **Extraction**: A regex parses the error message to extract the `retry_after` value (e.g., `"Please try again in 60 seconds"` → `retry_after = 60`).

3. **Propagation**: A custom `RateLimitException` is raised:
   ```python
   raise RateLimitException(
       message=f"Rate limit exceeded. Wait {retry_after}s",
       retry_after=retry_after
   )
   ```
   FastAPI catches this and returns HTTP 429 with headers: `{"detail": "...", "retry_after": "60"}`.

4. **Frontend**: The React UI reads `retry_after` from the 429 response and displays a countdown timer to the user: *"Rate limited. Please try again in 60s"*.

This is a **fail-fast** strategy — rather than retrying automatically (burning more quota), we surface the wait time to the user and let them decide.

---

## 9. Evaluation Framework

---

### Q27. Describe the 4-pillar evaluation framework.

**Answer:**

The evaluation framework covers every pipeline type with a dedicated eval script:

| Pillar | Pipeline | Tool | Key Metric | CI Threshold |
|---|---|---|---|---|
| 1 - Orchestrator | Routing accuracy | Golden dataset (70 cases) | Per-class F1 | ≥95% overall, ≥85% per class |
| 2 - RAG | Retrieval + Generation | RAGAS | Faithfulness, Answer Relevancy | ≥0.80 faithfulness, ≥0.75 relevancy |
| 3 - Text2SQL | SQL generation + execution | DeepEval + Structural | Execution Rate, Unsafe SQL Rate | ≥90% execution, 0% unsafe |
| 4 - General | General responses | LLM-as-a-judge (Gemini) | Safety score, Helpfulness | 0% harmful, ≥80% helpful |

**How RAGAS works**: It uses Gemini as a judge LLM to evaluate four dimensions:
- `faithfulness`: Is the answer faithful to the retrieved documents? (Catches hallucinations)
- `answer_relevancy`: Is the answer actually answering the question? (Catches off-topic responses)
- `context_precision`: Are the retrieved chunks relevant? (Catches noise in retrieval)
- `context_recall`: Do the retrieved chunks contain the answer? (Catches missing facts)

**How orchestrator eval works**: A golden dataset of 70 questions with known correct intents is run through the live system. Precision, Recall, and F1 are computed per class (`sql`, `rag`, `general`, `adversarial`, `ambiguous`).

---

### Q28. How do you prevent the evaluation from becoming a "gaming the benchmark" problem?

**Answer:**

Several design choices prevent overfitting to the golden dataset:

1. **Diverse adversarial cases**: The golden datasets include adversarial, ambiguous, and edge cases — not just happy paths. For orchestrator: `adversarial` and `ambiguous_sql_rag` categories. For Text2SQL: `hallucination_bait` cases.

2. **Structural metrics over LLM-judge-only**: The Text2SQL eval runs actual SQL against the live database and checks execution success — this cannot be gamed by prompt tuning.

3. **Zero-tolerance thresholds**: `unsafe_sql_rate = 0%` means a single `DROP TABLE` in the golden dataset causes the entire pipeline to fail CI. This creates a hard floor.

4. **Separate judge LLM**: The LLM-as-a-judge in `eval_general.py` uses Gemini Flash but evaluates responses from the full pipeline — it's not evaluating itself.

5. **Golden datasets are version-controlled**: Changes to golden datasets are code reviews, preventing silent drift.

---

## 10. Observability & Reliability

---

### Q29. How do you monitor what's happening inside the agent at runtime?

**Answer:**

Three observability layers:

1. **OpenTelemetry Tracing**: Every agent node is instrumented with OTel spans. This captures:
   - Node name and start/end timestamps
   - Input state (question, intent, etc.)
   - Output state changes
   - Errors
   Traces can be exported to Jaeger, Zipkin, or LangSmith.

2. **Server-Sent Events (SSE)**: The `/sse/{session_id}` endpoint streams real-time progress events to the frontend as each node completes:
   ```
   event: progress
   data: {"step": "generate", "message": "✍️ Generating SQL..."}
   ```
   Users see a live step-by-step visualization of what the agent is doing.

3. **Structured Logging**: Python's standard `logging` module with structured JSON output. Each log entry includes `session_id`, `node_name`, `question` (truncated for privacy), and error details.

For production, the recommendation is LangSmith (native LangChain/LangGraph integration) or Datadog for centralized log aggregation and alerting.

---

### Q30. What happens if the SQLite database is unavailable?

**Answer:**

The failure propagates gracefully:

1. `execute_node` attempts `sqlite3.connect()` → raises `sqlite3.OperationalError`.
2. The exception is caught, and `state["error"]` is set with the message.
3. `route_evaluate` sees the error → routes to `retry`.
4. `retry_node` increments `retry_count`.
5. Since reconnecting won't fix an unavailable database, all 3 retries fail with the same error.
6. After 3 retries, `route_retry` → `format_node` with message: *"I encountered a database connection error. Please try again later."*

**Improvement**: A future enhancement is a dedicated health check in `execute_node` that detects `sqlite3.OperationalError: unable to open database file` and short-circuits the retry loop (since retrying can't fix infrastructure unavailability).

---

## 11. Frontend & Real-Time Streaming

---

### Q31. How does the real-time agent step visualization work?

**Answer:**

The frontend uses the **EventSource API** (Server-Sent Events) to receive real-time updates:

**Backend flow:**
1. `/chat` creates a `session_id` and enqueues agent states to `SSEManager` as each LangGraph node completes.
2. `/sse/{session_id}` opens an async generator that reads from the session's queue and yields SSE-formatted events:
   ```
   event: progress
   data: {"step": "orchestrator", "message": "🤖 Analyzing query..."}
   ```

**Frontend flow:**
1. React sends `POST /chat` to start the request.
2. Simultaneously opens `new EventSource('/sse/{session_id}')`.
3. `onmessage` handler updates a `steps` array in React state.
4. Each step renders as an animated list item showing which nodes have completed.
5. When `event: complete` is received, the EventSource is closed.

This gives users visual feedback that the system is "thinking" and showing exactly which step it's on — particularly useful for SQL queries that take 3–5 seconds.

---

### Q32. Why SSE (Server-Sent Events) instead of WebSockets?

**Answer:**

| | SSE | WebSockets |
|---|---|---|
| **Direction** | Server → Client (unidirectional) | Bidirectional |
| **Protocol** | HTTP/1.1 | TCP upgrade |
| **Browser support** | Native `EventSource` API | Requires library |
| **Reconnection** | Automatic (built-in) | Manual |
| **Firewalls/Proxies** | Generally allowed | Often blocked |
| **Use case** | Real-time push notifications | Real-time chat/games |

For this use case (streaming agent progress to the browser), SSE is the right choice:
- We only need **server → client** communication (no user input once the query is submitted).
- SSE is simpler, uses standard HTTP, and auto-reconnects on drops.
- No special proxy/firewall configuration needed.

WebSockets would be appropriate if the user needed to cancel an in-flight query or provide live corrections to the agent.

---

## 12. Design Decisions & Trade-offs

---

### Q33. Why SQLite instead of PostgreSQL for the business database?

**Answer:**

SQLite was chosen for this stage for pragmatic reasons:

**Advantages:**
- **Zero setup**: File-based, no database server to install or manage.
- **Fast for demos**: No network round-trips.
- **Portable**: The `business.db` file can be committed to git and shared.
- **Full SQL compatibility**: All standard SQL features work identically in PostgreSQL.

**Limitations (and migration path):**
- **No concurrent writes**: SQLite locks on write. For multi-user production, PostgreSQL is required.
- **No managed backups**: Must be handled manually.
- **No connection pooling**: Using a new connection per request.

The production migration path is documented: swap `sqlite3` for `asyncpg` (async PostgreSQL driver), update `DATABASE_URL`, and the schema is identical.

---

### Q34. How would you scale this system to 1,000 concurrent users?

**Answer:**

Current bottlenecks and solutions:

1. **LLM Throughput**: The biggest bottleneck. Solution: Implement semantic caching (Redis + similarity search — cache LLM responses for semantically identical questions). Also: deploy multiple API keys and round-robin requests.

2. **FastAPI Scaling**: The API is stateless (state lives in `AgentState` per request). Horizontal scaling with Docker + Kubernetes is straightforward. Add a load balancer (Nginx, AWS ALB).

3. **FAISS**: Loaded in-memory at startup. With multiple replicas, each replica holds its own copy. For true scalability, migrate to Pinecone (hosted, replicated, with metadata filtering).

4. **SQLite → PostgreSQL**: Replace with PostgreSQL + connection pool (PgBouncer, asyncpg connection pool). Add read replicas for SQL queries.

5. **Rate Limiting**: Enable the Redis-backed rate limiter (currently stubbed) to prevent individual users from exhausting LLM quota.

6. **Async LLM Calls**: Current LLM calls are synchronous (LangChain limitation). Migrate to async LLM clients (`google-genai` async) to improve FastAPI's concurrency.

---

### Q35. What improvements would you make for a production deployment?

**Answer:**

Immediate (must-have for production):
- **JWT Authentication**: The `/chat` endpoint currently has no user authentication. Add JWT/OAuth2 with role injection (`admin` vs `user`).
- **Rate Limiting**: Enable Redis-backed rate limiting per user/IP.
- **HTTPS**: Deploy behind a TLS-terminating load balancer.
- **Secret Management**: Move API keys from `.env` to AWS Secrets Manager / HashiCorp Vault.
- **Database Migration**: SQLite → PostgreSQL + connection pooling.

Medium-term (significant value adds):
- **Conversation Memory**: Add a `conversation_history` table so the agent remembers prior turns within a session.
- **Caching Layer**: Redis cache for identical SQL results and LLM responses.
- **Vector DB Migration**: FAISS → Pinecone/Weaviate for persistent, scalable storage.
- **CI/CD Pipeline**: Automate evaluation suite on every PR — fail builds if accuracy drops below threshold.

Long-term:
- **Multi-database Support**: Connect to PostgreSQL, Snowflake, BigQuery via configurable connectors.
- **Fine-tuned Model**: Fine-tune a smaller model specifically on our SQL schema for lower cost and latency.
- **Multi-turn Agent Conversations**: Allow follow-up questions like "Show me only Q1 from that" without restating the full context.

---

### Q36. What was the hardest engineering challenge in building this system?

**Answer:**

The hardest challenge was **the Two-Way PII Tokenization system** — specifically ensuring that:

1. **Tokens survive the LLM round-trip**: LLMs sometimes paraphrase or slightly alter text. A token like `[PII_EMAIL_ADDRESS_a1b2c3d4]` must appear verbatim in the LLM's output for `deanonymize_text()` to find it. Prompt engineering was needed to instruct the model not to alter quoted values.

2. **HTML rendering doesn't destroy tokens**: Switching from `<TAG>` to `[bracket]` notation was a non-obvious fix discovered during frontend testing.

3. **Overlapping PII entity spans**: Presidio can detect the same text as both a `PERSON` and a `LOCATION` (e.g., "Florence" as a person's name vs. a city). A greedy deduplication algorithm (largest span wins) was implemented to prevent double-tokenization.

4. **Deterministic de-duplication**: The same email appearing in multiple documents should map to the same token to keep the vault small and avoid confusion. The `store_pii()` function checks for existing token before creating a new one.

A close second was **the SSE + async state management** — ensuring that agent nodes push progress events to the correct session's queue without race conditions in an async FastAPI environment.

---

### Q37. In a multi-agent system, how do you manage prompt updates so you don't have to redeploy the entire codebase every time a prompt changes?

**Answer:**

Hardcoding prompts as Python string constants inside agent files (e.g., `ORCHESTRATOR_PROMPT = "..."`) is an anti-pattern for production because any prompt tweak requires a code review and a full system redeploy.

To solve this, we implement a **Prompt Library Architecture**:

1. **Externalization**: Prompts are moved out of `.py` files and into version-controlled YAML files (e.g., `prompts/orchestrator.yaml`, `prompts/rag_generate.yaml`). The YAML contains the prompt text and metadata (version, author).
2. **Prompt Registry**: A singleton `PromptRegistry` class loads these YAML files at application startup. Agents fetch their templates via `PromptRegistry.get("orchestrator")`. The agent code becomes completely prompt-agnostic.
3. **Selective Deployment (CI/CD)**: In our GitHub Actions pipeline, we detect which specific YAML file changed using `git diff`. If `orchestrator.yaml` changes, the pipeline **only** rebuilds and restarts the Orchestrator container, leaving the RAG and SQL agents untouched.

For highly dynamic environments, this can be taken a step further by storing prompts in Redis or LangSmith Hub, allowing for **zero-downtime hot-reloads** and A/B testing of prompts without touching the CI/CD pipeline at all.

---

*End of Interview Q&A — Good luck with your interview!* 🎯
