from google import genai
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
print(f"API Key (first 15 chars): {api_key[:15]}...")

try:
    client = genai.Client(api_key=api_key, http_options={'api_version':'v1'})
    
    print("\nTesting Gemini API...")
    response = client.models.generate_content(
        model="gemini-1.5-flash",
        contents="What is 2+2? Answer in one word."
    )
    
    print(f"✅ SUCCESS!")
    print(f"Response: {response.text}\n")
    
except Exception as e:
    print(f"❌ FAILED: {e}\n")
    import traceback
    print(traceback.format_exc())
