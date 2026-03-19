from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings
from typing import Generator

# Main app DB (text2sql.db): stores audit logs, chat sessions, saved charts, etc.
engine = create_engine(
    settings.SQLITE_URL,
    connect_args={"check_same_thread": False}
)

# Analytics data DB (sales.db): the customer's data that agents run SQL on
data_engine = create_engine(
    settings.DATA_DB_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db() -> Generator:
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()
