from app.utils.state import AgentState
from app.sql.schema import get_schema_text

def fetch_schema_node(state: AgentState):
    """Fetches DB schema."""
    print("--- FETCH SCHEMA ---")
    
    # Security Check
    sec = state.get('security_context', {})
    role = sec.get('user_role', 'user')
    print(f"🔒 Schema Access Check: Role={role}")
    
    if role != 'admin':
        return {
            "error": "Access Denied: Only admins can access the database schema.",
            "schema": None
        }
        
    schema = get_schema_text()
    return {"schema": schema}
