import sys
import asyncio

# Ensure Unicode logs/progress messages don't crash on Windows cp1252 consoles.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

print("[DEBUG] Loading app.main...", flush=True)
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
print("[DEBUG] FastAPI imported", flush=True)
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uuid
from datetime import timedelta

print("[DEBUG] Importing graph...", flush=True)
from app.graphs.agent_graph import graph
print("[DEBUG] Graph imported.", flush=True)

from app.config import settings
from app.utils.sse_manager import sse_manager
from app.utils.hitl import approval_manager
from app.auth.models import Token, LoginRequest
from app.auth.jwt import create_access_token, get_current_user_token, verify_token, ACCESS_TOKEN_EXPIRE_MINUTES, TokenData
from fastapi import Query

# Rate Limiting
print("[DEBUG] Importing slowapi...")
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Initialize Limiter
limiter = Limiter(key_func=get_remote_address, headers_enabled=True)

print("[DEBUG] Initializing FastAPI app...")
app = FastAPI(title=settings.PROJECT_NAME)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Debug Middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    print(f"[REQUEST] {request.method} {request.url}")
    try:
        response = await call_next(request)
        print(f"[RESPONSE] {response.status_code}")
        return response
    except Exception as e:
        print(f"[ERROR] Request Failed: {e}")
        import traceback
        traceback.print_exc()
        raise e

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup OpenTelemetry
# from app.utils.telemetry import setup_telemetry
# setup_telemetry(app)
print("[DEBUG] App initialization complete (pre-startup)")


from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    message: str = Field(..., max_length=4000)
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    data: Optional[List[Dict[str, Any]]] = None
    chart: Optional[Dict[str, Any]] = None
    approval_status: Optional[str] = None

