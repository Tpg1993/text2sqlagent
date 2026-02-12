from app.utils.state import AgentState
from app.rag.retriever import get_retriever

def retrieve_node(state: AgentState):
    """Retrieves documents from vector store."""
    print("--- RAG RETRIEVE ---")
    
    # Security Check
    sec = state.get('security_context', {})
    print(f"🔒 Identity: {sec.get('current_agent')} | Role: {sec.get('role')}")
    
    try:
        retriever = get_retriever()
        docs = retriever.invoke(state['question'])
        return {"documents": docs}
    except Exception as e:
        print(f"Warning: RAG retrieval failed: {e}")
        print("Returning empty results - FAISS index may be missing")
        return {"documents": []}
