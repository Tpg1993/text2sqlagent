from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON
from app.db.session import Base
from datetime import datetime, timezone

class Connection(Base):
    __tablename__ = "connections"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    db_type = Column(String) # sqlite, postgres, snowflake, etc.
    host = Column(String, nullable=True)
    port = Column(Integer, nullable=True)
    username = Column(String, nullable=True)
    password = Column(String, nullable=True)
    database = Column(String, nullable=True)

class SavedChart(Base):
    __tablename__ = "saved_charts"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    creator = Column(String)
    spec = Column(JSON)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    username = Column(String)
    query = Column(Text)
    intent = Column(String)
    blocked = Column(Boolean, default=False)
    pii_scrubbed = Column(Boolean, default=False)
