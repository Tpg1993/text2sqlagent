
import google.generativeai as genai
import os
from app.config import settings

def list_models():
    print(f"Checking key: {settings.GOOGLE_API_KEY[:10]}...")
    genai.configure(api_key=settings.GOOGLE_API_KEY)
    
    try:
        print("Listing 'flash' models...")
        found = False
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                if 'flash' in m.name:
                    print(f"FOUND: {m.name}")
                    found = True
        if not found:
            print("No 'flash' models found. Listing first 5 others:")
            i = 0
            for m in genai.list_models():
                 if 'generateContent' in m.supported_generation_methods and i < 5:
                     print(f"- {m.name}")
                     i += 1
    except Exception as e:
        print(f"Error listing models: {e}")

if __name__ == "__main__":
    list_models()
