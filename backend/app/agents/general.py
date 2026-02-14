
from app.utils.state import AgentState
from app.config import settings
from langchain_google_genai import ChatGoogleGenerativeAI
from app.tools.search_tools import web_search

def general_node(state: AgentState):
    """
    Handles general queries (e.g., small talk, greetings, or questions about external world).
    Uses DuckDuckGo search if the LLM decides it needs external information.
    """
    print("--- GENERAL AGENT ---")
    
    # Initialize Gemini with Search Tool
    llm = ChatGoogleGenerativeAI(
        model=settings.GEMINI_MODEL,
        temperature=0,
        google_api_key=settings.GOOGLE_API_KEY
    )
    
    # Bind the search tool
    llm_with_tools = llm.bind_tools([web_search])
    
    # System Prompt
    SYS_PROMPT = """You are a helpful assistant.
    If the user asks about current events, news, or specific external facts (like 'stock price', 'who is CEO'), 
    you MUST use the `web_search` tool to get the answer.
    
    If the user just says 'hello' or asks a general question, just answer politely.
    """
    
    messages = [{"role": "system", "content": SYS_PROMPT}] + state['messages']
    
    try:
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}
    except Exception as e:
        print(f"General Agent Error: {e}")
        return {"messages": [f"I encountered an error: {str(e)}"]}
