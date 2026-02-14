# Architecture Diagrams & Flow Charts

## 1. Complete System Architecture

```mermaid
C4Context
    title System Context Diagram - Text2SQL & RAG Application

    Person(user, "End User", "Asks questions about data and documents")
    
    System_Boundary(app, "Text2SQL & RAG Application") {
        System(frontend, "React Frontend", "User interface with real-time updates")
        System(backend, "FastAPI Backend", "Agent orchestration with security")
    }
    
    System_Ext(gemini, "Google Gemini API", "LLM for intent classification, SQL generation, RAG")
    System_Ext(openai, "OpenAI API", "Fallback LLM (disabled)")
    
    Rel(user, frontend, "Asks questions", "HTTPS")
    Rel(frontend, backend, "Sends queries", "REST API + SSE")
    Rel(backend, gemini, "LLM calls", "HTTPS")
    Rel(backend, openai, "Fallback", "HTTPS")
```

## 2. Agent State Machine

```mermaid
stateDiagram-v2
    [*] --> InputGuardrail
    
    InputGuardrail --> Orchestrator: Input Valid
    InputGuardrail --> Format: Input Blocked
    
    Orchestrator --> SQLFlow: intent=sql
    Orchestrator --> RAGFlow: intent=rag
    Orchestrator --> GeneralAgent: intent=general
    
    state GeneralAgent {
        [*] --> SearchTool
        SearchTool --> [*]
    }
    
    state SQLFlow {
        [*] --> Schema
        Schema --> Generate
        Generate --> Validate
        
        Validate --> Execute: SQL Valid
        Validate --> Retry: SQL Invalid
        
        Execute --> Evaluate
        Evaluate --> Chart: Success
        Evaluate --> Retry: Error
        
        Retry --> Generate: retry_count ≤ 3
        Retry --> [*]: retry_count > 3
        
        Chart --> [*]
    }
    
    state RAGFlow {
        [*] --> Retrieve
        Retrieve --> RAGGenerate
        RAGGenerate --> [*]
    }
    
    SQLFlow --> Format
    RAGFlow --> Format
    GeneralAgent --> Format
    
    Format --> OutputGuardrail
    OutputGuardrail --> [*]
```

## 3. SQL Pipeline Detailed Flow

```mermaid
flowchart TD
    Start([SQL Query Request]) --> Schema[Fetch Database Schema]
    Schema --> Generate[Generate SQL with LLM]
    Generate --> Validate{Syntax Valid?}
    
    Validate -->|Yes| Execute[Execute Query]
    Validate -->|No| CheckRetry1{Retry Count > 3?}
    
    CheckRetry1 -->|Yes| FormatError[Format Error Message]
    CheckRetry1 -->|No| IncrementRetry1[Increment Retry Count]
    IncrementRetry1 --> Generate
    
    Execute --> Evaluate{Results Valid?}
    
    Evaluate -->|Yes| Chart[Generate Vega-Lite Chart]
    Evaluate -->|No| CheckRetry2{Retry Count > 3?}
    
    CheckRetry2 -->|Yes| FormatError
    CheckRetry2 -->|No| IncrementRetry2[Increment Retry Count]
    IncrementRetry2 --> Generate
    
    Chart --> FormatSuccess[Format Success Response]
    FormatSuccess --> End([Return to User])
    FormatError --> End
    
    style Generate fill:#4A90E2,color:#fff
    style Execute fill:#2ECC71,color:#fff
    style Chart fill:#9B59B6,color:#fff
    style FormatError fill:#E74C3C,color:#fff
    style FormatSuccess fill:#2ECC71,color:#fff
```

## 4. RAG Pipeline Detailed Flow

```mermaid
flowchart TD
    Start([RAG Query Request]) --> Retrieve[FAISS Similarity Search]
    Retrieve --> CheckDocs{Documents Found?}
    
    CheckDocs -->|Yes| RAGGen[Generate Answer with LLM]
    CheckDocs -->|No| NoDocsMsg[No relevant documents found]
    
    RAGGen --> Format[Format Response]
    NoDocsMsg --> Format
    
    Format --> End([Return to User])
    
    style Retrieve fill:#3498DB,color:#fff
    style RAGGen fill:#4A90E2,color:#fff
    style Format fill:#2ECC71,color:#fff
```

## 5. PII Scrubbing Flow

