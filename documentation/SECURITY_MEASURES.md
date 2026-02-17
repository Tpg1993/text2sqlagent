# Agentic Security Architecture - Implemented Measures

This document outlines the advanced security controls implemented in the Agentic RAG application to ensure production-grade safety, privacy, and reliability.

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
    *   **UPDATE**: SQL execution is now available to **all authenticated users** (admin and standard roles) to ensure core application functionality. Administrative checks are reserved for highly sensitive tables.
    *   `Retrieve` agent is the **only** one with `READ_VECTOR_DB` permission.
    *   If a low-privilege agent tries to perform a high-value action, it is blocked.

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
*   **Uses**: NeMo Guardrails response validation.
*   **Remediation**:
    *   The final response from the LLM is checked against safety policies.
    *   If the output contains PII or violates content policy, it is redacted or replaced with a standard fallback message.

---

## 4. Execution Safety (Safe Actuators)

### **Name: SQL Static Analysis**
*   **Prevents**: Destructive SQL Commands (`DROP`, `DELETE`, `ALTER`).
*   **Uses**: `validate_node` in [app/agents/validate.py](../backend/app/agents/validate.py).
*   **Remediation**:
    *   Before any SQL is executed, the generated string is parsed.
    *   Keywords like `DROP TABLE`, `DELETE FROM`, or `ALTER USER` trigger an instant validation failure.
    *   Only `SELECT` statements (Read-Only) are permitted by default.

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
