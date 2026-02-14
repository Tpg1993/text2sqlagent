
import sys
try:
    import duckduckgo_search
    print(f"duckduckgo_search version: {getattr(duckduckgo_search, '__version__', 'unknown')}")
    print(f"duckduckgo_search file: {duckduckgo_search.__file__}")
except ImportError:
    print("duckduckgo_search not found")

try:
    from duckduckgo_search import DDGS
    print("DDGS imported from duckduckgo_search")
except ImportError as e:
    print(f"DDGS import failed: {e}")

try:
    import ddgs
    print(f"ddgs version: {getattr(ddgs, '__version__', 'unknown')}")
except ImportError:
    print("ddgs module not found")