@app.post(settings.API_V1_STR + "/auth/login", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    # In a real app, verify username/password against DB
    # For HITL demo, we accept any username/password and make 'admin' user robust
    user_role = "user"
    if form_data.username == "admin":
        if form_data.password != settings.ADMIN_PASSWORD:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user_role = "admin"
    elif form_data.username == "user1":
        if form_data.password != settings.USER1_PASSWORD:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user_role = "user"
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": form_data.username, "role": user_role},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get(settings.API_V1_STR + "/stream/{session_id}")
async def stream_progress(session_id: str, token: str = Query(...)):
    """SSE endpoint for streaming agent progress. Requires token query param."""
    # TEMPORARILY DISABLED - StreamingResponse causing issues
    # Return empty response to prevent frontend errors
    from fastapi.responses import Response
    return Response(content="", media_type="text/plain", status_code=200)

# Helper: Extract User ID for Rate Limiting
def get_user_key(request: Request):
    """
    Extracts user ID from Authorization header for rate limiting.
    Falls back to IP if no token is present.
    """
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
             # Basic decode to get 'sub' (username). Signature verification is handled by dependency.
             import jwt
             # We assume standard JWT format. Using pyjwt here.
             # Note: 'options' param might vary by library version, but decode generally works.
             # We use verify=False because we just want the ID for the key, security is handled later.
             payload = jwt.decode(token, options={"verify_signature": False})
             return payload.get("sub", get_remote_address(request))
        except Exception:
             return get_remote_address(request)
    return get_remote_address(request)

# Dynamic Limit Value Functions
def get_ip_limit_value():
    return "60/minute" if settings.ENABLE_IP_RATE_LIMIT else "10000/second"

def get_user_limit_value():
    return "10/minute" if settings.ENABLE_USER_RATE_LIMIT else "10000/second"

APPROVAL_TIMEOUT_SECONDS = 300  # 5 minutes

async def auto_reject_after_timeout(request_id: str, timeout: int = APPROVAL_TIMEOUT_SECONDS):
    """
    Background task: auto-reject a pending approval after `timeout` seconds.
    """
    await asyncio.sleep(timeout)
    approval_request = approval_manager.get_request(request_id)
    if approval_request and approval_request.status.value == "pending":
        approval_manager.reject_request(
            request_id,
            reason="Auto-rejected: timed out after 5 minutes with no admin action.",
            rejector_id="system"
        )

@app.post(settings.API_V1_STR + "/chat", response_model=ChatResponse)
# TEMPORARILY REMOVED: Rate limiting causes slowapi response type error
# @limiter.limit(get_ip_limit_value, key_func=get_remote_address) # Per IP Limit (DoS Protection)
# @limiter.limit(get_user_limit_value, key_func=get_user_key)       # Per User Limit (Quota)
async def chat_endpoint(request: Request, body: ChatRequest, current_user: TokenData = Depends(get_current_user_token)):
    import logging
    import traceback
    logger = logging.getLogger(__name__)
    
    # Generate or use provided session ID
    session_id = body.session_id or str(uuid.uuid4())
    sse_manager.create_session(session_id)
    print(f"[DEBUG] Chat Endpoint: Received message '{body.message}' Session: {session_id}")
    
    try:
        from langchain_core.messages import HumanMessage
        initial_state = {
            "question": body.message,
            "messages": [HumanMessage(content=body.message)],
            "retry_count": 0,
            "session_id": session_id,
            "user_id": current_user.username,
            "user_role": current_user.role
        }
        config = {"configurable": {"thread_id": session_id}}
        result = await graph.ainvoke(initial_state, config=config)
        
        final_msg = result.get("messages", [""])[-1]
        response_text = final_msg if isinstance(final_msg, str) else final_msg.content
        
        # Check if query requires approval (HITL)
        if result.get("requires_approval") and result.get("approval_status") == "pending":
            request_id = result.get('approval_request_id')
            asyncio.create_task(auto_reject_after_timeout(request_id))
            # DO NOT close SSE session here. Keep it open for approval result.
            return ChatResponse(
                response=f"[WARNING] This query requires approval as it accesses sensitive tables: {', '.join(result.get('sensitive_tables', []))}. Approval request ID: {request_id}",
                data=None,
                chart=None,
                approval_status="pending"
            )
        
        # Close SSE session for normal requests
        sse_manager.close_session(session_id)
        
        return ChatResponse(
            response=response_text,
            data=result.get("sql_result") if isinstance(result.get("sql_result"), list) else None,
            chart=result.get("visualization_spec")
        )
    except Exception as e:
        import traceback
        print(f"CRITICAL BACKEND EXCEPTION: {repr(e)}")
        print(traceback.format_exc())
        
        # Check if it is our custom RateLimitException
        from app.utils.exceptions import RateLimitException
        if isinstance(e, RateLimitException) or (hasattr(e, "retry_after") and e.retry_after):
             logger.warning(f"Rate limit hit: {e}")
             from fastapi.responses import JSONResponse
             return JSONResponse(
                 status_code=429, 
                 content={
                     "error": "Rate limit exceeded", 
                     "message": str(e),
                     "retry_after": getattr(e, "retry_after", None)
                 }
             )

        logger.error(f"Error in chat endpoint: {e}")
        logger.error(traceback.format_exc())
        
        # Write to file for debugging
        with open("error_log.txt", "w") as f:
            f.write(f"=== ERROR IN CHAT ENDPOINT ===\n")
            f.write(f"Error: {e}\n")
            f.write(f"Traceback:\n{traceback.format_exc()}\n")
            f.write(f"=== END ERROR ===\n")
        
        # Re-raise to let FastAPI handle it (or return 500)
        raise HTTPException(status_code=500, detail=str(e))

from fastapi import UploadFile, File, BackgroundTasks
import shutil
import os

def run_ingestion(filepath: str):
    import logging
    logger = logging.getLogger(__name__)
    try:
        from app.rag.ingest import ingest_pdf_file
        logger.info(f"Starting background ingestion for {filepath}")
        ingest_pdf_file(filepath)
        logger.info("Background ingestion completed")
    except Exception as e:
        logger.error(f"Background ingestion failed: {e}")

@app.post(settings.API_V1_STR + "/upload-docs")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    token: TokenData = Depends(get_current_user_token)
):
    if token.role != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required to upload documents")
    
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
    save_dir = os.path.join(settings.BASE_DIR, "data", "docs")
    os.makedirs(save_dir, exist_ok=True)
    
    file_path = os.path.join(save_dir, file.filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    background_tasks.add_task(run_ingestion, file_path)
    
    return {"message": f"File {file.filename} uploaded successfully. Ingestion started in background."}

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get(settings.API_V1_STR + "/test-limit")
@limiter.limit("2/minute")
async def test_limit(request: Request):
    return {"status": "ok"}

# ===== HITL Approval Endpoints =====

@app.post(settings.API_V1_STR + "/approve/{request_id}")
async def approve_query(request_id: str, token: TokenData = Depends(get_current_user_token)):
    """
    Approve a pending query. Requires admin authentication.
    """
    from fastapi import HTTPException
    
    if token.role != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required to approve queries")
    
    # Get the approval request
    approval_request = approval_manager.get_request(request_id)
    
    if not approval_request:
        raise HTTPException(status_code=404, detail="Approval request not found")
    
    if approval_request.status.value != "pending":
        raise HTTPException(
            status_code=400, 
            detail=f"Request is already {approval_request.status.value}"
        )
    
    # Approve the request
    approval_manager.approve_request(request_id, approver_id=token.username)
    
    # Execute the query
    try:
        from app.db.session import engine
        from sqlalchemy import text
        
        with engine.connect() as conn:
            # Clean up the query string: remove formatting backticks and any stray quotes
            clean_query = approval_request.query.replace('```sql', '').replace('```', '').strip().strip('"').strip("'")
            result = conn.execute(text(clean_query))
            rows = [dict(row._mapping) for row in result]
        
        # Store results so frontend polling can retrieve them
        approval_request.results = rows

        # Send real-time update to the user (best effort, may drop on Vite proxy)
        if approval_request.session_id:
            try:
                await sse_manager.send_event(
                    session_id=approval_request.session_id,
                    event_type="approval_result",
                    data={
                         "response": f"[APPROVED] Query executed successfully.",
                         "data": rows
                    }
                )
            except Exception:
                pass

        return {
            "status": "approved",
            "request_id": request_id,
            "query": approval_request.query,
            "results": rows
        }
    except Exception as e:
        return {
            "status": "approved_but_failed",
            "request_id": request_id,
            "error": str(e)
        }

@app.post(settings.API_V1_STR + "/reject/{request_id}")
async def reject_query(request_id: str, reason: str = "No reason provided", token: TokenData = Depends(get_current_user_token)):
    """
    Reject a pending query. Requires admin authentication.
    """
    from fastapi import HTTPException
    
    if token.role != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required to reject queries")
    
    approval_request = approval_manager.get_request(request_id)
    
    if not approval_request:
        raise HTTPException(status_code=404, detail="Approval request not found")
    
    if approval_request.status.value != "pending":
        raise HTTPException(
            status_code=400, 
            detail=f"Request is already {approval_request.status.value}"
        )
    
    # Reject the request
    approval_manager.reject_request(request_id, reason=reason, rejector_id=token.username)
    
    return {
        "status": "rejected",
        "request_id": request_id,
        "reason": reason
    }

@app.get(settings.API_V1_STR + "/pending-approvals")
async def get_pending_approvals(token: TokenData = Depends(get_current_user_token)):
    """
    Get all pending approval requests. Requires admin authentication.
    """
    from fastapi import HTTPException
    
    if token.role != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required to view pending approvals")
    pending = approval_manager.get_pending_requests()
    
    return {
        "count": len(pending),
        "requests": [req.to_dict() for req in pending]
    }

@app.get(settings.API_V1_STR + "/approval-status/{request_id}")
async def get_approval_status(request_id: str, token: TokenData = Depends(get_current_user_token)):
    """
    Poll the status and results of an approval request.
    """
    approval_request = approval_manager.get_request(request_id)
    
    if not approval_request:
        raise HTTPException(status_code=404, detail="Approval request not found")
    
    response = {
        "request_id": request_id,
        "status": approval_request.status.value,
        "query": approval_request.query,
        "sensitive_tables": approval_request.sensitive_tables,
    }
    
    if approval_request.status.value == "approved":
        response["results"] = getattr(approval_request, 'results', [])
        response["message"] = approval_request.reason
    elif approval_request.status.value == "rejected":
        response["message"] = approval_request.reason
    
    return response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