```mermaid
flowchart LR
    A[PDF Document] --> B[PyPDFLoader]
    B --> C[Split into Chunks<br/>1000 chars, 200 overlap]
    C --> D{For Each Chunk}
    
    D --> E[Presidio Analyzer]
    E --> F{PII Detected?}
    
    F -->|Yes| G[Presidio Anonymizer]
    F -->|No| H[Keep Original]
    
    G --> I[Replace with Placeholders<br/>&lt;EMAIL&gt; &lt;PHONE&gt;]
    I --> J[Create Embeddings]
    H --> J
    
    J --> K[Store in FAISS]
    K --> L[Vector Database]
    
    style E fill:#E74C3C,color:#fff
    style G fill:#E74C3C,color:#fff
    style I fill:#2ECC71,color:#fff
    style L fill:#3498DB,color:#fff
```

## 6. Guardrails Validation Flow

```mermaid
flowchart TD
    subgraph Input["Input Guardrail"]
        I1[User Query] --> I2[NeMo Validation]
        I2 --> I3{Safe?}
        I3 -->|Yes| I4[Continue to Orchestrator]
        I3 -->|No| I5[Block & Return Error]
    end
    
    subgraph Processing["Agent Processing"]
        P1[Orchestrator] --> P2[SQL/RAG]
        P1 --> P3[General Agent]
        P3 --> P3a[Web Search Tool]
        P2 --> P4[LLM Generation]
        P3 --> P4
        P4 --> P5[Format Response]
        P4 --> P6[Chart Tool]
        P6 --> P5
    end
    
    subgraph Output["Output Guardrail"]
        O1[LLM Response] --> O2[NeMo Validation]
        O2 --> O3{Safe?}
        O3 -->|Yes| O4[Return to User]
        O3 -->|No| O5[Replace with Safe Message]
        O5 --> O4
    end
    
    I4 --> P1
    P4 --> O1
    
    style I2 fill:#FFD700,color:#000
    style I5 fill:#E74C3C,color:#fff
    style O2 fill:#FFD700,color:#000
    style O5 fill:#E74C3C,color:#fff
```

## 7. LLM Invocation with Fallback

```mermaid
flowchart TD
    Start[LLM Call Needed] --> TryGemini[Try Google Gemini 2.0]
    
    TryGemini --> CheckError{Error?}
    
    CheckError -->|No Error| Success[Return Response]
    CheckError -->|Rate Limit 429| RateLimit[Extract retry_after]
    CheckError -->|Other Error| TryOpenAI[Try OpenAI GPT-4o]
    
    RateLimit --> FailFast[Raise RateLimitException]
    FailFast --> UserWait[User Sees Wait Time]
    
    TryOpenAI --> CheckOpenAI{Error?}
    CheckOpenAI -->|No Error| Success
    CheckOpenAI -->|Error| Fail[Raise Exception]
    
    Success --> End([Complete])
    UserWait --> End
    Fail --> End
    
    style TryGemini fill:#4285F4,color:#fff
    style TryOpenAI fill:#10A37F,color:#fff
    style RateLimit fill:#E74C3C,color:#fff
    style Success fill:#2ECC71,color:#fff
```

## 8. Database Schema ER Diagram

```mermaid
erDiagram
    EMPLOYEES ||--o{ SALES : makes
    EMPLOYEES }o--|| DEPARTMENTS : belongs_to
    DEPARTMENTS ||--o| EMPLOYEES : managed_by
    CUSTOMERS ||--o{ SALES : purchases
    
    EMPLOYEES {
        int id PK
        string name
        int department_id FK
        float salary
        date hire_date
    }
    
    DEPARTMENTS {
        int id PK
        string name
        int manager_id FK
    }
    
    SALES {
        int id PK
        int employee_id FK
        int customer_id FK
        float amount
        date sale_date
    }
    
    CUSTOMERS {
        int id PK
        string name
        string email
        string phone
        string state
    }
```

## 9. Frontend Component Hierarchy

```mermaid
graph TD
    App[App.jsx] --> Header[Header Component]
    App --> ChatInterface[ChatInterface Component]
    App --> SSEManager[SSE Manager]
    
    ChatInterface --> QueryInput[QueryInput Component]
    ChatInterface --> ProgressSteps[ProgressSteps Component]
    ChatInterface --> ResultDisplay[ResultDisplay Component]
    
    ResultDisplay --> SQLResult[SQLResult Component]
    ResultDisplay --> ChartDisplay[ChartDisplay Component]
    ResultDisplay --> RAGAnswer[RAGAnswer Component]
    ResultDisplay --> ErrorDisplay[ErrorDisplay Component]
    
    ChartDisplay --> RechartsLib[Recharts Library]
    
    SSEManager --> EventSource[EventSource API]
    
    style App fill:#61DAFB,color:#000
    style ChatInterface fill:#4A90E2,color:#fff
    style ResultDisplay fill:#2ECC71,color:#fff
```

## 10. Deployment Architecture

