import pytest
import sys
import os
from unittest.mock import MagicMock

# Add backend directory to path so we can import 'app'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

@pytest.fixture(autouse=True)
def mock_settings(monkeypatch):
    """Set dummy environment variables for testing."""
    monkeypatch.setenv("GOOGLE_API_KEY", "dummy_key")
    monkeypatch.setenv("OPENAI_API_KEY", "dummy_key")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./test.db")

@pytest.fixture(autouse=True)
def mock_llm_calls(mocker):
    """
    Globally mock invoke_chain_with_fallback to prevent ANY real LLM calls.
    Returns a MagicMock that tests can configure if needed.
    """
    mock_invoke = mocker.patch("app.utils.llm.invoke_chain_with_fallback")
    
    # Default behavior: return a generic string based on inputs if possible, 
    # or just a simple "MOCKED RESPONSE"
    def side_effect(chain_factory, input_data, name=None, tags=None):
        # We can implement simple logic to return different mocks based on 'name'
        if name == "Orchestrator Agent":
            # Return a valid intent based on question content
            q = input_data.get("question", "").lower()
            if "policy" in q or "return" in q: return "rag"
            if "sales" in q or "revenue" in q: return "sql"
            return "general"
        
        if name == "SQL Generator Agent":
            return "SELECT * FROM sales;"
            
        if name == "RAG Answer Generator":
            return "This is a mocked RAG answer about policy."
            
        if name == "Chart Generator Agent":
            return '{"type": "bar", "data": []}'
            
        return "MOCKED_LLM_RESPONSE"
        
    mock_invoke.side_effect = side_effect
    return mock_invoke
