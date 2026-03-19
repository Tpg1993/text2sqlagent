from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List

from app.db.session import SessionLocal
from app.db.models import ChatSession, ChatMessage
from app.auth.jwt import get_current_user_token, TokenData

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/chat/sessions")
async def get_sessions(
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user_token)
):
    sessions = db.query(ChatSession).filter(
        ChatSession.username == current_user.username
    ).order_by(desc(ChatSession.updated_at)).all()
    
    return [
        {"id": s.id, "title": s.title, "updated_at": s.updated_at}
        for s in sessions
    ]

@router.get("/chat/sessions/{session_id}")
async def get_session_history(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user_token)
):
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.username == current_user.username
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    messages = db.query(ChatMessage).filter(
        ChatMessage.session_id == session_id
    ).order_by(ChatMessage.created_at).all()
    
    return [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "data": m.data,
            "chart": m.chart,
            "feedback": m.feedback,
            "created_at": m.created_at
        }
        for m in messages
    ]

@router.post("/chat/messages/{message_id}/feedback")
async def submit_feedback(
    message_id: int,
    feedback: dict, # {"feedback": 1 or -1}
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user_token)
):
    val = feedback.get("feedback")
    if val not in [1, -1, None]:
         raise HTTPException(status_code=400, detail="Feedback must be 1 or -1")
         
    message = db.query(ChatMessage).filter(ChatMessage.id == message_id).first()
    if not message:
         raise HTTPException(status_code=404, detail="Message not found")
         
    # verify ownership
    session = db.query(ChatSession).filter(ChatSession.id == message.session_id).first()
    if not session or session.username != current_user.username:
         raise HTTPException(status_code=403, detail="Not authorized")
         
    message.feedback = val
    db.commit()
    return {"status": "success"}
