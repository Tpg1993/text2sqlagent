from app.utils.state import AgentState

def format_node(state: AgentState):
    print("--- FORMAT ---")
    # If RAG
    if state.get("intent") == "rag":
        return {"messages": [state['rag_answer']]}
    
    # If General
    if state.get("intent") == "general":
        return {"messages": ["Hello! I am Agenthic, your data assistant. I can help you query the sales database or answer questions from our knowledge base."]}

    # IF SQL
    if state.get("sql_result"):
        msg = f"Executed SQL: `{state['sql_query']}`"
    else:
        msg = f"Could not answer. Error: {state.get('error')}"
        
    return {"messages": [msg]}
