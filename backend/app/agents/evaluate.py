from app.utils.state import AgentState

def evaluate_node(state: AgentState):
    """Evaluates result."""
    print("--- EVALUATE ---")
    
    # Check for DB execution errors
    if state['error']:
        return {"sql_valid": False}
        
    # Check for Empty Data
    rows = state.get('sql_result', [])
    if isinstance(rows, list) and len(rows) == 0:
        # We treat empty results as a "soft error" to trigger regeneration
        # unless it's a retry limit (handled by graph layer)
        print("Empty result detected. Triggering retry.")
        return {
            "sql_valid": False, 
            "error": "Query returned no data. It might be too restrictive or incorrect."
        }
        
    return {"sql_valid": True}
