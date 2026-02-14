from sqlalchemy import text
from app.utils.state import AgentState
from app.db.session import engine

def execute_node(state: AgentState):
    """Executes SQL."""
    print("--- EXECUTE ---")
    
    # Security Check
    sec = state.get('security_context', {})
    role = sec.get('user_role', 'user')
    print(f"🔒 Identity: {sec.get('current_agent')} | Role: {sec.get('role')} | UserRole: {role}")
    
    if role != 'admin':
         error_msg = "Access Denied: Only admins can execute SQL queries."
         print(f"⛔ {error_msg}")
         return {"sql_result": None, "error": error_msg}
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text(state['sql_query']))
            rows = [dict(row._mapping) for row in result]
            return {"sql_result": rows, "error": None}
    except Exception as e:
        return {"sql_result": None, "error": str(e)}
