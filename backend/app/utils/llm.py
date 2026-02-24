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

def invoke_chain_with_fallback(chain_factory, input_data: Dict[str, Any], name: str = "LLM Chain", tags: list = None, metadata: Dict[str, Any] = None) -> str:
    """
    Invokes a chain using Gemini (primary) with OpenAI as fallback.
    Supports LangSmith tracing with custom name and tags.
    """
    tags = tags or []
    metadata = metadata or {}
    
    # Merge default metadata
    default_metadata = {"tags": tags, "agent": name}
    metadata.update(default_metadata)
    
    with tracer.start_as_current_span(name) as span:
        def get_sarvam():
            if not settings.SARVAM_API_KEY or settings.SARVAM_API_KEY == "ENTER_SARVAM_API_KEY_HERE":
                raise ValueError("SARVAM_API_KEY is not set")
            print(f"🔵 Using Sarvam model {settings.SARVAM_MODEL}...")
            logger.info("Using Sarvam as LLM...")
            return ChatOpenAI(
                model=settings.SARVAM_MODEL, temperature=0,
                api_key=settings.SARVAM_API_KEY, base_url="https://api.sarvam.ai/v1"
            )

        def get_openai():
            if not settings.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY is not set")
            print(f"🔵 Using OpenAI model {settings.LLM_MODEL}...")
            logger.info("Using OpenAI as LLM...")
            return ChatOpenAI(
                model=settings.LLM_MODEL, temperature=0, api_key=settings.OPENAI_API_KEY
            )

        def get_gemini():
            if not settings.GOOGLE_API_KEY:
                raise ValueError("GOOGLE_API_KEY is not set")
            print(f"🔵 Using Gemini model {settings.GEMINI_MODEL}...")
            logger.info("Using Gemini as LLM...")
            def gemini_runner(prompt_value):
                client = genai.Client(api_key=settings.GOOGLE_API_KEY, http_options={'api_version':'v1'})
                prompt_text = prompt_value.to_string()
                response = client.models.generate_content(
                    model=settings.GEMINI_MODEL, contents=prompt_text
                )
                return AIMessage(content=response.text)
            return RunnableLambda(gemini_runner, name="Gemini Call")

        providers = [
            ("sarvam", get_sarvam),
            ("gemini", get_gemini),
            ("openai", get_openai)
        ]

        # Order providers: start with the selected LLM_PROVIDER
        primary_provider = settings.LLM_PROVIDER.lower()
        sequence = []
        for pid, builder in providers:
            if pid == primary_provider:
                sequence.append((pid, builder))
                
        for pid, builder in providers:
            if pid != primary_provider:
                sequence.append((pid, builder))
                
        last_error = None
        for pid, builder in sequence:
            try:
                llm = builder()
                chain = chain_factory(llm)
                result = chain.invoke(
                    input_data, 
                    config={"run_name": name, "tags": tags, "metadata": metadata}
                )
                print(f"✅ {pid.capitalize()} response received")
                return result
            except Exception as e:
                print(f"❌ {pid.capitalize()} call failed: {e}")
                logger.error(f"{pid.capitalize()} call failed: {e}")
                last_error = e

        # If we reach here, all providers failed
        span.record_exception(last_error)
        span.set_status(trace.Status(trace.StatusCode.ERROR))
        
        # Check for Rate Limit to throw expected custom exception
        if last_error:
            error_str = str(last_error)
            import re
            
            # Explicitly match HTTP 429 error code or RESOURCE_EXHAUSTED status
            if re.search(r'\b429\b', error_str) or "RESOURCE_EXHAUSTED" in error_str:
                print(f"DEBUG RATE LIMIT MATCHER: Triggered by string: {error_str}")
                gemini_retry_after = None
                match = re.search(r"retryDelay': '([\d\.]+)s'", error_str)
                if match:
                    gemini_retry_after = match.group(1)
                
                from app.utils.exceptions import RateLimitException
                raise RateLimitException(
                    message=f"Rate limit exceeded on all available providers. Please try again later.",
                    retry_after=gemini_retry_after
                )

        raise last_error
