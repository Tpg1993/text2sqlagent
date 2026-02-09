import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "Agenthic Text2SQL & RAG"
    API_V1_STR: str = "/api/v1"
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Database
    SQLITE_URL: str = f"sqlite:///{BASE_DIR}/data/sales.db"
    
    # LLM
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    
    # RAG
    FAISS_INDEX_PATH: str = f"{BASE_DIR}/data/faiss_index"

settings = Settings()
