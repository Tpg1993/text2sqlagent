from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_classic.retrievers import EnsembleRetriever
from langchain_classic.retrievers.contextual_compression import ContextualCompressionRetriever
from app.config import settings
import os
import pickle

def get_retriever():
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-2-preview",
        google_api_key=settings.GOOGLE_API_KEY
    )
    
    # 1. FAISS Retriever (Semantic)
    try:
        vectorstore = FAISS.load_local(
            folder_path=settings.FAISS_INDEX_PATH, 
            embeddings=embeddings,
            allow_dangerous_deserialization=True # Required for local files
        )
        faiss_retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
    except RuntimeError:
        print("FAISS index not found. Please run ingest first.")
        raise
        
    # 2. BM25 Retriever (Keyword)
    bm25_path = os.path.join(settings.BASE_DIR, "data", "bm25_index.pkl")
    if os.path.exists(bm25_path):
        with open(bm25_path, "rb") as f:
            bm25_retriever = pickle.load(f)
        bm25_retriever.k = 5
        
        # Combine FAISS + BM25
        base_retriever = EnsembleRetriever(
            retrievers=[bm25_retriever, faiss_retriever], weights=[0.4, 0.6]
        )
    else:
        print("BM25 index not found, falling back to FAISS only.")
        base_retriever = faiss_retriever
        
    # 3. FlashRank Reranker (optional — may have Pydantic v2 compatibility issues)
    try:
        from langchain_community.document_compressors.flashrank_rerank import FlashrankRerank
        compressor = FlashrankRerank(top_n=3)
        return ContextualCompressionRetriever(
            base_compressor=compressor, base_retriever=base_retriever
        )
    except Exception as e:
        print(f"Warning: FlashrankRerank failed to initialize ({e}). Using base retriever without re-ranking.")
        return base_retriever
