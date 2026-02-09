
import google.generativeai as genai
import os
from app.config import settings

def test_direct():
    print(f"Testing Direct Gemini API with key: {settings.GOOGLE_API_KEY[:10]}...")
    genai.configure(api_key=settings.GOOGLE_API_KEY)
    
    model_name = "gemini-1.5-flash"
    print(f"Instantiating model: {model_name}")
    model = genai.GenerativeModel(model_name)
    
    try:
        response = model.generate_content("Hello, can you hear me?")
        print("PASS: Response received:")
        print(response.text)
    except Exception as e:
        print(f"FAIL: Direct generation failed: {e}")

if __name__ == "__main__":
    test_direct()
