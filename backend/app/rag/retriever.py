from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from app.config import settings

def get_retriever():
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001",
        google_api_key=settings.GOOGLE_API_KEY
    )
    try:
        vectorstore = FAISS.load_local(
            folder_path=settings.FAISS_INDEX_PATH, 
            embeddings=embeddings,
            allow_dangerous_deserialization=True # Required for local files
        )
        return vectorstore.as_retriever(search_kwargs={"k": 3})
    except RuntimeError:
        # Index usually not found or empty
        print("FAISS index not found. Please run ingest first.")
        # Return a dummy retriever or empty one
        # For now, just raise or let it fail
        raise
