from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uuid
from datetime import timedelta
from app.graphs.agent_graph import graph
from app.config import settings
from app.utils.sse_manager import sse_manager
from app.utils.hitl import approval_manager
from app.auth.models import Token, LoginRequest
from app.auth.jwt import create_access_token, get_current_user_token, verify_token, ACCESS_TOKEN_EXPIRE_MINUTES, TokenData
from fastapi import Query

app = FastAPI(title=settings.PROJECT_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup OpenTelemetry
from app.utils.telemetry import setup_telemetry
setup_telemetry(app)


class ChatRequest(BaseModel):
    message: str
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
    # Verify token
    await verify_token(token)
    
    return StreamingResponse(
        sse_manager.stream_events(session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

@app.post(settings.API_V1_STR + "/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, current_user: TokenData = Depends(get_current_user_token)):
    import logging
    import traceback
    logger = logging.getLogger(__name__)
    
    # Generate or use provided session ID
    session_id = request.session_id or str(uuid.uuid4())
    sse_manager.create_session(session_id)
    
    try:
        initial_state = {
            "question": request.message,
            "messages": [],
            "retry_count": 0,
            "session_id": session_id,
            "user_id": current_user.username,
            "user_role": current_user.role
        }
        result = await graph.ainvoke(initial_state)
        
        final_msg = result.get("messages", [""])[-1]
        response_text = final_msg if isinstance(final_msg, str) else final_msg.content
        
        # Check if query requires approval (HITL)
        if result.get("requires_approval") and result.get("approval_status") == "pending":
            # DO NOT close SSE session here. Keep it open for approval result.
            return ChatResponse(
                response=f"⚠️ This query requires approval as it accesses sensitive tables: {', '.join(result.get('sensitive_tables', []))}. Approval request ID: {result.get('approval_request_id')}",
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
        
        print(f"\n\n=== ERROR IN CHAT ENDPOINT ===")
        print(f"Error: {e}")
        print(f"Traceback:\n{traceback.format_exc()}")
        print(f"=== END ERROR ===\n\n")
        raise

@app.get("/health")
def health():
    return {"status": "ok"}

# ===== HITL Approval Endpoints =====

@app.post(settings.API_V1_STR + "/approve/{request_id}")
async def approve_query(request_id: str, token: TokenData = Depends(get_current_user_token)):
    """
    Approve a pending query. Requires authentication.
    """
    from fastapi import HTTPException
    
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
            result = conn.execute(text(approval_request.query))
            rows = [dict(row._mapping) for row in result]
        
        # Send real-time update to the user
        if approval_request.session_id:
            await sse_manager.send_event(
                session_id=approval_request.session_id,
                event_type="approval_result",
                data={
                     "response": f"✅ Query Approved! Executed SQL: {approval_request.query}",
                     "data": rows
                }
            )

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
    Reject a pending query. Requires authentication.
    """
    from fastapi import HTTPException
    
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
    Get all pending approval requests. Requires authentication.
    """
    pending = approval_manager.get_pending_requests()
    
    return {
        "count": len(pending),
        "requests": [req.to_dict() for req in pending]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

