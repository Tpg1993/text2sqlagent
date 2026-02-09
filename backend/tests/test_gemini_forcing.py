
import sys
import os
from unittest.mock import MagicMock, patch
from app.utils.llm import invoke_chain_with_fallback
from app.config import settings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_gemini_only():
    print("--- Testing Gemini ONLY (Disabling OpenAI) ---")
    
    # Define a simple factory mimicking the real app
    def chain_factory(llm):
        return ChatPromptTemplate.from_template("Answer briefly: {text}") | llm | StrOutputParser()

    # Save original key
    original_key = settings.OPENAI_API_KEY
    
    # Disable OpenAI Key to force fallback
    settings.OPENAI_API_KEY = "" 
    
    try:
        print("Invoking chain with NO OpenAI Key...")
        # asking a simple question
        res = invoke_chain_with_fallback(chain_factory, {"text": "What is the capital of France?"})
        print(f"\nFINAL RESULT: {res}")
        
    except Exception as e:
        print(f"\nTEST FAILED with error: {e}")
    finally:
        # Restore key just in case (though script ends anyway)
        settings.OPENAI_API_KEY = original_key

if __name__ == "__main__":
    test_gemini_only()
