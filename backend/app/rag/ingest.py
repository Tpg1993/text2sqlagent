import os
import io
import magic
import fitz # PyMuPDF
import pickle
from langchain_community.document_loaders import UnstructuredPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_community.retrievers import BM25Retriever
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.config import settings
from app.utils.pii import get_pii_scrubber

def secure_pdf_preprocessor(pdf_path: str) -> str:
    """
    Validates the PDF file signature and rebuilds it to strip malicious objects/macros.
    Returns the path to the sanitized PDF.
    """
    print(f"🛡️ Validating PDF signature for {pdf_path}...")
    
    # 1. Magic Number Validation
    file_type = magic.from_file(pdf_path, mime=True)
    if file_type != 'application/pdf':
        raise ValueError(f"Security Alert: File {pdf_path} spoofed extension. Detected MIME: {file_type}")
    
    # 2. Rebuild/Sanitize using PyMuPDF (Strips active content/macros)
    print("🧹 Sanitizing PDF and stripping metadata...")
    doc = fitz.open(pdf_path)
    
    # Save a sanitized version to a safe temp path
    sanitized_path = pdf_path.replace(".pdf", "_sanitized.pdf")
    doc.save(sanitized_path, garbage=4, deflate=True, clean=True)
    doc.close()
    
    return sanitized_path

def ingest_pdf_file(file_path: str = None):
    # Hardcoded to data/docs/support.pdf for demo if not provided
    original_pdf_path = file_path or os.path.join(settings.BASE_DIR, "data/docs/support.pdf")
    
    if not os.path.exists(original_pdf_path):
        print(f"File {original_pdf_path} not found.")
        return

    try:
        pdf_path = secure_pdf_preprocessor(original_pdf_path)
    except Exception as e:
        print(f"🚨 Ingestion Aborted: {e}")
        return

    print("📄 Loading PDF with Unstructured...")
    loader = UnstructuredPDFLoader(pdf_path, mode="elements")
    docs = loader.load()
    
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splits = text_splitter.split_documents(docs)
    
    # ===== PII SCRUBBING =====
    # Anonymize PII before creating embeddings and storing in vector DB
    print("🔒 Scrubbing PII from documents...")
    pii_scrubber = get_pii_scrubber()
    pii_count = 0
    
    original_filename = os.path.basename(original_pdf_path)
    
    for doc in splits:
        original_content = doc.page_content
        scrubbed_content = pii_scrubber.scrub_text(original_content)
        
        # Count how many documents had PII
        if original_content != scrubbed_content:
            pii_count += 1
        
        doc.page_content = scrubbed_content
        doc.metadata["source"] = original_filename
    
    print(f"✅ PII scrubbed from {pii_count}/{len(splits)} document chunks")
    
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-2-preview", 
        google_api_key=settings.GOOGLE_API_KEY
    )
    
    vectorstore = FAISS.from_documents(
        documents=splits, 
        embedding=embeddings
    )
    vectorstore.save_local(settings.FAISS_INDEX_PATH)
    print(f"Ingested {len(splits)} chunks into FAISS.")

    print("🔍 Creating BM25 Index for Hybrid Search...")
    bm25_retriever = BM25Retriever.from_documents(splits)
    bm25_path = os.path.join(settings.BASE_DIR, "data", "bm25_index.pkl")
    with open(bm25_path, "wb") as f:
        pickle.dump(bm25_retriever, f)
    print("✅ Saved BM25 Index to data/bm25_index.pkl")

    # Clean up the sanitized temp PDF — prevents accumulation of *_sanitized*.pdf files
    if pdf_path != original_pdf_path and os.path.exists(pdf_path):
        os.remove(pdf_path)
        print(f"🧹 Removed sanitized temp file: {pdf_path}")

if __name__ == "__main__":
    ingest_pdf_file()
