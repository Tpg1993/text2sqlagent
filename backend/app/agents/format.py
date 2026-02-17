from app.utils.state import AgentState

def format_node(state: AgentState):
    print("--- FORMAT ---")
    # If RAG
    if state.get("intent") == "rag":
        return {"messages": [state['rag_answer']]}
    
    # If General
    if state.get("intent") == "general":
        # Return the last message from the general_node (which contains the LLM response)
        # Note: state['messages'] contains the list of messages including the LLM's AIMessage
        return {"messages": [state['messages'][-1]]}

    # IF SQL
    if state.get("sql_result"):
        msg = f"Executed SQL: `{state['sql_query']}`"
    else:
        msg = f"Could not answer. Error: {state.get('error')}"
        
    return {"messages": [msg]}
