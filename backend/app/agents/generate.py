from app.utils.state import AgentState
from app.sql.generator import generate_sql_query

def generate_node(state: AgentState):
    """Generates SQL."""
    print("--- GENERATE SQL ---")
    
    # Security Check
    sec = state.get('security_context', {})
    print(f"🔒 Identity: {sec.get('current_agent')} | Role: {sec.get('role')}")
    
    
    # Extract error context if this is a retry
    previous_error = state.get("error")
    previous_query = state.get("sql_query")
    
    # If we are retrying, we might want to clear the error in the new state,
    # but for generation we need it. The graph state update will merge the new 'sql_query'
    # and we can clear 'error' here or let the validate node handle it.
    # Usually returning {"error": None} clears it.
    
    sql, pid = generate_sql_query(
        schema=state['schema'], 
        plan=state.get('plan', "Directly translate the question to SQL based on the schema."), 
        question=state['question'],
        previous_error=previous_error,
        previous_query=previous_query,
        metadata={"session_id": state.get("session_id")},
        return_provider=True
    )
    
    return {
        "sql_query": sql,
        "llm_used": pid,
        "error": None # Clear error on new generation
    }
