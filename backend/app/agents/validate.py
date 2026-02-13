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

