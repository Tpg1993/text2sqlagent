from app.utils.state import AgentState
from app.sql.schema import get_schema_text

def fetch_schema_node(state: AgentState):
    """Fetches DB schema."""
    print("--- FETCH SCHEMA ---")
    schema = get_schema_text()
    return {"schema": schema}
