# LLM Fallback & Retry Logic

This diagram illustrates the current logic for LLM model selection and error handling, including the new "Fail Fast" mechanism for rate limits.

```mermaid
flowchart TD
    Start([Start Request]) --> TryGemini[Try Gemini Model]
    
    TryGemini -- Success --> Result([Return Result])
    TryGemini -- Error --> CheckError{Error Type?}
    
    CheckError -- "Rate Limit (429)" --> FailFast[Raise RateLimitException]
    FailFast --> EndError([Stop & Notify User])
    
    CheckError -- "Other Error" --> Log[Log Gemini Error]
    Log --> TryOpenAI[Try OpenAI Fallback]
    
    TryOpenAI -- Success --> Result
    TryOpenAI -- Error --> FailOpenAI[Raise OpenAI Error]
    FailOpenAI --> EndError
    
    style FailFast fill:#f96,stroke:#333,stroke-width:2px
    style EndError fill:#f00,stroke:#333,stroke-width:2px,color:#fff
    style TryGemini fill:#e1f5fe,stroke:#01579b
    style TryOpenAI fill:#e8f5e9,stroke:#2e7d32
```

## Key behaviors:
1.  **Primary**: Gemini is always attempted first.
2.  **Fail Fast**: If a **Rate Limit** (429) is encountered, the system **immediately stops** and propagates the error to the user. It does *not* try OpenAI, avoiding further delays or confusion.
3.  **Fallback**: For other errors (e.g., API downtime, bad request), it attempts to fall back to OpenAI.
