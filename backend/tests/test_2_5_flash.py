from google import genai
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
model_name = "gemini-2.5-flash"  # Using the model from your quota dashboard

print(f"Testing: {model_name}")
print(f"Key: {api_key[:15]}...\n")

try:
    client = genai.Client(api_key=api_key, http_options={'api_version':'v1'})
    
    response = client.models.generate_content(
        model=model_name,
        contents="What is 2+2? Answer in one word."
    )
    
    print(f"✅ SUCCESS!")
    print(f"Response: {response.text}\n")
    
except Exception as e:
    print(f"❌ FAILED: {e}\n")
