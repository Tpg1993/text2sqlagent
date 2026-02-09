
import sys
import os
from unittest.mock import MagicMock, patch
from app.utils.llm import invoke_chain_with_fallback
from app.config import settings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_fallback_integration():
    print("--- Testing Fallback Integration with New SDK (v1) ---")
    
    def chain_factory(llm):
        return ChatPromptTemplate.from_template("Say {text}") | llm | StrOutputParser()

    # Corrupt OpenAI key to force fallback
    original_openai = settings.OPENAI_API_KEY
    settings.OPENAI_API_KEY = "invalid-key"
    
    try:
        print("Invoking chain (expecting fallback)...")
        res = invoke_chain_with_fallback(chain_factory, {"text": "hello"})
        print(f"Result: {res}")
        if res:
             print("PASS: Got response from fallback.")
    except Exception as e:
        print(f"FAIL: {e}")
    finally:
        settings.OPENAI_API_KEY = original_openai

if __name__ == "__main__":
    test_fallback_integration()
