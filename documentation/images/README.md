# Image Assets for Documentation

This folder contains diagram images used in the documentation.

## System Architecture Diagrams

### Main Architecture Diagram
**File**: `system_architecture.png`  
**Used in**:
- `../README.md` - Section: "Architecture" → "System Overview"
- `../documentation/HLD.md` - Section: "1. System Overview"
- `../documentation/ARCHITECTURE_DIAGRAMS.md` - Section: "1. Complete System Architecture"

**Description**: Layered architecture showing:
- React Web UI (top)
- FastAPI Server (API layer)
- Security Layer (Input Guardrail, PII Scrubber, Output Guardrail)
- Orchestration Layer (Orchestrator with LLM)
- Processing Layer (SQL Pipeline, RAG Pipeline, General)
- LLM Layer (Google Gemini 2.0 Flash, OpenAI GPT-4o fallback)
- Data Layer (SQLite, FAISS)

---

## How to Add Images

1. **Save your screenshot** to this folder as `system_architecture.png`
2. The documentation files will automatically reference it using:
   ```markdown
   ![System Architecture](./images/system_architecture.png)
   ```

## Current Status

- [ ] `system_architecture.png` - **PENDING** (add your screenshot here)
- [ ] `agent_flow.png` - Optional
- [ ] `pii_scrubbing.png` - Optional
- [ ] `security_layers.png` - Optional

---

## Alternative: Mermaid Diagrams

The documentation currently uses Mermaid diagrams which render automatically in:
- Antigravity markdown preview
- GitHub/GitLab
- VS Code with Mermaid extension

If you prefer static images, replace the Mermaid code blocks with image references.
