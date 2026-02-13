"""
Test script for HITL (Human-in-the-Loop) approval workflow.
Tests that sensitive queries are correctly flagged and require approval.
"""
import sys
import os
import asyncio

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.graphs.agent_graph import graph
from app.utils.hitl import approval_manager

async def test_hitl():
    print("=" * 60)
    print("🧪 HITL Approval Workflow Test")
    print("=" * 60)
    
    # Test 1: Sensitive query (should require approval)
    print("\n📋 Test 1: Sensitive Query (SELECT from customers)")
    print("-" * 60)
    
    sensitive_query_state = {
        "question": "Show me all customers",
        "messages": [],
        "retry_count": 0,
        "session_id": "test-session-1"
    }
    
    result = await graph.ainvoke(sensitive_query_state)
    
    print(f"\n✅ Result:")
    print(f"   Requires Approval: {result.get('requires_approval', False)}")
    print(f"   Approval Status: {result.get('approval_status', 'N/A')}")
    print(f"   Approval Request ID: {result.get('approval_request_id', 'N/A')}")
    print(f"   Sensitive Tables: {result.get('sensitive_tables', [])}")
    
    if result.get('requires_approval'):
        print(f"\n✅ TEST PASSED: Sensitive query correctly flagged for approval")
    else:
        print(f"\n❌ TEST FAILED: Sensitive query was not flagged")
    
    # Test 2: Check pending approvals
    print("\n\n📋 Test 2: Pending Approvals")
    print("-" * 60)
    
    pending = approval_manager.get_pending_requests()
    print(f"   Pending Requests: {len(pending)}")
    
    if pending:
        for req in pending:
            print(f"\n   Request ID: {req.request_id}")
            print(f"   Query: {req.query}")
            print(f"   Sensitive Tables: {', '.join(req.sensitive_tables)}")
            print(f"   Status: {req.status.value}")
    
    # Test 3: Non-sensitive query (should NOT require approval)
    print("\n\n📋 Test 3: Non-Sensitive Query (SELECT from products)")
    print("-" * 60)
    
    normal_query_state = {
        "question": "Show me all products",
        "messages": [],
        "retry_count": 0,
        "session_id": "test-session-2"
    }
    
    result2 = await graph.ainvoke(normal_query_state)
    
    print(f"\n✅ Result:")
    print(f"   Requires Approval: {result2.get('requires_approval', False)}")
    
    if not result2.get('requires_approval'):
        print(f"\n✅ TEST PASSED: Non-sensitive query did not require approval")
    else:
        print(f"\n❌ TEST FAILED: Non-sensitive query was incorrectly flagged")
    
    print("\n" + "=" * 60)
    print("✅ HITL Test Completed")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_hitl())
