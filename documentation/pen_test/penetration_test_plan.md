# Comprehensive Penetration Testing Plan: Agentic Text2SQL & RAG

Our Agentic application introduces a massive attack surface spanning traditional web vulnerabilities and new LLM/Agentic vectors. A robust penetration test must holistically attack both the infrastructure and the autonomous agent behaviors.

Below is the structured plan detailing what we will test, organized by attack surface.

## 1. LLM & Agentic Attack Vectors (The "AI" Layer)

This phase focuses on exploiting the LLM orchestrator, guardrails, and autonomous decision-making processes.

*   **Prompt Injection & Jailbreaking (Direct & Indirect):**
    *   *Direct:* Attempting to bypass NeMo Input Guardrails using complex personas, encoding, or adversarial suffixes to force the Orchestrator to route incorrectly or ignore system prompts.
    *   *Indirect:* Embedding malicious instructions inside the PDF documents *before* RAG ingestion to see if the `rag_gen` node executes them when retrieved.
*   **Agent Goal Hijacking & Tool Misuse:**
    *   Attempting to trick the `Generate` (SQL) node into writing destructive queries (`DROP TABLE`, `DELETE`, `UPDATE`) or queries that exfiltrate sensitive cross-tenant data.
    *   Testing the robustness of the **Human-in-the-Loop (HITL)** system: Can we spoof an approval? Can we bypass the `approval_pending` state and force the `Execute` node to run immediately?
*   **Vector Database (FAISS) Poisoning & Extraction:**
    *   *Poisoning:* Attempting to inject false information during ingestion to skew future RAG answers (e.g., altering the "return policy").
    *   *Extraction:* Crafting queries designed to leak raw training data, system prompts, or embedded PII that Presidio might have missed.
*   **PII Scrubber (Presidio) Evasion:**
    *   Submitting edge-case PII formats (obfuscated emails, international phone numbers, spaced-out SSNs) to test if Presidio reliably anonymizes them before they hit the LLM or Vector DB.
*   **SSRF via Search Tool:**
    *   Exploiting the `general` agent's `web_search` tool: Asking the agent to fetch internal network addresses (e.g., `http://169.254.169.254` or `http://localhost:8000/metrics`) instead of external public information.

## 2. API & Infrastructure Attack Vectors (The "Web" Layer)

This phase focuses on the FastAPI backend, routing, and standard OWASP Top 10 web vulnerabilities.

*   **Authentication & Authorization (RBAC) Bypass:**
    *   Testing JWT token security (weak signing keys, alg=none attacks, expiration evasion).
    *   *Privilege Escalation:* Attempting to execute SQL queries restricted to the `admin` role using a `user` role JWT.
    *   *Broken Object Level Authorization (BOLA):* Attempting to approve a HITL request using a different user's session/token.
*   **Denial of Service (DoS) & Asymmetric Resource Exhaustion:**
    *   *LLM DoS:* Sending thousands of massive prompts to exhaust Google/OpenAI API quotas or run up the billing.
    *   *Graph Infinite Loops:* Attempting to trap the LangGraph into an infinite retry loop (between `Validate` and `Retry` nodes) to crash the application memory.
    *   Testing the effectiveness of the SlowAPI rate limiters (`/chat` endpoint limits).
*   **SQL Injection (Traditional vs Agentic):**
    *   *Traditional:* Exploiting the `init_db` script or direct backend endpoints if any raw inputs are concatenated.
    *   *Agentic:* Trick the LLM into generating an SQL Injection payload that the system blindly trusts and executes.

## 3. Execution Strategy

To execute this Penetration Testing Plan, we will perform the following actions:

1.  **Red Teaming (Prompt Level):** Manually curating and automatically fuzzing the `/chat` endpoint with hundreds of known jailbreak arrays (e.g., using frameworks like *Garak* or *Promptfoo*).
2.  **API Fuzzing:** Using standard API testing tools (Postman, Burp Suite) to hammer the authentication and SSE streaming endpoints.
3.  **Code Review (Whitebox):** Analyzing the LangGraph edge transitions (`app/graphs/agent_graph.py`) to mathematically prove there are no unauthenticated bypasses to the `execute` node.
4.  **Guardrail Stress Testing:** Iteratively adjusting NeMo configurations while firing adversarial prompts to map exactly where the boundary of the allowed topic sits.
