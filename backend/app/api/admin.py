from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.session import get_db
from app.db.models import AuditLog
from app.auth.jwt import get_current_user_token, TokenData

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/analytics")
def get_analytics(db: Session = Depends(get_db), token: TokenData = Depends(get_current_user_token)):
    if token.role != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")
        
    total_queries = db.query(func.count(AuditLog.id)).scalar()
    blocked_count = db.query(func.count(AuditLog.id)).filter(AuditLog.blocked == True).scalar()
    pii_count = db.query(func.count(AuditLog.id)).filter(AuditLog.pii_scrubbed == True).scalar()
    
    # Intent breakdown
    intent_counts = db.query(
        AuditLog.intent, func.count(AuditLog.id).label("count")
    ).group_by(AuditLog.intent).all()
    
    intents = {item.intent or 'unknown': item.count for item in intent_counts}
    
    # Recent logs
    recent_logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(20).all()
    
    return {
        "metrics": {
            "total_queries": total_queries,
            "blocked_count": blocked_count,
            "pii_count": pii_count
        },
        "intents": [{"name": k, "value": v} for k, v in intents.items()],
        "recent_logs": [
            {
                "id": log.id,
                "timestamp": log.timestamp,
                "username": log.username,
                "query": log.query,
                "intent": log.intent,
                "blocked": log.blocked,
                "pii_scrubbed": log.pii_scrubbed
            } for log in recent_logs
        ]
    }
