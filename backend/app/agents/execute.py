from sqlalchemy import text
from app.utils.state import AgentState
from app.db.session import engine

def execute_node(state: AgentState):
    """Executes SQL."""
    print("--- EXECUTE ---")
    
    # Log user info (no restriction - all authenticated users can query)
    role = state.get('user_role', 'user')
    user_id = state.get('user_id', 'unknown')
    print(f"🔒 User: {user_id} | Role: {role}")
    
    try:
        with engine.connect() as conn:
            clean_query = state['sql_query'].replace('```sql', '').replace('```', '').strip().strip('"').strip("'")
            result = conn.execute(text(clean_query))
            rows = [dict(row._mapping) for row in result]
            return {"sql_result": rows, "error": None}
    except Exception as e:
        return {"sql_result": None, "error": str(e)}
