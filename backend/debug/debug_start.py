import sys
import traceback

try:
    print("Attempting to import app.main...")
    from app.main import app
    print("Import successful!")
except Exception:
    traceback.print_exc()
except ImportError:
    traceback.print_exc()
