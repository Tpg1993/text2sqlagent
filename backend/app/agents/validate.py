from app.utils.state import AgentState

def validate_node(state: AgentState):
    """Validates SQL (Basic)."""
    print("--- VALIDATE ---")
    sql = state['sql_query'].upper()
    if "DROP" in sql or "DELETE" in sql or "UPDATE" in sql or "ALTER" in sql:
        return {"sql_valid": False, "error": "Unsafe SQL detected."}
    return {"sql_valid": True}
