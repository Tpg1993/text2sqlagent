import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.config import settings
from app.utils.pii import get_pii_scrubber

def ingest_pdf_file():
    # Hardcoded to data/docs/support.pdf for demo
    pdf_path = os.path.join(settings.BASE_DIR, "data/docs/support.pdf")
    
    if not os.path.exists(pdf_path):
        print(f"File {pdf_path} not found.")
        return

    loader = PyPDFLoader(pdf_path)
    docs = loader.load()
    
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splits = text_splitter.split_documents(docs)
    
    # ===== PII SCRUBBING =====
    # Anonymize PII before creating embeddings and storing in vector DB
    print("🔒 Scrubbing PII from documents...")
    pii_scrubber = get_pii_scrubber()
    pii_count = 0
    
    for doc in splits:
        original_content = doc.page_content
        scrubbed_content = pii_scrubber.scrub_text(original_content)
        
        # Count how many documents had PII
        if original_content != scrubbed_content:
            pii_count += 1
        
        doc.page_content = scrubbed_content
    
    print(f"✅ PII scrubbed from {pii_count}/{len(splits)} document chunks")
    
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001", 
        google_api_key=settings.GOOGLE_API_KEY
    )
    
    vectorstore = FAISS.from_documents(
        documents=splits, 
        embedding=embeddings
    )
    vectorstore.save_local(settings.FAISS_INDEX_PATH)
    print(f"Ingested {len(splits)} chunks into FAISS.")

if __name__ == "__main__":
    ingest_pdf_file()
