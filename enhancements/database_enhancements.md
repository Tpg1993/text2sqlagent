# Production Enhancements Guide

This document outlines recommended enhancements to transition the Agentic RAG application from development to production-ready deployment.

## 1. Dual-Database Architecture

### Overview
Separate business data (read-only) from application metadata (read-write) to enforce least privilege and improve security.

### Architecture

```
┌─────────────────────────────────────┐
│  Production Database                │
│  (PostgreSQL / Cosmos DB)           │
│  ─────────────────────────────────  │
│  • Customer Data                    │
│  • Orders, Products, Sales          │
│  • Managed Identity: READ-ONLY      │ ← Agents query here
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│  Application Database               │
│  (Separate PostgreSQL instance)     │
│  ─────────────────────────────────  │
│  • User sessions                    │
│  • Query history                    │
│  • Audit logs                       │
│  • Managed Identity: READ-WRITE     │ ← App writes here
└─────────────────────────────────────┘
```

### Implementation Steps

#### Step 1: Create Application Database
```sql
-- Create separate database for app metadata
CREATE DATABASE text2sql_app;

-- Create audit tables
CREATE TABLE query_history (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255),
    query TEXT,
    execution_time TIMESTAMP,
    success BOOLEAN,
    error_message TEXT
);

CREATE TABLE security_audit (
    id SERIAL PRIMARY KEY,
    agent_name VARCHAR(100),
    action VARCHAR(100),
    permission_required VARCHAR(100),
    result VARCHAR(50),
    timestamp TIMESTAMP
);
```

#### Step 2: Update Code to Use Dual Connections

**File: `app/sql/engine.py`**
```python
from sqlalchemy import create_engine

# Production data (read-only)
production_engine = create_engine(
    os.getenv("PRODUCTION_DB_URL"),
    connect_args={"options": "-c default_transaction_read_only=on"}
)

# Application metadata (read-write)
app_engine = create_engine(
    os.getenv("APP_DB_URL")
)
```

**File: `app/agents/execute.py`**
```python
from app.sql.engine import production_engine, app_engine

def execute_node(state):
    # Query production data (read-only)
    with production_engine.connect() as conn:
        result = conn.execute(text(state['sql_query']))
    
    # Log to application database
    with app_engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO query_history (user_id, query, execution_time, success)
            VALUES (:uid, :q, :ts, :success)
        """), {
            "uid": state.get('user_id'),
            "q": state['sql_query'],
            "ts": datetime.now(),
            "success": True
        })
    
    return {"results": result.fetchall()}
```

#### Step 3: Configure Azure Managed Identity

**For Production Database (Read-Only)**
```bash
# Create managed identity
az identity create --name text2sql-reader --resource-group myResourceGroup

# Assign read-only role to PostgreSQL
az postgres flexible-server ad-admin create \
  --resource-group myResourceGroup \
  --server-name myProductionDB \
  --object-id <managed-identity-object-id> \
  --display-name text2sql-reader

# Grant SELECT only
GRANT SELECT ON ALL TABLES IN SCHEMA public TO "text2sql-reader";
```

**For Application Database (Read-Write)**
```bash
# Create separate managed identity
az identity create --name text2sql-writer --resource-group myResourceGroup

# Grant INSERT/UPDATE for audit tables
GRANT SELECT, INSERT, UPDATE ON query_history TO "text2sql-writer";
GRANT SELECT, INSERT ON security_audit TO "text2sql-writer";
```

---

## 2. Persistent Audit Logging

### Current State
Security logs are printed to stdout and lost after container restart.

### Enhancement
Stream logs to Azure Log Analytics or Application Insights.

### Implementation

**File: `app/utils/security.py`**
```python
from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry import trace

# Configure Azure Monitor
configure_azure_monitor(
    connection_string=os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
)

tracer = trace.get_tracer(__name__)

class SecurityManager:
    def enforce(self, node_name: str, required_permission: Optional[Permission] = None):
        def decorator(func: Callable):
            @functools.wraps(func)
            def wrapper(state: Any):
                identity = self.policy.get_identity(node_name)
                
                # Create audit span
                with tracer.start_as_current_span("security_check") as span:
                    span.set_attribute("agent.name", node_name)
                    span.set_attribute("agent.role", identity.role)
                    span.set_attribute("permission.required", required_permission.value if required_permission else "none")
                    
                    if required_permission and not identity.has_permission(required_permission):
                        span.set_attribute("result", "DENIED")
                        logger.error(f"⛔ Access Denied: {node_name}")
                        return {"error": "Access Denied"}
                    
                    span.set_attribute("result", "ALLOWED")
                    logger.info(f"✅ Allowed: {node_name}")
                    return func(state)
            return wrapper
        return decorator
```

---

## 3. User Authentication (JWT)

### Implementation

**File: `app/auth/jwt.py`**
```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(
            credentials.credentials,
            os.getenv("JWT_SECRET"),
            algorithms=["HS256"]
        )
        return payload  # Contains user_id, role
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

**File: `app/main.py`**
```python
from app.auth.jwt import verify_token

@app.post("/chat")
async def chat(request: ChatRequest, user=Depends(verify_token)):
    # Add user_id to state
    inputs = {
        "question": request.question,
        "user_id": user["user_id"],
        "user_role": user["role"]
    }
    result = await graph.ainvoke(inputs)
    return result
```

---

## 4. Secrets Management

### Current State
API keys stored in `.env` files.

### Enhancement
Use Azure Key Vault.

### Implementation

```python
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

credential = DefaultAzureCredential()
client = SecretClient(vault_url="https://mykeyvault.vault.azure.net/", credential=credential)

# Retrieve secrets
OPENAI_API_KEY = client.get_secret("openai-api-key").value
DATABASE_URL = client.get_secret("production-db-url").value
```

---

## 5. HTTPS/TLS Enforcement

### Implementation
Use Azure Application Gateway or Nginx reverse proxy.

**Nginx Config**
```nginx
server {
    listen 443 ssl;
    server_name api.example.com;
    
    ssl_certificate /etc/ssl/certs/cert.pem;
    ssl_certificate_key /etc/ssl/private/key.pem;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto https;
    }
}
```

---

## Priority Roadmap

| Phase | Enhancement | Effort | Impact |
|:---:|:---|:---:|:---:|
| **Phase 1** | Dual-Database Architecture | Medium | High |
| **Phase 1** | Managed Identity (Azure) | Low | High |
| **Phase 2** | Persistent Audit Logging | Medium | Medium |
| **Phase 2** | JWT Authentication | Medium | High |
| **Phase 3** | Secrets Management (Key Vault) | Low | Medium |
| **Phase 3** | HTTPS/TLS | Low | High |
