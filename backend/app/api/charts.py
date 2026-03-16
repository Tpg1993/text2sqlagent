from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import SavedChart
from app.auth.jwt import get_current_user_token, TokenData
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

router = APIRouter(prefix="/charts", tags=["charts"])

class SavedChartCreate(BaseModel):
    title: str
    spec: Dict[str, Any]

class SavedChartResponse(SavedChartCreate):
    id: int
    creator: str

@router.post("/", response_model=SavedChartResponse)
def create_chart(chart: SavedChartCreate, db: Session = Depends(get_db), token: TokenData = Depends(get_current_user_token)):
    db_chart = SavedChart(title=chart.title, spec=chart.spec, creator=token.username)
    db.add(db_chart)
    db.commit()
    db.refresh(db_chart)
    return db_chart

@router.get("/", response_model=List[SavedChartResponse])
def list_charts(db: Session = Depends(get_db), token: TokenData = Depends(get_current_user_token)):
    return db.query(SavedChart).all()

@router.delete("/{chart_id}", status_code=204)
def delete_chart(chart_id: int, db: Session = Depends(get_db), token: TokenData = Depends(get_current_user_token)):
    chart = db.query(SavedChart).filter(SavedChart.id == chart_id).first()
    if not chart:
        raise HTTPException(status_code=404, detail="Chart not found")
    if chart.creator != token.username and token.role != "admin":
        raise HTTPException(status_code=403, detail="Not allowed to delete this chart")
    db.delete(chart)
    db.commit()
