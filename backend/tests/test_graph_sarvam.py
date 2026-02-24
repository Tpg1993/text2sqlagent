import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.graphs.agent_graph import graph
from langchain_core.messages import HumanMessage

def test_graph():
    
    config = {
        "configurable": {
            "thread_id": "test_1",
            "user_id": "admin",
            "session_id": "test_session_1"
        }
    }
    
    inputs = {
        "question": "Show me all customers from California",
        "messages": [],
        "retry_count": 0,
        "session_id": "test_session_1",
        "user_id": "admin",
        "user_role": "admin"
    }
    
    try:
        print("Invoking graph...")
        result = graph.invoke(inputs, config)
        print("PASS. Finished executing graph. Here are the resulting messages:")
        import json
        
        # We need to serialize the AIMessage objects and other LangChain types
        def serialize_message(m):
            if hasattr(m, 'type'):
                return {"type": m.type, "content": m.content, "tool_calls": getattr(m, 'tool_calls', [])}
            return str(m)

        serializable_result = {"messages": [serialize_message(m) for m in result.get("messages", [])]}
        # Also copy other top-level keys
        for k, v in result.items():
            if k != "messages":
                serializable_result[k] = str(v)
                
        with open("sarvam_result.json", "w", encoding="utf-8") as f:
            json.dump(serializable_result, f, indent=4)
        print("Result saved to sarvam_result.json")
    except Exception as e:
        import traceback
        with open("sarvam_result.json", "w", encoding="utf-8") as f:
            f.write(traceback.format_exc())
        print(f"Graph execution failed: {e}")

if __name__ == "__main__":
    test_graph()
