import os
import sys

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.rag.retriever import get_retriever
from app.config import settings

def test_retrieval(question):
    print(f"Testing retrieval for: {question}")
    try:
        retriever = get_retriever()
        docs = retriever.invoke(question)
        print(f"Found {len(docs)} documents.")
        for i, doc in enumerate(docs):
            print(f"\nDocument {i+1}:")
            print(doc.page_content[:500])
    except Exception as e:
        print(f"Error during retrieval: {e}")

if __name__ == "__main__":
    test_retrieval("shipping options")
