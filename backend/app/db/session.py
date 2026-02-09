from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings
from typing import Generator

# Ensure the DB URL is correct. SQLite requires 3 slashes for relative, 4 for absolute.
# settings.SQLITE_URL is constructed carefully.
engine = create_engine(
    settings.SQLITE_URL,
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
