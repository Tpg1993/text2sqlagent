import pytest
from app.utils.state import AgentState
from app.agents.orchestrator import orchestrator_node
from app.agents.validate import validate_node
from app.agents.format import format_node

# --- Orchestrator Tests ---
def test_orchestrator_routing_sql(mock_llm_calls):
    """Test that unrelated questions route to General, but specific ones might route to SQL/RAG based on mock."""
    # Configure mock to return "sql" for sales questions
    mock_llm_calls.side_effect = lambda *args, **kwargs: "sql"
    
    state = {"question": "Show me total sales"}
    result = orchestrator_node(state)
    assert result["intent"] == "sql"

def test_orchestrator_routing_rag(mock_llm_calls):
    # Configure mock to return "rag" for policy questions
    mock_llm_calls.side_effect = lambda *args, **kwargs: "rag"
    
    state = {"question": "What is the return policy?"}
    result = orchestrator_node(state)
    assert result["intent"] == "rag"

# --- Validate Tests ---
def test_validate_safe_sql():
    state = {"sql_query": "SELECT * FROM users"}
    result = validate_node(state)
    assert result["sql_valid"] == True
    assert result["requires_approval"] == False

def test_validate_unsafe_sql():
    state = {"sql_query": "DROP TABLE users"}
    result = validate_node(state)
    assert result["sql_valid"] == False
    assert "Unsafe SQL" in result["error"]

def test_validate_sensitive_table(mocker):
    # Mock approval manager to return True for sensitivity
    mocker.patch("app.utils.hitl.approval_manager.is_query_sensitive", return_value=(True, ["salaries"]))
    mocker.patch("app.utils.hitl.approval_manager.create_approval_request", return_value=mocker.Mock(request_id="123"))
    
    state = {"sql_query": "SELECT * FROM salaries", "user_id": "test_user"}
    result = validate_node(state)
    
    assert result["sql_valid"] == True
    assert result["requires_approval"] == True
    assert result["approval_status"] == "pending"

# --- Format Tests ---
def test_format_rag_response():
    state = {"intent": "rag", "rag_answer": "This is the policy."}
    result = format_node(state)
    assert result["messages"] == ["This is the policy."]

def test_format_sql_response():
    state = {"intent": "sql", "sql_result": [{"total": 100}], "sql_query": "SELECT 100"}
    result = format_node(state)
    assert "Executed SQL" in result["messages"][0]
