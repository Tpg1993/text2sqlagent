import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config import settings
from langchain_openai import ChatOpenAI

print("Testing OpenAI connection...")
print(f"API Key (first 10 chars): {settings.OPENAI_API_KEY[:10]}...")
print(f"Model: {settings.LLM_MODEL}")

try:
    llm = ChatOpenAI(model=settings.LLM_MODEL, api_key=settings.OPENAI_API_KEY)
    response = llm.invoke("Say hello")
    print(f"\nSUCCESS: {response.content}")
except Exception as e:
    print(f"\nFAILED: {e}")
    import traceback
    print(traceback.format_exc())
