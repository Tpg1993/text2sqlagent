from app.utils.state import AgentState
from langchain_core.messages import AIMessage
import json

def format_node(state: AgentState):
    print("--- FORMAT ---")
    # If RAG
    if state.get("intent") == "rag":
        return {"messages": [state['rag_answer']]}
    
    # Check if this is a final failure after retries
    retry_count = state.get("retry_count", 0)
    if retry_count > 3 and state.get("error"):
        content = (
            f"❌ I attempted to generate the SQL query multiple times but encountered errors.\n\n"
            f"**Last Error:** {state.get('error')}\n\n"
            f"Please use the **Self-Correction** tool below to fix the query manually."
        )
        return {
            "messages": [AIMessage(content=content)],
            "failed_sql": state.get("sql_query", ""),
            "schema_context": state.get("schema_context", "")
        }

    # If General
    # If it was an RAG answer or general search answer, it's just the last message from the general_node (which contains the LLM response)
    if state.get("intent") == "general":
        # Note: state['messages'] contains the list of messages including the LLM's AIMessage
        return {"messages": [state['messages'][-1]]}

    # IF SQL
    if state.get("sql_result"):
        msg = f"Executed SQL: `{state['sql_query']}`"
    else:
        msg = f"Could not answer. Error: {state.get('error')}"
        
    return {"messages": [msg]}
