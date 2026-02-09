from sqlalchemy import inspect
from app.db.session import engine

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
