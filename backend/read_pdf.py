from langchain_community.document_loaders import PyPDFLoader
import os

pdf_path = "data/docs/support.pdf"
if os.path.exists(pdf_path):
    loader = PyPDFLoader(pdf_path)
    docs = loader.load()
    for doc in docs:
        print(doc.page_content)
else:
    print("PDF not found")
