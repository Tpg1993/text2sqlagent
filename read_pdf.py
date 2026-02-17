import os
import sys
from langchain_community.document_loaders import PyPDFLoader

def read_pdf():
    pdf_path = "backend/data/docs/support.pdf"
    if not os.path.exists(pdf_path):
        print("PDF not found")
        return
    
    loader = PyPDFLoader(pdf_path)
    docs = loader.load()
    for i, doc in enumerate(docs):
        print(f"--- Page {i+1} ---")
        print(doc.page_content)

if __name__ == "__main__":
    read_pdf()
