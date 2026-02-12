from typing import Any, Dict
from langchain_openai import ChatOpenAI
# from langchain_google_genai import ChatGoogleGenerativeAI # Deprecated/Broken for this key
from google import genai  # Required for direct API usage
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda
from app.config import settings
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from opentelemetry import trace

tracer = trace.get_tracer(__name__)

def invoke_chain_with_fallback(chain_factory, input_data: Dict[str, Any]) -> str:
    """
    Invokes a chain using Gemini (primary) with OpenAI as fallback.
    """
    with tracer.start_as_current_span("invoke_chain_with_fallback") as span:
        # Use Gemini as primary
        try:
            print(f"🔵 Using Gemini model {settings.GEMINI_MODEL}...")
            logger.info("Using Gemini as primary LLM...")
            
            if not settings.GOOGLE_API_KEY:
                raise ValueError("GOOGLE_API_KEY is not set")
            
            # Create a RunnableLambda that acts as the LLM
            def gemini_runner(prompt_value):
                # 1. Initialize Client
                client = genai.Client(api_key=settings.GOOGLE_API_KEY, http_options={'api_version':'v1'})
                
                # 2. Extract text from PromptValue (LangChain object)
                prompt_text = prompt_value.to_string()
                
                # 3. Call New SDK
                response = client.models.generate_content(
                    model=settings.GEMINI_MODEL,
                    contents=prompt_text
                )
                
                # 4. Return AIMessage for compatibility with StrOutputParser
                return AIMessage(content=response.text)
    
            # Wrap in RunnableLambda so it supports "|" operator
            llm = RunnableLambda(gemini_runner)
            
            chain = chain_factory(llm)
            result = chain.invoke(input_data)
            print(f"✅ Gemini response received")
            return result
            
        except Exception as e:
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR))
            print(f"❌ Gemini call failed: {e}")
            logger.error(f"Gemini call failed: {e}")
            
            # Check for Gemini Rate Limit
            gemini_retry_after = None
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                import re
                match = re.search(r"retryDelay': '([\d\.]+)s'", str(e))
                if match:
                    gemini_retry_after = match.group(1)
                
                # Fail FAST on Rate Limit: Do not try fallback
                from app.utils.exceptions import RateLimitException
                raise RateLimitException(
                    message=f"Rate limit exceeded. Please try again in {gemini_retry_after or '60'} seconds.",
                    retry_after=gemini_retry_after
                )
            
            # Fallback to OpenAI only if Gemini fails for other reasons (and not rate limit)
            # print(" Falling back to OpenAI...")
            # logger.info("Falling back to OpenAI...")
            
            # try:
            #     if not settings.OPENAI_API_KEY:
            #         raise ValueError("OPENAI_API_KEY is not set")
                    
            #     llm = ChatOpenAI(
            #         model=settings.LLM_MODEL, 
            #         temperature=0, 
            #         api_key=settings.OPENAI_API_KEY
            #     )
            #     chain = chain_factory(llm)
            #     return chain.invoke(input_data)
                
            # except Exception as openai_error:
            #     print(f"❌ OpenAI fallback also failed: {openai_error}")
            #     logger.error(f"OpenAI fallback failed: {openai_error}")
                
            #     # If we had a Gemini rate limit (redundant check but safe)
            #     if gemini_retry_after:
            #         from app.utils.exceptions import RateLimitException
            #         raise RateLimitException(
            #             message=f"Rate limit exceeded. Please try again in {gemini_retry_after} seconds.",
            #             retry_after=gemini_retry_after
            #         )
                
            #     raise openai_error
            
            # If fallback is disabled, just re-raise the Gemini error
            raise e
