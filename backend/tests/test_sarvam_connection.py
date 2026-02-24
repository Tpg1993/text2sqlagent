import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.utils.llm import invoke_chain_with_fallback
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

def test_sarvam_initialization():
    print("--- DIAGNOSTICS for selected LLM_PROVIDER ---")
    print(f"Configured Provider: {settings.LLM_PROVIDER}")
    print(f"Configured Model: {settings.SARVAM_MODEL if settings.LLM_PROVIDER == 'sarvam' else (settings.LLM_MODEL if settings.LLM_PROVIDER == 'openai' else settings.GEMINI_MODEL)}")
    print(f"Sarvam API Key configured: {'YES' if settings.SARVAM_API_KEY and settings.SARVAM_API_KEY != 'ENTER_SARVAM_API_KEY_HERE' else 'NO'}")
    
    prompt = PromptTemplate.from_template("Say 'Hello, World!'")
    
    def create_chain(llm):
        return prompt | llm | StrOutputParser()
        
    try:
        if settings.LLM_PROVIDER == 'sarvam' and (not settings.SARVAM_API_KEY or settings.SARVAM_API_KEY == 'ENTER_SARVAM_API_KEY_HERE'):
             print("Skipping actual API call, API key not set.")
        else:
            result = invoke_chain_with_fallback(create_chain, {}, name="TestSarvam")
            print("PASS: Response:", result)
    except Exception as e:
        print(f"FAIL: {settings.LLM_PROVIDER} failed: {e}")

if __name__ == "__main__":
    test_sarvam_initialization()