```mermaid
graph TB
    subgraph User["User Layer"]
        Browser[Web Browser]
    end
    
    subgraph CDN["CDN Layer"]
        Vercel[Vercel<br/>Static Hosting]
    end
    
    subgraph API["API Layer"]
        CloudRun[Google Cloud Run<br/>Docker Container]
        LB[Load Balancer]
    end
    
    subgraph Services["External Services"]
        GeminiAPI[Google Gemini API]
        OpenAIAPI[OpenAI API]
    end
    
    subgraph Data["Data Layer"]
        SQLiteFile[SQLite File<br/>Persistent Volume]
        FAISSFile[FAISS Index<br/>Persistent Volume]
    end
    
    Browser --> Vercel
    Vercel --> LB
    LB --> CloudRun
    
    CloudRun --> GeminiAPI
    CloudRun --> OpenAIAPI
    CloudRun --> SQLiteFile
    CloudRun --> FAISSFile
    
    style Browser fill:#61DAFB,color:#000
    style Vercel fill:#000,color:#fff
    style CloudRun fill:#4285F4,color:#fff
    style GeminiAPI fill:#4285F4,color:#fff
    style OpenAIAPI fill:#10A37F,color:#fff
```

## 11. Error Handling Flow

```mermaid
flowchart TD
    Start[Error Occurs] --> Classify{Error Type?}
    
    Classify -->|Rate Limit| RateLimit[Extract retry_after]
    Classify -->|SQL Error| SQLError[Check Retry Count]
    Classify -->|LLM Error| LLMError[Try Fallback]
    Classify -->|Validation Error| ValError[Return 400]
    Classify -->|Guardrail Block| GuardBlock[Return Safe Message]
    
    RateLimit --> Return429[Return 429 with retry_after]
    
    SQLError --> CheckCount{Count > 3?}
    CheckCount -->|Yes| ReturnError[Return Error in Response]
    CheckCount -->|No| Retry[Retry with Error Context]
    
    LLMError --> TryFallback{Fallback Available?}
    TryFallback -->|Yes| UseFallback[Use OpenAI]
    TryFallback -->|No| Return500[Return 500]
    
    ValError --> ReturnError
    GuardBlock --> ReturnError
    
    Return429 --> End([Response to User])
    ReturnError --> End
    Retry --> End
    UseFallback --> End
    Return500 --> End
    
    style Return429 fill:#E74C3C,color:#fff
    style Return500 fill:#E74C3C,color:#fff
    style Retry fill:#F39C12,color:#fff
    style UseFallback fill:#2ECC71,color:#fff
```

## 12. SSE (Server-Sent Events) Flow

```mermaid
sequenceDiagram
    participant F as Frontend
    participant API as FastAPI
    participant SSE as SSE Manager
    participant Graph as LangGraph
    
    F->>API: POST /chat {question}
    API->>API: Generate session_id
    API->>Graph: Invoke workflow(state)
    
    par Workflow Execution
        Graph->>SSE: Emit "orchestrator" event
        SSE->>F: SSE: "🤖 Analyzing query..."
        
        Graph->>SSE: Emit "schema" event
        SSE->>F: SSE: "📋 Fetching schema..."
        
        Graph->>SSE: Emit "generate" event
        SSE->>F: SSE: "✍️ Generating SQL..."
        
        Graph->>SSE: Emit "execute" event
        SSE->>F: SSE: "⚡ Running query..."
        
        Graph->>SSE: Emit "chart" event
        SSE->>F: SSE: "📈 Creating chart..."
    end
    
    Graph-->>API: Final state
    API->>F: HTTP Response {answer, sql_query, ...}
    SSE->>F: SSE: "complete"
```

## 13. Security Layers

```mermaid
graph LR
    subgraph External["External Threats"]
        Jailbreak[Jailbreak Attempts]
        Harmful[Harmful Queries]
        PII[PII in Documents]
    end
    
    subgraph Defense["Defense Layers"]
        Layer1[Input Guardrail<br/>NeMo]
        Layer2[Intent Classification<br/>LLM]
        Layer3[PII Scrubbing<br/>Presidio]
        Layer4[Output Guardrail<br/>NeMo]
    end
    
    subgraph Safe["Safe Output"]
        User[User Receives<br/>Safe Response]
    end
    
    Jailbreak --> Layer1
    Harmful --> Layer1
    Layer1 --> Layer2
    
    PII --> Layer3
    Layer3 --> Layer2
    
    Layer2 --> Layer4
    Layer4 --> User
    
    style Layer1 fill:#FFD700,color:#000
    style Layer3 fill:#E74C3C,color:#fff
    style Layer4 fill:#FFD700,color:#000
    style User fill:#2ECC71,color:#fff
```
