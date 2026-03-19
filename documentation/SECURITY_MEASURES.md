# Agentic Security Architecture - Implemented Measures

This document outlines the advanced security controls implemented in the Agentic RAG application to ensure production-grade safety, privacy, and reliability.

## Agent Roles, Permissions, and Boundaries


The following table summarizes all agent nodes, their assigned roles, permissions, and operational boundaries enforced by the RBAC system:

| Agent Name        | Role                | Permissions                | Operational Boundary / Description                                 |
|-------------------|---------------------|----------------------------|--------------------------------------------------------------------|
| orchestrator      | router              | ROUTE_REQUEST              | Routes requests; cannot execute queries or access data             |
| schema            | metadata_reader     | (none)                     | Fetches **role-filtered** schema (Semantic RBAC)                   |
| planner           | planner             | PLAN_QUERY                 | Can plan queries; no data access                                   |
| generate          | sql_writer          | GENERATE_SQL               | Can generate SQL strings; cannot execute them                      |
| validate          | security_audit      | VALIDATE_SQL               | AST-parses SQL; enforces SELECT-only and schema whitelist          |
| execute           | db_admin            | EXECUTE_SQL                | Sole executor; runs ABAC PDP check before every query              |
| evaluate          | auditor             | (none)                     | Checks result quality; no privileged actions                       |
| masking           | data_sanitizer      | (none)                     | Scrubs PII from SQL results before LLM sees them (DLP node)        |
| retrieve          | knowledge_seeker    | READ_VECTOR_DB             | Can access vector DB for RAG retrieval                             |
| rag_gen           | writer              | GENERATE_RAG_ANSWER        | Can generate RAG answers; cannot access DB directly                |
| chart             | analyst             | GENERATE_CHART             | Can generate data visualizations                                   |
| format            | frontend_interface  | FORMAT_RESPONSE            | Can format output for frontend                                     |
| retry             | logic               | (none)                     | Handles retry logic; no data access                                |
| approval_pending  | approval_router     | (none)                     | Used for HITL approval routing; no privileged actions              |
| general           | generalist          | (web_search)               | Handles general/external queries; only agent allowed to use web_search tool |


## Tool-to-Agent Binding and RBAC Enforcement

The following table defines which agents are allowed to use each tool, ensuring strict RBAC and least-privilege enforcement:

| Tool Name           | Purpose/Function                        | Agents Allowed to Use Tool         | Reason/Scope                                                      |
|---------------------|-----------------------------------------|------------------------------------|-------------------------------------------------------------------|
| list_tables         | List all DB tables                      | schema, generate, validate         | Only agents involved in query planning/generation/validation      |
| get_table_schema    | Get schema for a table                  | schema, generate, validate         | Only agents that need schema info for query generation/validation |
| get_sample_rows     | Get sample rows from a table            | generate, validate, execute        | Only agents that generate, validate, or execute SQL               |
| generate_chart_spec | Generate chart config for frontend      | chart                              | Only the chart agent should generate visualizations               |
| web_search          | Perform web search (DuckDuckGo)         | general                            | Only the general agent should access external web info            |

**Enforcement:**
- Each tool must be accessible only to the agent(s) whose role and permissions require it for their function.
- No agent should be able to invoke a tool outside its defined scope. This is enforced in the agent logic and RBAC system.

This mapping ensures strong separation of duties, minimizes risk, and aligns with production-grade security best practices.


## 1. Identity & Access Control (IAM)

### **Name: Unique Agent Identities**
*   **Prevents**: Identity Spoofing, Unauthorized Access.
*   **Uses**: `AgentIdentity` class in [app/utils/security.py](../backend/app/utils/security.py).
*   **Remediation**: Every agent node (`generate`, `execute`, `retrieve`) is assigned a cryptographic-like identity with a specific **Role** (e.g., `sql_writer`, `db_admin`) upon initialization. This strictly defines "Who is acting".

