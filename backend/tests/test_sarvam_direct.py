import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

import json
def print_err(e):
    try:
        err_out = str(e)
        if hasattr(e, 'response') and e.response is not None:
            err_out = e.response.json()
        with open('sarvam_error.json', 'w', encoding='utf-8') as f:
            json.dump({'error': err_out}, f, indent=2)
        print("Logged error to sarvam_error.json")
    except Exception as ex:
        print("Failed to log:", ex)

def test_sarvam():
    print("--- TESTING SARVAM ---")
    
    llm = ChatOpenAI(
        model=settings.SARVAM_MODEL, 
        temperature=0,
        api_key=settings.SARVAM_API_KEY, 
        base_url="https://api.sarvam.ai/v1"
    )
    
    print("1. Testing basic message...")
    try:
        resp = llm.invoke([HumanMessage(content="Hello")])
        print("Success:", resp.content)
    except Exception as e:
        print_err(e)
        
    print("\n2. Testing with system message...")
    try:
        resp = llm.invoke([
            SystemMessage(content="You are a helpful assistant."),
            HumanMessage(content="Hello")
        ])
        print("Success:", resp.content)
    except Exception as e:
        print_err(e)

    print("\n3. Testing with bind_tools...")
    try:
        # Mock tool
        def get_weather(location: str):
            """Get weather"""
            pass
            
        llm_with_tools = llm.bind_tools([get_weather])
        resp = llm_with_tools.invoke([HumanMessage(content="What is the weather in London?")])
        print("Success. Tool calls:", resp.tool_calls)
    except Exception as e:
        print_err(e)

if __name__ == "__main__":
    test_sarvam()
