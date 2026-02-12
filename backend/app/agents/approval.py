from app.utils.state import AgentState

def approval_pending_node(state: AgentState):
    """
    Node that handles queries awaiting approval.
    This node pauses execution and returns a pending status to the user.
    """
    print("--- APPROVAL PENDING ---")
    
    approval_request_id = state.get('approval_request_id')
    sensitive_tables = state.get('sensitive_tables', [])
    
    print(f"⏸️  [HITL] Query requires approval")
    print(f"   Request ID: {approval_request_id}")
    print(f"   Sensitive tables: {', '.join(sensitive_tables)}")
    
    # Return state indicating approval is pending
    # The main API will detect this and return appropriate response
    return {
        "error": None,  # Clear any previous errors
        "sql_result": None  # No results yet
    }