### **Name: Role-Based Access Control (RBAC)**
*   **Prevents**: Privilege Escalation, Lateral Movement.
*   **Uses**: `SecurityPolicy` class defining permissions per role.
*   **Remediation**:
    *   `Generate` agent can **only** write SQL (`GENERATE_SQL`), never execute it.
    *   `Execute` agent is the **only** one with `EXECUTE_SQL` permission.
    *   `Retrieve` agent is the **only** one with `READ_VECTOR_DB` permission.
    *   The new `masking` agent (`data_sanitizer` role) sits between execute and evaluate, with no special permissions beyond reading and writing safe result rows.
    *   If a low-privilege agent tries to perform a high-value action, it is blocked.

### **Name: Attribute-Based Access Control (ABAC)**
*   **Prevents**: Fine-grained unauthorized data access that RBAC cannot express.
*   **Uses**: `PolicyDecisionPoint` in [app/utils/abac.py](../backend/app/utils/abac.py).
*   **Remediation**:
    *   ABAC extends RBAC with **contextual** access decisions evaluated at execution time.
    *   Policies evaluate multiple attributes simultaneously: **Subject** (user role), **Resource** (table name), **Action** (`EXECUTE_SQL`), **Context** (approval status).
    *   The `execute_node` calls the PDP for every table referenced in the SQL. If any table is denied for the current user's role or context, the entire query is blocked before hitting the database.
    *   **Deny-first** evaluation: a single deny policy overrides any allow policies.
    *   **Example policies enforced**:
        - `user` role + `audit_logs` → **DENY**
        - `user` role + `users` table → **DENY**
        - `admin` role + any table → **ALLOW** (unless pending approval)
        - Any role + pending approval → **DENY** (must go through HITL first)

### **Name: Semantic RBAC (Dynamic Schema Injection)**
*   **Prevents**: LLM generating SQL for tables the user should not know exist.
*   **Uses**: `get_schema_for_role()` in [app/utils/schema_policy.py](../backend/app/utils/schema_policy.py).
*   **Remediation**:
    *   The `schema_node` no longer returns the full database schema to the LLM.
    *   It filters the schema based on the **user's JWT role** before injection into the LLM prompt.
    *   A `user` role only sees `sales`, `employees`, `departments` — sensitive tables like `users`, `audit_logs`, `pii_vault` are completely invisible to the LLM.
    *   An `admin` role sees `*` (all tables).
    *   Since the LLM cannot generate SQL for tables it doesn't know about, this is a proactive prevention layer before any validation or ABAC check runs.

### **Name: Tool-Level Authorization**
*   **Prevents**: Unauthorized Data Access via Tools.
*   **Uses**: `InjectedToolArg` for context propagation and strict checks within tool definitions.
*   **Remediation**:
    *   **Context Injection**: User roles (`admin`, `user`) are securely injected into the agent state via the chat endpoint for downstream permission checks.
    *   **SQL Tools**: Generic tool-level role barriers have been removed to allow the LLM to access metadata (schema/tables) for all users, shifting final enforcement to the `Execute` agent node.

---

## 2. Secure Cognitive Loop

### **Name: Security Middleware Interception**
*   **Prevents**: Bypass of Security Controls, "Shadow AI" execution.
*   **Uses**: `SecurityManager.enforce()` decorator in [app/graphs/agent_graph.py](../backend/app/graphs/agent_graph.py).
*   **Remediation**:
    *   Every single node execution in the graph is wrapped by the Security Manager.
    *   **Zero-Trust**: No code runs until the middleware verifies the agent's identity and checks its permissions against the policy.
    *   Any violation results in an immediate `SecurityException` and halt of execution.

### **Name: Context Injection & Auditability**
*   **Prevents**: Lack of Non-Repudiation (inability to prove who did what).
*   **Uses**: `AgentState` updates in [app/utils/state.py](../backend/app/utils/state.py).
*   **Remediation**:
    *   The middleware injects a `security_context` (containing `agent_id`, `role`, `permissions`) into the state for every step.
    *   This ensures that every action in the logs can be traced back to a specific, authorized agent identity.

