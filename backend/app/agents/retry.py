from app.utils.state import AgentState

def retry_node(state: AgentState):
    print("--- RETRY ---")
    return {"retry_count": state.get("retry_count", 0) + 1}
