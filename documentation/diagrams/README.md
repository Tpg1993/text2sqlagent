# Editable Diagram Files

This folder contains editable diagram source files that can be modified using diagram tools.

## Files

### 1. `system_architecture.drawio`
**Tool**: draw.io (diagrams.net)  
**Description**: Complete system architecture diagram with all layers

**How to Edit**:
1. Go to https://app.diagrams.net (or use VS Code with draw.io extension)
2. Click "Open Existing Diagram"
3. Select `system_architecture.drawio`
4. Edit the diagram
5. Export as PNG/SVG: File → Export as → PNG/SVG
6. Save exported image to `../images/system_architecture.png`

**Diagram Contents**:
- User Layer (React Web UI)
- API Layer (FastAPI Server)
- Security Layer (Input Guardrail, PII Scrubber, Output Guardrail)
- Orchestration Layer (Orchestrator)
- Processing Layer (SQL Pipeline, RAG Pipeline, General)
- LLM Layer (Google Gemini, OpenAI fallback)
- Data Layer (SQLite, FAISS)

## Alternative: Mermaid to draw.io

You can also convert Mermaid diagrams to draw.io:
1. Go to https://mermaid.live
2. Paste Mermaid code from documentation
3. Click "Actions" → "Export as draw.io"
4. Open in draw.io for editing

## Workflow

```
Edit .drawio file → Export as PNG/SVG → Save to ../images/ → Reference in docs
```

## VS Code Extension (Optional)

Install **Draw.io Integration** extension:
- Extension ID: `hediet.vscode-drawio`
- Allows editing .drawio files directly in VS Code