---

## 3. Input/Output Safety

### **Name: Input Guardrails**
*   **Prevents**: Prompt Injection, Jailbreaking, Harmful Content.
*   **Uses**: NeMo Guardrails ([app/utils/guardrails.py](../backend/app/utils/guardrails.py), [config/rails/prompts.yml](../backend/config/rails/prompts.yml)).
*   **Remediation**:
    *   User input is scanned for jailbreak attempts *before* it reaches the Orchestrator.
    *   Restricted topics or malicious patterns are blocked immediately with a 400 Bad Request or a standard refusal message.

### **Name: Output Guardrails**
*   **Prevents**: Data Leakage, Hallucination, Toxic Output.
*   **Uses**: NeMo Guardrails response validation + Two-Way PII De-anonymization.
*   **Remediation**:
    *   The final response from the LLM is checked against safety policies.
    *   If the output violates content policy, it is replaced with a standard fallback message.
    *   **PII De-anonymization**: The `deanonymize_text()` function in `vault.py` is applied to every response before it is sent to the user. It replaces secure `[PII_ENTITY_xxxxxxxx]` tokens with the original PII values that were stored in the vault at ingestion time, restoring the data correctly and securely only at the final output boundary.

### **Name: Two-Way PII Tokenization System**
*   **Prevents**: PII Exposure in Vector Database, LLM Training Data Leakage, PII Leaking into LLM prompts via SQL results.
*   **Uses**: `PIIScrubber` in [app/utils/pii.py](../backend/app/utils/pii.py) + `PII Vault` in [app/db/vault.py](../backend/app/db/vault.py) + `masking_node` in [app/agents/masking.py](../backend/app/agents/masking.py).
*   **Remediation**:
    *   **At Ingestion (Upload Time)**: Every PDF document is processed by the `PIIScrubber`. Detected PII (emails, phone numbers, names, etc.) is replaced with unique, opaque tokens e.g. `[PII_EMAIL_ADDRESS_a1b2c3d4]`. The original values are stored in a secure SQLite `pii_vault` table. Only the tokenized text is embedded into FAISS.
    *   **At SQL Execution (NEW)**: After `execute_node` returns raw database rows, the new `masking_node` (placed between `execute` and `evaluate` in the graph) runs every string column value through `scrub_text()`. PII found in live database rows is tokenized using the same vault system before the LLM ever sees the data for formatting.
    *   **Custom Detection**: A custom `PatternRecognizer` extends Presidio to detect alphanumeric phone numbers such as `1-800-COMPANY` which the default model misses.
    *   **At Query Time (Chat Response)**: After the LLM generates its answer (using only tokenized context), `deanonymize_text()` in `main.py` scans the final response text AND data rows for `[PII_...]` tokens and swaps them back to original values before the UI receives the response.
    *   **Token Safety**: Tokens use `[...]` bracket notation (not `<...>`) to prevent them from being silently swallowed by HTML parsers in the browser as invisible DOM elements.

---

## 4. Execution Safety (Safe Actuators)

### **Name: SQL AST Validation (sqlglot)**
*   **Prevents**: Destructive SQL Commands, Multi-statement Injection, Subquery/CTE Table Hiding.
*   **Uses**: `validate_node` in [app/agents/validate.py](../backend/app/agents/validate.py) via `sqlglot`.
*   **Remediation**:
    *   The generated SQL is **parsed into an Abstract Syntax Tree (AST)** using `sqlglot`.
    *   **Root-node enforcement**: If the root AST node is not a `Select` expression (e.g., `DROP`, `INSERT`, `UPDATE`), the query is rejected outright. This is unfakeable — SQL comments or obfuscated keywords cannot change the AST root.
    *   **Full tree traversal**: All `Table` references are extracted by traversing the complete AST, including those inside subqueries (`FROM (SELECT * FROM users)`) and CTEs (`WITH secret AS (SELECT * FROM users)`). The old regex approach (`FROM/JOIN` lookbehind) missed these.
    *   **Multi-statement injection blocked**: Queries with more than one statement (e.g., `SELECT 1; DROP TABLE users`) are rejected immediately — `sqlglot.parse()` returns a list and len > 1 is caught.
    *   **Graceful degradation**: If `sqlglot` is not installed, a legacy regex-based validator runs as a fallback with a logged warning.

