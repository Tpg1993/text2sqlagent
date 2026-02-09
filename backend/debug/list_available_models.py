
from google import genai
import os
from app.config import settings

def list_models_to_file():
    print(f"Listing models with key: {settings.GOOGLE_API_KEY[:10]}...")
    
    try:
        # Try v1 first (Preferred)
        client = genai.Client(api_key=settings.GOOGLE_API_KEY, http_options={'api_version':'v1'})
        
        with open("available_models.txt", "w") as f:
            f.write("--- Models (v1) ---\n")
            count = 0
            for m in client.models.list():
                try:
                    # Just print the model object string representation or name
                    f.write(f"ID: {m.name} | Display: {getattr(m, 'display_name', 'N/A')}\n")
                    count += 1
                except Exception as loop_e:
                    f.write(f"Error processing model: {loop_e}\n")
            f.write(f"Total v1 models: {count}\n")
            
    except Exception as e:
        with open("available_models.txt", "a") as f:
            f.write(f"\nError listing v1: {e}\n")

    print("Model list written to 'available_models.txt'")

if __name__ == "__main__":
    list_models_to_file()
