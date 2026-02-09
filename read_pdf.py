import sys
import os
sys.path.append(os.path.abspath("backend"))
from pypdf import PdfReader

try:
    reader = PdfReader("backend/data/docs/support.pdf")
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    
    print(text[:1000]) # Print first 1000 chars
except Exception as e:
    print(f"Error reading PDF: {e}")
