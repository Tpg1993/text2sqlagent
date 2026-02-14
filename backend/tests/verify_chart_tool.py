
import sys
import os
import json

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.agents.chart import chart_node

def test_chart_generation():
    print("Testing Chart Generation with Tool Calling...")
    
    # Mock State
    state = {
        "question": "Show me sales by product for Jan 2024",
        "sql_result": [
            {"product": "Laptop", "sales": 5000, "month": "Jan"},
            {"product": "Mouse", "sales": 1200, "month": "Jan"},
            {"product": "Keyboard", "sales": 800, "month": "Jan"},
            {"product": "Monitor", "sales": 3000, "month": "Jan"}
        ]
    }
    
    try:
        result = chart_node(state)
        spec = result.get("visualization_spec")
        
        if spec:
            print("\n✅ Chart Generated Successfully!")
            print(json.dumps(spec, indent=2))
            
            # Basic validation
            assert spec["type"] == "bar" or spec["type"] == "pie", "Unexpected chart type"
            assert "data" in spec, "Missing data"
            assert spec["title"], "Missing title"
            print("\nValidation Passed.")
        else:
            print("\n❌ Failed to generate chart (None returned)")
            
    except Exception as e:
        print(f"\n❌ Error during execution: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_chart_generation()
