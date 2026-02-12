from sqlalchemy import text
from app.utils.state import AgentState
from app.db.session import engine

def execute_node(state: AgentState):
    """Executes SQL."""
    print("--- EXECUTE ---")
    
    # Security Check
    sec = state.get('security_context', {})
    print(f"🔒 Identity: {sec.get('current_agent')} | Role: {sec.get('role')}")
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text(state['sql_query']))
            rows = [dict(row._mapping) for row in result]
            return {"sql_result": rows, "error": None}
    except Exception as e:
        return {"sql_result": None, "error": str(e)}
