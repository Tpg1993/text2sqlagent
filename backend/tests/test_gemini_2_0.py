from google import genai
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

print(f"API Key (first 15 chars): {api_key[:15]}...")
print(f"Testing Model: {model_name}")

try:
    # Try w/o http_options first as per previous finding
    client = genai.Client(api_key=api_key, http_options={'api_version':'v1'})
    
    print("\nGenerating content...")
    response = client.models.generate_content(
        model=model_name,
        contents="What is 2+2? Answer in one word."
    )
    
    print(f"✅ SUCCESS!")
    print(f"Response: {response.text}\n")
    
except Exception as e:
    print(f"❌ FAILED: {e}\n")
    import traceback
    print(traceback.format_exc())
