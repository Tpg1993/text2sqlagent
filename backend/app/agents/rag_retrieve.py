from app.utils.state import AgentState
from app.rag.retriever import get_retriever

def retrieve_node(state: AgentState):
    print("--- RETRIEVE ---")
    retriever = get_retriever()
    docs = retriever.invoke(state['question'])
    return {"documents": docs}
