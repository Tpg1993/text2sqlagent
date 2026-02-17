from app.utils.state import AgentState
from app.sql.schema import get_schema_text

def fetch_schema_node(state: AgentState):
    """Fetches DB schema."""
    print("--- FETCH SCHEMA ---")
    
    # Log user info (no restriction - all authenticated users can access schema)
    role = state.get('user_role', 'user')
    print(f"🔒 Schema Access: Role={role}")
        
    schema = get_schema_text()
    return {"schema": schema}
