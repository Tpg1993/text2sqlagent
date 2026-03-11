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
    # Everyone can see charts
    return db.query(SavedChart).all()
