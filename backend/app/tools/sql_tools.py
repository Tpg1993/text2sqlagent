
from typing import List, Dict, Any, Optional
from langchain_core.tools import tool
from sqlalchemy import inspect, text
from app.db.session import engine

@tool(parse_docstring=True)
def list_tables(user_role: str = "user") -> List[str]:
    """
    List all tables in the database.
    Use this tool to discover what data is available.
    
    Args:
        user_role: The role of the user (injected).
    
    Returns:
        List[str]: A list of table names.
    """
    if user_role != "admin":
        return ["Error: Access Denied. Only admins can list tables."]
    try:
        inspector = inspect(engine)
        return inspector.get_table_names()
    except Exception as e:
        return [f"Error listing tables: {str(e)}"]

@tool(parse_docstring=True)
def get_table_schema(table_name: str, user_role: str = "user") -> str:
    """
    Get the schema (columns and types) for a specific table.
    Use this tool to understand the structure of a table before writing a query.
    
    Args:
        table_name: The name of the table to inspect.
        user_role: The role of the user (injected).
    
    Returns:
        str: A text description of the table columns and their types.
    """
    if user_role != "admin":
        return "Error: Access Denied. Only admins can view schema."
    try:
        inspector = inspect(engine)
        if table_name not in inspector.get_table_names():
            return f"Error: Table '{table_name}' does not exist."
            
        columns = inspector.get_columns(table_name)
        schema_text = f"Table: {table_name}\n"
        for col in columns:
            schema_text += f"- {col['name']} ({col['type']})\n"
        
        # Add foreign keys if any
        fks = inspector.get_foreign_keys(table_name)
        if fks:
            schema_text += "Foreign Keys:\n"
            for fk in fks:
                schema_text += f"- {fk['constrained_columns']} -> {fk['referred_table']}.{fk['referred_columns']}\n"
                
        return schema_text
    except Exception as e:
        return f"Error getting schema for {table_name}: {str(e)}"

@tool(parse_docstring=True)
def get_sample_rows(table_name: str, limit: int = 3) -> List[Dict[str, Any]]:
    """
    Get sample rows from a table to understand the data format.
    Use this to see actual values (e.g., is 'status' a string or int?).
    
    Args:
        table_name: The name of the table.
        limit: Number of rows to return (default 3).
    
    Returns:
        List[Dict]: A list of row dictionaries.
    """
    try:
        with engine.connect() as connection:
            # Use text() for safe SQL execution
            query = text(f"SELECT * FROM {table_name} LIMIT :limit")
            result = connection.execute(query, {"limit": limit})
            # Convert rows to dicts
            return [dict(row._mapping) for row in result]
    except Exception as e:
        return [{"error": f"Error fetching samples from {table_name}: {str(e)}"}]
