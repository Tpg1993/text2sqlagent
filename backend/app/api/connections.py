import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.db.session import get_db, engine
from app.db.models import Connection
from app.auth.jwt import get_current_user_token, TokenData
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/connections", tags=["connections"])

class ConnectionCreate(BaseModel):
    name: str
    db_type: str
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    database: Optional[str] = None

class ConnectionResponse(ConnectionCreate):
    id: int

@router.post("/", response_model=ConnectionResponse)
def create_connection(conn: ConnectionCreate, db: Session = Depends(get_db), token: TokenData = Depends(get_current_user_token)):
    if token.role != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")
    db_conn = Connection(**conn.dict())
    db.add(db_conn)
    db.commit()
    db.refresh(db_conn)
    return db_conn

@router.get("/", response_model=List[ConnectionResponse])
def list_connections(db: Session = Depends(get_db)):
    # Everyone can list connections for now
    return db.query(Connection).all()

@router.post("/csv")
def upload_csv(
    file: UploadFile = File(...),
    token: TokenData = Depends(get_current_user_token)
):
    """
    Turns a CSV into a SQLite table dynamically.
    """
    if token.role != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")
        
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Must be a CSV file")
        
    try:
        # Table name will be filename without extension, sanitized
        table_name = file.filename.replace(".csv", "").replace(" ", "_").replace("-", "_").lower()
        
        # Read CSV into pandas directly from the UploadFile
        df = pd.read_csv(file.file)
        
        # Save securely to our main SQLite database
        df.to_sql(name=table_name, con=engine, if_exists="replace", index=False)
        
        return {
            "message": f"Successfully imported '{file.filename}' into table '{table_name}'.",
            "table_name": table_name,
            "columns": list(df.columns),
            "row_count": len(df)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
