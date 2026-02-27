from sqlalchemy import inspect
from app.db.session import engine
from typing import Dict, List

def get_schema_text() -> str:
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    schema_text = ""
    for table in table_names:
        columns = inspector.get_columns(table)
        schema_text += f"Table: {table}\n"
        for col in columns:
            schema_text += f"- {col['name']} ({col['type']})\n"
    return schema_text

def get_valid_tables_and_columns() -> Dict[str, List[str]]:
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    valid_schema = {}
    for table in table_names:
        columns = inspector.get_columns(table)
        valid_schema[table.lower()] = [col['name'].lower() for col in columns]
    return valid_schema
