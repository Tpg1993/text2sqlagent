# Image Generation Guide

The image generation service is currently at capacity. Here's how to create diagram images yourself:

## Option 1: Mermaid Live Editor (Recommended)

1. Go to **https://mermaid.live**
2. Copy the Mermaid code from the documentation files
3. Paste into the editor (left side)
4. The diagram will render on the right side
5. Click **"Actions"** → **"PNG"** or **"SVG"** to download
6. Save to `documentation/images/` folder

## Option 2: VS Code Extension

1. Install **"Markdown Preview Mermaid Support"** extension
2. Open the markdown file
3. Right-click on the rendered diagram in preview
4. Select **"Copy Image"** or use a screenshot tool
5. Save to `documentation/images/` folder

## Diagrams to Generate

From `ARCHITECTURE_DIAGRAMS.md`:

1. **system_overview.png** - Diagram 1 (System Overview)
2. **agent_state_machine.png** - Diagram 2 (Agent Execution Flow)
3. **sql_pipeline.png** - Diagram 3 (SQL Pipeline Detailed Flow)
4. **rag_pipeline.png** - Diagram 4 (RAG Pipeline Detailed Flow)
5. **pii_scrubbing.png** - Diagram 5 (PII Protection Pipeline)
6. **guardrails_flow.png** - Diagram 6 (Guardrails Validation Flow)
7. **llm_fallback.png** - Diagram 7 (LLM Invocation with Fallback)
8. **database_er.png** - Diagram 8 (Database Schema ER Diagram)
9. **deployment.png** - Diagram 10 (Deployment Architecture)
10. **security_layers.png** - Diagram 13 (Security Layers)

## File Naming Convention

Save files as: `{diagram_name}.png` or `{diagram_name}.svg`

Example: `system_overview.png`, `agent_state_machine.png`

## Once Images Are Created

Run this command to verify:
```powershell
Get-ChildItem documentation\images\*.png
```

Then I can update the documentation files to embed the images!
