
from typing import List, Dict, Any, Optional
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.tools import tool

# Initialize the search run
search = DuckDuckGoSearchRun()

@tool(parse_docstring=True, tags=["tool", "search", "duckduckgo"])
def web_search(query: str) -> str:
    """
    Search the web for real-time information using DuckDuckGo.
    Use this tool when the user asks about current events, stock prices, news, or
    information that is unlikely to be in the internal SQL database.
    
    Args:
        query: The search query string.
    
    Returns:
        A summary of the search results.
    """
    try:
        return search.invoke(query)
    except Exception as e:
        return f"Error performing web search: {str(e)}"
