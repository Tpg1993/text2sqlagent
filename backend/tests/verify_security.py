import asyncio
import sys
import os
from datetime import datetime

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.utils.security import security_manager, Permission, AgentIdentity
from app.graphs.agent_graph import graph

async def run_test_case(name, target_node, permission_to_revoke=None, expected_result="SUCCESS"):
    print(f"\n----------------------------------------------------------------")
    print(f"🧪 TEST CASE: {name}")
    print(f"----------------------------------------------------------------")
    
    # Snapshot original identity
    original_identity = security_manager.policy.get_identity(target_node)
    
    if permission_to_revoke:
        print(f"🔧 SETUP: Revoking '{permission_to_revoke.value}' from '{target_node}'")
        # Create crippled identity
        new_perms = [p for p in original_identity.permissions if p != permission_to_revoke]
        crippled_identity = AgentIdentity(name=target_node, role=original_identity.role, permissions=new_perms)
        security_manager.policy.identities[target_node] = crippled_identity
        
    inputs = {
        "question": "Show me sales.", # Logic doesn't matter much, just hitting the nodes
        "messages": [],
        "retry_count": 0,
        "session_id": f"test-{name.lower().replace(' ', '-')}"
    }
    
    try:
        # We can't easily target a specific node in isolation without mocking the whole state
        # So we run the graph. If we revoke EXECUTE, we expect failure at EXECUTE step.
        # If we revoke GENERATE, we expect failure at GENERATE step.
        
        print(f"▶️ Executing Graph...")
        result = await graph.ainvoke(inputs)
        final_msg = str(result.get("messages", [""])[-1])
        
        # Check result
        if "Access Denied" in final_msg or "Security Error" in final_msg:
            actual_result = "BLOCKED"
        else:
            actual_result = "ALLOWED"
            
        print(f"📝 Result: {actual_result}")
        
        if actual_result == expected_result:
            print("✅ TEST PASSED")
        else:
            print(f"❌ TEST FAILED (Expected {expected_result}, got {actual_result})")
            
    except Exception as e:
        print(f"⚠️ Exception: {e}")
        
    finally:
        # Restore
        if permission_to_revoke:
            security_manager.policy.identities[target_node] = original_identity
            print(f"Reverted permissions for {target_node}")

async def main():
    print(f"🚀 STARTING COMPREHENSIVE SECURITY AUDIT")
    print(f"📅 {datetime.now()}")
    
    # 1. Happy Path
    await run_test_case(
        "Standard SQL Query (Happy Path)", 
        "execute", 
        permission_to_revoke=None, 
        expected_result="ALLOWED"
    )
    
    # 2. Block Generation
    await run_test_case(
        "Unauthorized Generation (Revoke WRITE)", 
        "generate", 
        permission_to_revoke=Permission.GENERATE_SQL, 
        expected_result="BLOCKED"
    )
    
    # 3. Block Execution
    await run_test_case(
        "Unauthorized Execution (Revoke EXECUTE)", 
        "execute", 
        permission_to_revoke=Permission.EXECUTE_SQL, 
        expected_result="BLOCKED"
    )

    # 4. Block RAG Access
    await run_test_case(
        "Unauthorized RAG Access (Revoke READ_VECTOR_DB)", 
        "retrieve", 
        permission_to_revoke=Permission.READ_VECTOR_DB, 
        expected_result="BLOCKED"
    )

    # 5. Block Chart Generation 
    # (Note: Need a query that triggers charts, but we can force the node execution logic by revoking permission)
    await run_test_case(
        "Unauthorized Chart Generation (Revoke GENERATE_CHART)", 
        "chart", 
        permission_to_revoke=Permission.GENERATE_CHART, 
        expected_result="BLOCKED"
    )

    # 6. Block Orchestration (The Brain)
    await run_test_case(
        "Unauthorized Routing (Revoke ROUTE_REQUEST)", 
        "orchestrator", 
        permission_to_revoke=Permission.ROUTE_REQUEST, 
        expected_result="BLOCKED"
    )

if __name__ == "__main__":
    asyncio.run(main())
