import sys
import os

# Add the backend directory to sys.path so we can import app modules
sys.path.append(os.path.abspath("backend"))

try:
    from app.config import settings
    print(f"LLM_MODEL in settings: {settings.LLM_MODEL}")
    
    if settings.LLM_MODEL != "gpt-4o-mini":
        print("ERROR: LLM_MODEL is not gpt-4o-mini")
        sys.exit(1)

    print("Importing agents to check for initialization errors...")
    from app.sql import generator
    from app.agents import rag_generate
    from app.agents import orchestrator
    from app.agents import chart
    
    print("All imports successful.")
    
except Exception as e:
    print(f"Verification FAILED with error: {e}")
    sys.exit(1)
