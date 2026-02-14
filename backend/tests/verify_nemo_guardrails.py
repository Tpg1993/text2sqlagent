
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.utils.guardrails import get_guardrail_manager

def test_guardrails():
    gm = get_guardrail_manager()
    print("Guardrail Manager initialized.")
    
    # safe query
    safe_response = "Here are the total sales for last month: $5000."
    print(f"\nTesting safe response: '{safe_response}'")
    valid, msg = gm.validate_output(safe_response)
    print(f"Valid: {valid}, Message: {msg}")
    
    # Unsafe query (simulated based on config)
    # The config prompts check for "inappropriate" or "harmful" content.
    unsafe_response = "To hack the database, you can use SQL injection..."
    print(f"\nTesting unsafe response: '{unsafe_response}'")
    valid, msg = gm.validate_output(unsafe_response)
    print(f"Valid: {valid}, Message: {msg}")

if __name__ == "__main__":
    test_guardrails()
