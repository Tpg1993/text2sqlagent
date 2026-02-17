import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load .env file for local development
load_dotenv()

class Config:
    """
    Environment-aware configuration.
    Automatically detects if running locally or in Kubernetes and loads secrets accordingly.
    
    Priority for secret loading:
    1. Kubernetes mounted secrets (/mnt/secrets/<key>) - if in K8s
    2. Environment variables - works everywhere
    3. Default values
    """
    
    def __init__(self):
        # Auto-detect Kubernetes environment
        # Kubernetes automatically sets this env var in all pods
        self.is_kubernetes = os.getenv("KUBERNETES_SERVICE_HOST") is not None
        
        # Allow manual override via LOCAL_MODE env var
        # Set LOCAL_MODE=false in K8s to explicitly use K8s secrets
        local_mode_override = os.getenv("LOCAL_MODE", "").lower()
        if local_mode_override:
            self.is_local = local_mode_override == "true"
        else:
            self.is_local = not self.is_kubernetes
        
        # Base directory
        self.BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Load all configuration
        self._load_config()
    
    def get_secret(self, key: str, default: Optional[str] = None) -> str:
        """
        Fetch secret from appropriate source based on environment.
        
        Args:
            key: Secret key name
            default: Default value if secret not found
            
        Returns:
            Secret value
            
        Raises:
            ValueError: If secret not found and no default provided
        """
        # Try Kubernetes mounted secret first (if in K8s and not local mode)
        if not self.is_local and self.is_kubernetes:
            secret_path = Path(f"/mnt/secrets/{key}")
            if secret_path.exists():
                value = secret_path.read_text().strip()
                if value:
                    return value
        
        # Fallback to environment variable (works in both local and K8s)
        value = os.getenv(key)
        if value:
            return value
        
        # Return default if provided
        if default is not None:
            return default
        
        # Raise error if secret not found and no default
        raise ValueError(
            f"Secret '{key}' not found. "
            f"Environment: {'Kubernetes' if self.is_kubernetes else 'Local'}, "
            f"Local Mode: {self.is_local}"
        )
    
    def _load_config(self):
        """Load all configuration values."""
        # Project metadata
        self.PROJECT_NAME = "Agenthic Text2SQL & RAG"
        self.API_V1_STR = "/api/v1"
        
        # Secrets (API Keys)
        self.OPENAI_API_KEY = self.get_secret("OPENAI_API_KEY", default="")
        self.GOOGLE_API_KEY = self.get_secret("GOOGLE_API_KEY", default="")
        self.LANGCHAIN_API_KEY = self.get_secret("LANGCHAIN_API_KEY", default="")
        
        # Database
        self.SQLITE_URL = f"sqlite:///{self.BASE_DIR}/data/sales.db"
        
        # LLM Configuration
        self.LLM_MODEL = self.get_secret("LLM_MODEL", default="gpt-4o-mini")
        self.GEMINI_MODEL = self.get_secret("GEMINI_MODEL", default="gemini-2.0-flash")
        
        # RAG
        self.FAISS_INDEX_PATH = f"{self.BASE_DIR}/data/faiss_index"
        
        # Monitoring (OpenTelemetry & LangSmith)
        self.LANGCHAIN_TRACING_V2 = self.get_secret("LANGCHAIN_TRACING_V2", default="false")
        self.LANGCHAIN_ENDPOINT = self.get_secret("LANGCHAIN_ENDPOINT", default="https://api.smith.langchain.com")
        self.LANGCHAIN_PROJECT = self.get_secret("LANGCHAIN_PROJECT", default="text2sql")
        
        self.OTEL_SERVICE_NAME = self.get_secret("OTEL_SERVICE_NAME", default="agenthic-text2sql-backend")
        self.OTEL_EXPORTER_OTLP_ENDPOINT = self.get_secret("OTEL_EXPORTER_OTLP_ENDPOINT", default="")
        
        # Auth
        # Auth
        # Fail if passwords not set (Security Best Practice)
        self.ADMIN_PASSWORD = self.get_secret("ADMIN_PASSWORD") 
        self.USER1_PASSWORD = self.get_secret("USER1_PASSWORD")

        # Rate Limit Feature Flags
        self.ENABLE_IP_RATE_LIMIT = self.get_secret("ENABLE_IP_RATE_LIMIT", default="true").lower() == "true"
        self.ENABLE_USER_RATE_LIMIT = self.get_secret("ENABLE_USER_RATE_LIMIT", default="true").lower() == "true"
        
        # Safety Limits
        self.MAX_AGENT_STEPS = int(self.get_secret("MAX_AGENT_STEPS", default="50"))

# Singleton instance
settings = Config()

