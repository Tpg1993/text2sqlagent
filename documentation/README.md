# Documentation Index

Welcome to the Text2SQL & RAG Application documentation. This folder contains comprehensive technical documentation for the system.

## 📚 Documents

### 1. [High-Level Design (HLD)](./HLD.md)
**Purpose**: System overview and architectural decisions

**Contents**:
- System overview with component diagrams
- Architecture principles and design patterns
- Component responsibilities
- Data flow diagrams (SQL and RAG)
- Non-functional requirements
- Technology stack decisions
- Future enhancements

**Audience**: Architects, Tech Leads, Stakeholders

---

### 2. [Low-Level Design (LLD)](./LLD.md)
**Purpose**: Detailed implementation specifications

**Contents**:
- Module-level architecture
- Detailed component design with function signatures
- Database schema (SQLite tables)
- API specifications (request/response formats)
- Error handling strategy
- Performance considerations
- Testing strategy

**Audience**: Developers, QA Engineers

---

### 3. [Architecture Diagrams](./ARCHITECTURE_DIAGRAMS.md)
**Purpose**: Visual representations of system architecture

**Contents**:
- System context diagram
- Agent state machine
- SQL pipeline flow
- RAG pipeline flow
- PII scrubbing flow
- Guardrails validation flow
- LLM invocation with fallback
- Database ER diagram
- Frontend component hierarchy
- Deployment architecture
- Error handling flow
- SSE (Server-Sent Events) flow
- Security layers

**Audience**: All technical stakeholders

---

## 🎯 Quick Navigation

### For New Developers
1. Start with [HLD](./HLD.md) - Section 1 & 2 (System Overview & Architecture Principles)
2. Review [Architecture Diagrams](./ARCHITECTURE_DIAGRAMS.md) - Diagrams 1, 2, 3, 4
3. Read [LLD](./LLD.md) - Section 2 (Detailed Component Design)

### For Architects
1. [HLD](./HLD.md) - Complete document
2. [Architecture Diagrams](./ARCHITECTURE_DIAGRAMS.md) - All diagrams
3. [LLD](./LLD.md) - Section 5 (Error Handling) & Section 6 (Performance)

### For Security Review
1. [HLD](./HLD.md) - Section 3.3 (Security Layer)
2. [Architecture Diagrams](./ARCHITECTURE_DIAGRAMS.md) - Diagrams 5, 6, 13
3. [LLD](./LLD.md) - Section 2.4 (Security Components)

### For DevOps/Deployment
1. [HLD](./HLD.md) - Section 6 (Deployment Architecture)
2. [Architecture Diagrams](./ARCHITECTURE_DIAGRAMS.md) - Diagram 10
3. [LLD](./LLD.md) - Section 6 (Performance Considerations)

---

## 🔑 Key Concepts

### Agent-Based Architecture
The system uses **LangGraph** to orchestrate multiple specialized agents in a state machine pattern. Each agent has a specific responsibility (e.g., SQL generation, validation, execution).

### Security-First Design
Three layers of security:
1. **Input Guardrails** (NeMo) - Validates user inputs
2. **PII Scrubbing** (Presidio) - Anonymizes sensitive data
3. **Output Guardrails** (NeMo) - Validates LLM responses

### Dual Processing Pipelines
- **SQL Pipeline**: Natural language → SQL → Execution → Visualization
- **RAG Pipeline**: Question → Document Retrieval → Answer Generation

---

## 📊 Diagram Legend

### Colors
- 🔵 **Blue**: LLM-powered components
- 🟢 **Green**: Success states / Safe outputs
- 🔴 **Red**: Error states / Security blocks
- 🟡 **Yellow**: Security/Validation layers
- 🟣 **Purple**: Data processing

### Symbols
- `[ ]` - Process/Function
- `{ }` - Decision point
- `( )` - Start/End state
- `→` - Data flow
- `⇢` - Conditional flow

---

## 🛠️ Tools Used

All diagrams are created using **Mermaid** syntax, which renders natively in:
- GitHub
- GitLab
- VS Code (with Mermaid extension)
- Markdown viewers

To edit diagrams, modify the Mermaid code blocks in the respective `.md` files.

---

## 📝 Document Maintenance

### When to Update

| Trigger | Documents to Update |
|---------|---------------------|
| New feature added | HLD (Section 8), LLD (Section 2), Architecture Diagrams |
| Architecture change | HLD (Section 1, 2), Architecture Diagrams (Diagram 1, 2) |
| API change | LLD (Section 4) |
| Database schema change | LLD (Section 3), Architecture Diagrams (Diagram 8) |
| Security enhancement | HLD (Section 3.3), LLD (Section 2.4), Architecture Diagrams (Diagram 13) |
| Deployment change | HLD (Section 6), Architecture Diagrams (Diagram 10) |

### Version History
- **v1.0** (2026-02-09): Initial documentation with Guardrails & PII detection

---

## 📞 Contact

For questions about this documentation:
- Technical questions: Review the specific document section
- Architecture decisions: See HLD Section 7 (Technology Decisions)
- Implementation details: See LLD Section 2 (Detailed Component Design)

---

## 🔗 Related Resources

- [Main README](../README.md) - Project setup and usage
- [Backend Code](../backend/) - Implementation
- [Frontend Code](../frontend/) - UI implementation
- [API Documentation](http://localhost:8000/docs) - Interactive API docs (when server is running)
