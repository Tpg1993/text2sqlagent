
import sys
import os
import pytest
from unittest.mock import MagicMock

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.tools.sql_tools import list_tables, get_table_schema
from app.tools.search_tools import web_search

def test_rbac_sql_tools():
    print("--- Testing RBAC for SQL Tools ---")

    # 1. Test Admin Access (Should Succeed)
    print("\n1. Testing Admin Access (list_tables)...")
    try:
        # Simulate injection of user_role="admin"
        # Since we modified the tool to accept user_role, we pass it in invoke
        result = list_tables.invoke({"user_role": "admin"})
        print(f"Admin Result: {str(result)[:50]}...")
        if "Error" in str(result) and "Access Denied" in str(result):
             print("❌ Admin was denied access!")
        else:
             print("✅ Admin access granted.")
    except Exception as e:
        print(f"❌ Admin access failed with error: {e}")

    # 2. Test User Access (Should Fail)
    print("\n2. Testing User Access (list_tables)...")
    try:
        result = list_tables.invoke({"user_role": "user"})
        print(f"User Result: {result}")
        if "Access Denied" in str(result):
            print("✅ User correctly denied access.")
        else:
            print("❌ User was NOT denied access (Security Risk!)")
    except Exception as e:
        # If it raised an exception, that's also a valid denial depending on implementation
        if "Access Denied" in str(e):
             print("✅ User correctly denied access (Exception raised).")
        else:
             print(f"❌ Unexpected error: {e}")

def test_rbac_search_tool():
    print("\n--- Testing RBAC for Search Tool ---")
    # Search should be open to all
    try:
        print("Testing User Access (web_search)...")
        # limit result to avoid network spam/latency
        # web_search might not accept user_role yet if we didn't add it, 
        # but the plan said to add it.
        # check if it accepts it
        try:
            result = web_search.invoke({"query": "test", "user_role": "user"})
            print("✅ User allowed to search.")
        except TypeError:
            print("⚠️ web_search does not accept user_role yet (Expected if not updated).")
            # This is fine if we decided not to restrict search
            result = web_search.invoke({"query": "test"})
            print("✅ User allowed to search (Standard arg).")

    except Exception as e:
        print(f"❌ Search failed: {e}")

if __name__ == "__main__":
    test_rbac_sql_tools()
    test_rbac_search_tool()
