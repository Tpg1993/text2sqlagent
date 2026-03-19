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

from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    
    id = Column(String, primary_key=True, index=True) # UUID
    title = Column(String, default="New Chat")
    username = Column(String, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("chat_sessions.id"))
    role = Column(String) # 'user' or 'assistant'
    content = Column(Text)
    data = Column(JSON, nullable=True) # Optional SQL results
    chart = Column(JSON, nullable=True) # Optional Chart Spec
    feedback = Column(Integer, nullable=True) # +1 (upvote), -1 (downvote), None
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    session = relationship("ChatSession", back_populates="messages")
