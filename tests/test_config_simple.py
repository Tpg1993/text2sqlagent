import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend'))

from app.config import settings

print("=" * 60)
print("Environment-Aware Configuration Test")
print("=" * 60)
print(f"Environment: {'Kubernetes' if settings.is_kubernetes else 'Local'}")
print(f"Local Mode: {settings.is_local}")
print(f"OPENAI_API_KEY: {'Set' if settings.OPENAI_API_KEY else 'Not set'}")
print(f"GOOGLE_API_KEY: {'Set' if settings.GOOGLE_API_KEY else 'Not set'}")
print(f"LLM_MODEL: {settings.LLM_MODEL}")
print(f"GEMINI_MODEL: {settings.GEMINI_MODEL}")
print(f"BASE_DIR: {settings.BASE_DIR}")
print("=" * 60)
print("Test completed successfully!")
