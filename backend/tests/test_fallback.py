import os
import sys
import logging

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.utils.llm import invoke_chain_with_fallback
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

logging.basicConfig(level=logging.INFO)

def test_fallback():
    print("--- DIAGNOSTICS for LLM Fallback ---")
    
    prompt = PromptTemplate.from_template("Say 'Fallback successful'")
    
    def create_chain(llm):
        return prompt | llm | StrOutputParser()
        
    try:
        result = invoke_chain_with_fallback(create_chain, {}, name="TestFallback")
        print("\n🏆 FINAL PASS: Response:", result)
    except Exception as e:
        print(f"\n❌ FINAL FAIL: All providers failed: {e}")

if __name__ == "__main__":
    test_fallback()
