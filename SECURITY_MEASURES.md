# Agentic Security Architecture - Implemented Measures

This document outlines the advanced security controls implemented in the Agentic RAG application to ensure production-grade safety, privacy, and reliability.

## 1. Identity & Access Control (IAM)

### **Name: Unique Agent Identities**
*   **Prevents**: Identity Spoofing, Unauthorized Access.
*   **Uses**: `AgentIdentity` class in `app/utils/security.py`.
*   **Remediation**: Every agent node (`generate`, `execute`, `retrieve`) is assigned a cryptographic-like identity with a specific **Role** (e.g., `sql_writer`, `db_admin`) upon initialization. This strictly defines "Who is acting".

### **Name: Role-Based Access Control (RBAC)**
*   **Prevents**: Privilege Escalation, Lateral Movement.
*   **Uses**: `SecurityPolicy` class defining permissions per role.
*   **Remediation**:
    *   `Generate` agent can **only** write SQL (`GENERATE_SQL`), never execute it.
    *   `Execute` agent is the **only** one with `EXECUTE_SQL` permission.
    *   `Retrieve` agent is the **only** one with `READ_VECTOR_DB` permission.
    *   If a low-privilege agent tries to perform a high-value action, it is blocked.

---

## 2. Secure Cognitive Loop

### **Name: Security Middleware Interception**
*   **Prevents**: Bypass of Security Controls, "Shadow AI" execution.
*   **Uses**: `SecurityManager.enforce()` decorator in `app/graphs/agent_graph.py`.
*   **Remediation**:
    *   Every single node execution in the graph is wrapped by the Security Manager.
    *   **Zero-Trust**: No code runs until the middleware verifies the agent's identity and checks its permissions against the policy.
    *   Any violation results in an immediate `SecurityException` and halt of execution.

### **Name: Context Injection & Auditability**
*   **Prevents**: Lack of Non-Repudiation (inability to prove who did what).
*   **Uses**: `AgentState` updates in `app/utils/state.py`.
*   **Remediation**:
    *   The middleware injects a `security_context` (containing `agent_id`, `role`, `permissions`) into the state for every step.
    *   This ensures that every action in the logs can be traced back to a specific, authorized agent identity.

---

## 3. Input/Output Safety

### **Name: Input Guardrails**
*   **Prevents**: Prompt Injection, Jailbreaking, Harmful Content.
*   **Uses**: NeMo Guardrails (`app/utils/guardrails.py`, `config/rails/prompts.yml`).
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
*   **Uses**: `validate_node` in `app/agents/validate.py`.
*   **Remediation**:
    *   Before any SQL is executed, the generated string is parsed.
    *   Keywords like `DROP TABLE`, `DELETE FROM`, or `ALTER USER` trigger an instant validation failure.
    *   Only `SELECT` statements (Read-Only) are permitted by default.

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
*   **Uses**: Custom Rate Limit middleware in `app/main.py`.
*   **Remediation**:
    *   Tracks requests per user/IP.
    *   If limits are exceeded, returns a `429 Too Many Requests` status with a `Retry-After` header, protecting the backend from being overwhelmed.

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
*   **Uses**: Per-request `AgentState` instantiation in `app/main.py` and `LangGraph`.
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

