
import os
import sys
from app.config import settings
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_connections():
    print("--- DIAGNOSTICS ---")
    
    # 2. Test Gemini
    print(f"\n2. Testing Gemini ({settings.GEMINI_MODEL})...")
    try:
        if not settings.GOOGLE_API_KEY:
            print("SKIP: GOOGLE_API_KEY not set.")
        else:
            llm = ChatGoogleGenerativeAI(
                model="models/gemini-1.5-flash", 
                google_api_key=settings.GOOGLE_API_KEY,
                convert_system_message_to_human=True
            )
            resp = llm.invoke([HumanMessage(content="Hello")])
            print("PASS: Gemini response received:", resp.content)
    except Exception as e:
        print(f"FAIL: Gemini failed: {e}")

if __name__ == "__main__":
    test_connections()