### **Name: SQL Input Sanitization (Whitelisting)**
*   **Prevents**: SQL Injection via Tool Arguments, "Hallucinated" Table Names.
*   **Uses**: Runtime Schema Validation in [app/tools/sql_tools.py](../backend/app/tools/sql_tools.py).
*   **Remediation**:
    *   Before any tool execution (`get_schema`, `sample_rows`), the input `table_name` is validated against the **actual** database table list.
    *   Invalid tables are rejected immediately, preventing injection attacks and driver errors.

### **Name: Deterministic Graph Flow**
*   **Prevents**: Logic Corruption, "Tool-Use" Hallucinations.
*   **Uses**: `LangGraph` StateGraph definition.
*   **Remediation**:
    *   The application does *not* rely on the LLM to decide which tool to call next (which is prone to error).
    *   The flow is hardcoded: `Orchestrator -> Generate -> Validate -> Execute`.
    *   This forces the LLM to stay on the "Happy Path" and prevents it from skipping validation steps.

---

## 5. Infrastructure Protection

### **Name: API Rate Limiting**
*   **Prevents**: Denial of Service (DoS), Resource Exhaustion.
*   **Uses**: Custom Rate Limit middleware in [app/main.py](../backend/app/main.py).
*   **Remediation**:
    *   Tracks requests per user/IP. (Note: Currently disabled on main chat endpoint to resolve response middleware conflicts).
    *   If limits are exceeded, returns a `429 Too Many Requests` status with a `Retry-After` header, protecting the backend from being overwhelmed.

### **Name: SSRF Firewall (Web Search)**
*   **Prevents**: Internal Network Scanning, Metadata Access.
*   **Uses**: Regex Validator in [app/tools/search_tools.py](../backend/app/tools/search_tools.py).
*   **Remediation**:
    *   Blocks search queries containing: `localhost`, `127.0.0.1`, `file://`, and Private IP ranges (`10.x`, `192.168.x`).
    *   Ensures the agent cannot be used as a proxy to attack internal infrastructure.

### **Name: Ephemeral State Isolation**
*   **Prevents**: Session Hijacking, Cross-User Data Leakage.
*   **Uses**: Per-request `AgentState` instantiation.
*   **Remediation**:
    *   State is created fresh for every request.
    *   No shared global variables for user data.
    *   Memory is strictly typed (`TypedDict`) to prevent schema corruption.

---

## 6. Memory & State Protection

### **Name: Ephemeral State Isolation**
*   **Prevents**: Session Hijacking, Cross-User Data Leakage, long-term memory corruption.
*   **Uses**: Per-request `AgentState` instantiation in [app/main.py](../backend/app/main.py) and `LangGraph`.
*   **Remediation**:
    *   State is created fresh for **every single request**.
    *   No shared global variables or persistent memory structures that can be corrupted across sessions.
    *   Memory is strictly typed (`TypedDict`) to prevent schema corruption or "parameter pollution" attacks.

### **Name: Immutable History (Append-Only)**
*   **Prevents**: History Tampering by Hallucinating Agents.
*   **Uses**: `LangGraph` message handling.
*   **Remediation**:
    *   The message history `messages` is append-only for the duration of the request.
    *   Agents cannot rewrite past messages or inject fake user commands into the history.
