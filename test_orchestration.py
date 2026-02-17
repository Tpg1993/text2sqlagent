import os
import sys

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.agents.orchestrator import orchestrator_node
from app.utils.state import AgentState

def test_routing(question):
    print(f"Testing question: {question}")
    state = {
        "question": question,
        "messages": [],
        "session_id": "test_session"
    }
    result = orchestrator_node(state)
    print(f"Resulting intent: {result['intent']}")

if __name__ == "__main__":
    test_routing("What are the shipping options?")
