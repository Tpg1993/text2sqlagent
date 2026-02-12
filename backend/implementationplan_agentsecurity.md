# Implementation Plan - Advanced Agentic Security

## Goal Description
Enhance the current Agentic RAG system with advanced security patterns inspired by Strata.io and Palo Alto Networks.
1.  **Unique Agent Identities & Least Privilege (Strata.io)**: Assign distinct identities to agents (Orchestrator vs. Generator) and enforce role-based access control (RBAC).
2.  **Securing the Agent Loop (Palo Alto Networks)**: Implement "hooks" or "interceptors" at each phase of the agent's cognitive loop (Perception, Reasoning, Planning, Execution) to validate actions against security policies.

## User Review Required
> [!IMPORTANT]
> This will introduce a new `SecurityManager` and modify the `AgentState` to carry `agent_id` and `permissions`.
> Existing agents will need to be updated to check permissions before acting.

## Proposed Changes

### Core Security Infrastructure

#### [NEW] [security.py](file:///c:/Users/Tejas/Downloads/APPS/text2sql%20rag/backend/app/utils/security.py)
- Define `AgentIdentity` class (ID, Role, Permissions).
- Define `SecurityPolicy` class.
- Implement `SecurityManager` to handle authentication and authorization of agents.
- Implement `SecureLoopMiddleware` to intercept agent steps.

### Graph & State Updates

#### [MODIFY] [state.py](file:///c:/Users/Tejas/Downloads/APPS/text2sql%20rag/backend/app/utils/state.py)
- Add `agent_identity: dict` to `AgentState`.
- Add `security_context: dict` to `AgentState` (for audit logs).

#### [MODIFY] [agent_graph.py](file:///c:/Users/Tejas/Downloads/APPS/text2sql%20rag/backend/app/graphs/agent_graph.py)
- Initialize `SecurityManager` at graph entry.
- Wrap nodes with `security_manager.enforce(node_func)` instead of just `trace_node`.

### Agent Updates (Least Privilege)

#### [MODIFY] [generate.py](file:///c:/Users/Tejas/Downloads/APPS/text2sql%20rag/backend/app/agents/generate.py)
- Check if current agent identity has `EXECUTE_SQL` permission.

#### [MODIFY] [rag_retrieve.py](file:///c:/Users/Tejas/Downloads/APPS/text2sql%20rag/backend/app/agents/rag_retrieve.py)
- Check if current agent identity has `READ_VECTOR_DB` permission.

## Verification Plan

### Automated Tests
- Create `tests/test_security_agent.py`:
    - **Test 1**: Verify `Orchestrator` can route but NOT execute SQL.
    - **Test 2**: Verify `SQL Generator` can execute SQL but NOT access vector DB (if restricted).
    - **Test 3**: Verify blocked actions raise `SecurityException`.
    - **Test 4**: Verify audit logs contain agent IDs.

### Manual Verification
## Verification Results

I ran a comprehensive security audit script `tests/verify_security_comprehensive.py` that covers both Happy Paths and Negative Scenarios.

### Test Execution Summary

| Test Case | Target Agent | Action | Permission Revoked | Expected Result | Actual Result | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Standard SQL Query** | `execute` | Run SQL | None | `ALLOWED` | `ALLOWED` | ✅ PASS |
| **Unauthorized Generation** | `generate` | Write SQL | `GENERATE_SQL` | `BLOCKED` | `BLOCKED` | ✅ PASS |
| **Unauthorized Execution** | `execute` | Run SQL | `EXECUTE_SQL` | `BLOCKED` | `BLOCKED` | ✅ PASS |
| **Unauthorized RAG Access** | `retrieve` | Search Docs | `READ_VECTOR_DB` | `BLOCKED` | `BLOCKED` | ✅ PASS |
| **Unauthorized Charting** | `chart` | Create Chart | `GENERATE_CHART` | `BLOCKED` | `BLOCKED` | ✅ PASS |
| **Unauthorized Orchestration** | `orchestrator` | Route Request | `ROUTE_REQUEST` | `BLOCKED` | `BLOCKED` | ✅ PASS |

### Detailed Logs

#### ✅ Happy Path (Standard Query)
```text
TEST CASE: Standard SQL Query (Happy Path)
▶️ Executing Graph...
INFO:app.utils.security:✅ [Security] Allowed: orchestrator (Role: router)
...
INFO:app.utils.security:✅ [Security] Allowed: execute (Role: db_admin)
📝 Result: ALLOWED
✅ TEST PASSED
```

#### ⛔ Failure Scenario 1: Unauthorized Syntax Generation
*Scenario*: The `Generate` agent is compromised and tries to write SQL without the `GENERATE_SQL` permission.
```text
TEST CASE: Unauthorized Generation (Revoke WRITE)
🔧 SETUP: Revoking 'generate_sql' from 'generate'
▶️ Executing Graph...
INFO:app.utils.security:⛔ [Security] Access Denied: Agent 'generate' does not have permission 'generate_sql'
📝 Result: BLOCKED
✅ TEST PASSED
```

#### ⛔ Failure Scenario 2: Unauthorized Execution
*Scenario*: The `Execute` agent tries to run SQL without the `EXECUTE_SQL` permission (e.g., privilege escalation attempt).
```text
TEST CASE: Unauthorized Execution (Revoke EXECUTE)
🔧 SETUP: Revoking 'execute_sql' from 'execute'
▶️ Executing Graph...
INFO:app.utils.security:✅ [Security] Allowed: generate (Role: sql_writer)
INFO:app.utils.security:⛔ [Security] Access Denied: Agent 'execute' does not have permission 'execute_sql'
📝 Result: BLOCKED
✅ TEST PASSED
```

#### ⛔ Failure Scenario 3: Unauthorized RAG Access
*Scenario*: The `Retrieval` agent tries to access the vector DB without `READ_VECTOR_DB` permission.
```text
TEST CASE: Unauthorized RAG Access (Revoke READ_VECTOR_DB)
🔧 SETUP: Revoking 'read_vector_db' from 'retrieve'
▶️ Executing Graph...
INFO:app.utils.security:⛔ [Security] Access Denied: Agent 'retrieve' does not have permission 'read_vector_db'
📝 Result: BLOCKED
✅ TEST PASSED
```

#### ⛔ Failure Scenario 4: Unauthorized Charting
*Scenario*: The `Chart` agent attempts to generate a visualization without `GENERATE_CHART` permission.
```text
TEST CASE: Unauthorized Chart Generation (Revoke GENERATE_CHART)
🔧 SETUP: Revoking 'generate_chart' from 'chart'
▶️ Executing Graph...
INFO:app.utils.security:⛔ [Security] Access Denied: Agent 'chart' does not have permission 'generate_chart'
📝 Result: BLOCKED
✅ TEST PASSED
```

#### ⛔ Failure Scenario 5: Unauthorized Orchestration
*Scenario*: The `Orchestrator` tries to route a request without `ROUTE_REQUEST` permission (Total Lockdown).
```text
TEST CASE: Unauthorized Routing (Revoke ROUTE_REQUEST)
🔧 SETUP: Revoking 'route_request' from 'orchestrator'
▶️ Executing Graph...
INFO:app.utils.security:⛔ [Security] Access Denied: Agent 'orchestrator' does not have permission 'route_request'
📝 Result: BLOCKED
✅ TEST PASSED
```

