from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from app.graphs.agent_graph import graph
from app.config import settings

app = FastAPI(title=settings.PROJECT_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str
    data: Optional[List[Dict[str, Any]]] = None
    chart: Optional[Dict[str, Any]] = None

@app.post(settings.API_V1_STR + "/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    import logging
    import traceback
    logger = logging.getLogger(__name__)
    
    try:
        initial_state = {
            "question": request.message,
            "messages": [],
            "retry_count": 0
        }
        result = await graph.ainvoke(initial_state)
        
        final_msg = result.get("messages", [""])[-1]
        response_text = final_msg if isinstance(final_msg, str) else final_msg.content
        
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
