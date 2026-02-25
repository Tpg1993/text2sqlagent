# Minimal PDF generator using fpdf if available or just simple text
# Since we don't know if fpdf is installed, we'll try to use reportlab if installed or just write a text file 
# BUT the user wants PDF. 
# We'll just write a text file and user can verify with that if they change loader.
# OR we assume user provides PDF.
# Let's try to make a dummy PDF with raw bytes if possible, but that's risky.

# Let's clean up dependencies: add reportlab
from reportlab.pdfgen import canvas
import os
from app.config import settings

def create_sample_pdf():
    pdf_path = os.path.join(settings.BASE_DIR, "data/docs/support.pdf")
    c = canvas.Canvas(pdf_path)
    c.drawString(100, 750, "Agentic Support Policy")
    c.drawString(100, 730, "1. Returns: You can return items within 30 days.")
    c.drawString(100, 710, "2. Refunds: Processed within 5-7 business days.")
    c.drawString(100, 690, "3. Shipping: Free shipping on orders over $100.")
    c.drawString(100, 670, "4. Contact: For support, email support@agentic.com or call 1-800-AGENTIC.")
    c.save()
    print(f"Created {pdf_path}")

if __name__ == "__main__":
    create_sample_pdf()
