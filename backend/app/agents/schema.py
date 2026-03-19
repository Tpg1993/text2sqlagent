from app.utils.state import AgentState
from app.utils.schema_policy import get_schema_for_role

def fetch_schema_node(state: AgentState):
    """Fetches DB schema filtered by the current user's role (Semantic RBAC)."""
    print("--- FETCH SCHEMA ---")
    
    role = state.get('user_role', 'user')
    print(f"🔒 [Semantic RBAC] Fetching schema for role='{role}'")
    
    # Role-filtered schema: the LLM only sees tables the user is allowed to access
    schema = get_schema_for_role(role)
    print(f"📋 Schema injected: {len(schema.splitlines())} lines (role-filtered)")
    return {"schema": schema}
