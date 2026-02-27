from app.utils.state import AgentState
from app.utils.hitl import approval_manager

def validate_node(state: AgentState):
    """Validates SQL and checks for sensitive table access."""
    print("--- VALIDATE ---")
    sql = state['sql_query']
    sql_upper = sql.upper()
    
    # Check for destructive operations
    if "DROP" in sql_upper or "DELETE" in sql_upper or "UPDATE" in sql_upper or "ALTER" in sql_upper:
        return {"sql_valid": False, "error": "Unsafe SQL detected."}
        
    # Strict Schema Validation (Hallucination Mitigation)
    from app.sql.schema import get_valid_tables_and_columns
    import re
    
    valid_schema = get_valid_tables_and_columns()
    valid_tables = list(valid_schema.keys())
    
    # Very basic parsing to find potential table names (words following FROM or JOIN)
    # This is a naive heuristic but works well for basic to intermediate queries
    matches = re.findall(r'(?:FROM|JOIN)\s+([a-zA-Z0-9_]+)', sql_upper)
    for match in matches:
        table_name = match.lower()
        if table_name not in valid_tables:
            error_msg = f"Hallucination Detected: Table '{table_name}' does not exist in the database schema."
            print(f"❌ {error_msg}")
            return {"sql_valid": False, "error": error_msg}
    
    # Check if query touches sensitive tables (HITL)
    is_sensitive, sensitive_tables = approval_manager.is_query_sensitive(sql)
    
    if is_sensitive:
        print(f"⚠️  [HITL] Sensitive query detected: {', '.join(sensitive_tables)}")
        # Create approval request
        approval_request = approval_manager.create_approval_request(
            query=sql,
            sensitive_tables=sensitive_tables,
            user_id=state.get('user_id'),
            session_id=state.get('session_id')
        )
        
        return {
            "sql_valid": True,  # SQL is valid, but requires approval
            "requires_approval": True,
            "approval_status": "pending",
            "approval_request_id": approval_request.request_id,
            "sensitive_tables": sensitive_tables
        }
    
    # Query is safe and doesn't require approval
    return {
        "sql_valid": True,
        "requires_approval": False
    }

