
from typing import List, Dict, Any, Optional
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.tools import tool

# Initialize the search run
search = DuckDuckGoSearchRun()

@tool(parse_docstring=True)
def web_search(query: str, user_role: str = "user") -> str:
    """
    Search the web for real-time information using DuckDuckGo.
    Use this tool when the user asks about current events, stock prices, news, or
    information that is unlikely to be in the internal SQL database.
    
    Args:
        query: The search query string.
        user_role: The role of the user (injected).
    
    Returns:
        A summary of the search results.
    """
    import re
    
    # 1. SSRF / Local Network Protection
    # Block localhost, 127.0.0.1, 0.0.0.0, private IPs, file://, ftp://
    blocked_patterns = [
        r"localhost",
        r"127\.0\.0\.1",
        r"0\.0\.0\.0",
        r"192\.168\.\d{1,3}\.\d{1,3}",
        r"10\.\d{1,3}\.\d{1,3}\.\d{1,3}",
        r"172\.(1[6-9]|2[0-9]|3[0-1])\.\d{1,3}\.\d{1,3}", # 172.16.x.x - 172.31.x.x
        r"file://",
        r"ftp://",
        r"gopher://"
    ]
    
    for pattern in blocked_patterns:
        if re.search(pattern, query, re.IGNORECASE):
            return f"Error: Search query blocked for security reasons (Matched restricted pattern: {pattern})."

    try:
        return search.invoke(query)
    except Exception as e:
        return f"Error performing web search: {str(e)}"
