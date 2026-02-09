
from google import genai
import os
from app.config import settings

def debug_sdk():
    print(f"Debug New SDK with key: {settings.GOOGLE_API_KEY[:10]}...")
    
    # Try default (v1)
    client = genai.Client(api_key=settings.GOOGLE_API_KEY)
    
    print("\n--- Listing Models (v1) ---")
    try:
        # Pager object, iterate to get models
        for m in client.models.list():
            if "flash" in m.name:
                print(f"Found: {m.name} -> {m.display_name}")
    except Exception as e:
        print(f"Error listing: {e}")

    # Try explicit v1beta
    print("\n--- Listing Models (v1beta) ---")
    try:
        client_beta = genai.Client(api_key=settings.GOOGLE_API_KEY, http_options={'api_version':'v1beta'})
        for m in client_beta.models.list():
            if "flash" in m.name:
                print(f"CONFIRMED_MODEL: {m.name}")
                with open("model_name.txt", "w") as f:
                    f.write(m.name)
                return # Exit after first match
    except Exception as e:
        print(f"Error listing beta: {e}")

if __name__ == "__main__":
    debug_sdk()
