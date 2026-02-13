"""
Simple test for HITL sensitivity detection only.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend'))

from app.utils.hitl import approval_manager

print("=" * 60)
print("🧪 HITL Sensitivity Detection Test")
print("=" * 60)

# Test 1: Sensitive query
query1 = "SELECT * FROM customers WHERE id = 1"
is_sensitive1, tables1 = approval_manager.is_query_sensitive(query1)

print(f"\nTest 1: {query1}")
print(f"  Is Sensitive: {is_sensitive1}")
print(f"  Sensitive Tables: {tables1}")
print(f"  Result: {'✅ PASS' if is_sensitive1 else '❌ FAIL'}")

# Test 2: Non-sensitive query
query2 = "SELECT * FROM products WHERE price > 100"
is_sensitive2, tables2 = approval_manager.is_query_sensitive(query2)

print(f"\nTest 2: {query2}")
print(f"  Is Sensitive: {is_sensitive2}")
print(f"  Sensitive Tables: {tables2}")
print(f"  Result: {'✅ PASS' if not is_sensitive2 else '❌ FAIL'}")

# Test 3: Create approval request
if is_sensitive1:
    request = approval_manager.create_approval_request(
        query=query1,
        sensitive_tables=tables1,
        user_id="test-user"
    )
    print(f"\nTest 3: Approval Request Created")
    print(f"  Request ID: {request.request_id}")
    print(f"  Status: {request.status.value}")
    print(f"  Result: ✅ PASS")

# Test 4: Get pending approvals
pending = approval_manager.get_pending_requests()
print(f"\nTest 4: Pending Approvals")
print(f"  Count: {len(pending)}")
print(f"  Result: {'✅ PASS' if len(pending) > 0 else '❌ FAIL'}")

print("\n" + "=" * 60)
print("✅ HITL Sensitivity Detection Test Completed")
print("=" * 60)
