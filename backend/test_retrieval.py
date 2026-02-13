from app.rag.retriever import get_retriever
from app.config import settings

print(f"Using FAISS index at: {settings.FAISS_INDEX_PATH}")
try:
    retriever = get_retriever()
    query = "What is the return policy?"
    print(f"Query: {query}")
    docs = retriever.invoke(query)
    print(f"Retrieved {len(docs)} documents.")
    for i, doc in enumerate(docs):
        print(f"--- Doc {i} ---")
        print(doc.page_content[:200] + "...")
except Exception as e:
    print(f"Error: {e}")
