
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.tools.sql_tools import list_tables, get_table_schema, get_sample_rows

def test_sql_tools():
    print("--- Testing SQL Tools ---")

    # 1. Test list_tables
    print("\n1. Testing list_tables()...")
    tables = list_tables.invoke({})
    print(f"Tables found: {tables}")
    
    if not tables or "Error" in str(tables):
        print("❌ list_tables failed")
        return

    # 2. Test get_table_schema
    first_table = tables[0]
    print(f"\n2. Testing get_table_schema('{first_table}')...")
    schema = get_table_schema.invoke({"table_name": first_table})
    print(f"Schema:\n{schema}")
    
    if "Error" in schema:
         print("❌ get_table_schema failed")
         return

    # 3. Test get_sample_rows
    print(f"\n3. Testing get_sample_rows('{first_table}', limit=2)...")
    rows = get_sample_rows.invoke({"table_name": first_table, "limit": 2})
    print(f"Rows:\n{rows}")
    
    if isinstance(rows, list) and len(rows) > 0 and "error" not in rows[0]:
        print("\n✅ All SQL Tools Verified Successfully!")
    else:
        print("\n❌ get_sample_rows failed or returned empty")

if __name__ == "__main__":
    test_sql_tools()
