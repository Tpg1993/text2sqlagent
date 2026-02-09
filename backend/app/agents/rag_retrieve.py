from app.utils.state import AgentState
from app.rag.retriever import get_retriever

def retrieve_node(state: AgentState):
    """Retrieves documents from vector store."""
    print("--- RAG RETRIEVE ---")
    try:
        retriever = get_retriever()
        docs = retriever.invoke(state['question'])
        return {"retrieved_docs": docs}
    except Exception as e:
        print(f"Warning: RAG retrieval failed: {e}")
        print("Returning empty results - FAISS index may be missing")
        return {"retrieved_docs": []}
