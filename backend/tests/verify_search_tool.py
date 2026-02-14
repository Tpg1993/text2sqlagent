
import sys
import os
import json

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.agents.general import general_node
from app.utils.state import AgentState

def test_search_tool():
    print("Testing Web Search Tool...")
    
    # Test Case 1: Search Query
    print("\n--- Test 1: Search Query ---")
    state_search = {
        "messages": [], # General agent adds system prompt
        "question": "Who is the CEO of OpenAI in 2024?"
    }
    
    # We need to simulate the message history appropriately if the agent relies on it
    # But general_node just takes state['messages'] and appends system prompt.
    # It doesn't use state['question'] directly in the prompt, it uses messages.
    # So we should put the question in messages.
    state_search["messages"] = [{"role": "user", "content": state_search["question"]}]

    try:
        result = general_node(state_search)
        response = result["messages"][0]
        
        print(f"Tool Calls: {response.tool_calls}")
        print(f"Content: {response.content}")
        
        if response.tool_calls and response.tool_calls[0]['name'] == 'web_search':
            print("✅ Agent correctly decided to search!")
        else:
            print("❌ Agent did NOT search (unexpected behavior).")
            
    except Exception as e:
        print(f"Error: {e}")

    # Test Case 2: Chit Chat
    print("\n--- Test 2: Chit Chat ---")
    state_chat = {
        "messages": [{"role": "user", "content": "Hello, how are you?"}]
    }
    
    try:
        result = general_node(state_chat)
        response = result["messages"][0]
        
        if not response.tool_calls:
            print(f"✅ Agent correctly replied without search: {response.content}")
        else:
            print(f"❌ Agent searched unnecessarily: {response.tool_calls}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_search_tool()
