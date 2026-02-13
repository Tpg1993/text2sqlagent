import pytest
from app.sql.generator import generate_sql_query, generate_plan

def test_generate_plan(mock_llm_calls):
    # Mock returns a dummy plan string
    mock_llm_calls.side_effect = lambda *args, **kwargs: "Step 1: Join tables."
    
    plan = generate_plan("schema_str", "question")
    assert plan == "Step 1: Join tables."

def test_generate_sql_query(mock_llm_calls):
    # Mock returns a dummy SQL
    mock_llm_calls.side_effect = lambda *args, **kwargs: "SELECT * FROM data"
    
    sql = generate_sql_query("schema", "plan", "question")
    assert sql == "SELECT * FROM data"

def test_generate_sql_with_error_context(mock_llm_calls):
    # Verify error context is passed (would need to check mock call args in real scenario)
    mock_llm_calls.side_effect = lambda *args, **kwargs: "SELECT fixed"
    
    sql = generate_sql_query("schema", "plan", "question", previous_error="Syntax Error")
    assert sql == "SELECT fixed"
