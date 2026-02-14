
import sys
import os
import pytest
from unittest.mock import MagicMock

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.agents.schema import fetch_schema_node
from app.agents.execute import execute_node

def test_agent_rbac():
    print("--- Testing Agent-Level RBAC ---")

    # 1. Test Schema Access
    print("\n1. Testing fetch_schema_node...")
    
    # Case A: Admin (Should Succeed)
    state_admin = {
        "security_context": {"user_role": "admin"}
    }
    res_admin = fetch_schema_node(state_admin)
    if res_admin.get("schema"):
        print("✅ Admin can fetch schema.")
    else:
        print(f"❌ Admin blocked from schema: {res_admin}")

    # Case B: User (Should Fail)
    state_user = {
        "security_context": {"user_role": "user"}
    }
    res_user = fetch_schema_node(state_user)
    if "Access Denied" in str(res_user.get("error")):
        print("✅ User correctly blocked from schema.")
    else:
        print(f"❌ User NOT blocked from schema: {res_user}")

    # 2. Test Execute Access
    print("\n2. Testing execute_node...")
    
    # Case A: Admin (Should Try to Execute)
    # Note: It will fail on SQL execution because we didn't mock DB, 
    # but we check if it PASSED the security check.
    state_exec_admin = {
        "security_context": {"user_role": "admin"},
        "sql_query": "SELECT 1"
    }
    res_exec_admin = execute_node(state_exec_admin)
    # If error is about DB connection/table, it passed security. 
    # If error is "Access Denied", it failed security.
    if "Access Denied" not in str(res_exec_admin.get("error")):
        print("✅ Admin passed security check (Execution attempted).")
    else:
        print(f"❌ Admin blocked from execution: {res_exec_admin}")

    # Case B: User (Should Fail Security Check)
    state_exec_user = {
        "security_context": {"user_role": "user"},
        "sql_query": "SELECT 1"
    }
    res_exec_user = execute_node(state_exec_user)
    if "Access Denied" in str(res_exec_user.get("error")):
        print("✅ User correctly blocked from execution.")
    else:
        print(f"❌ User NOT blocked from execution: {res_exec_user}")

if __name__ == "__main__":
    test_agent_rbac()
