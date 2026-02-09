from sqlalchemy import text
import os
from app.db.session import engine
from app.config import settings

def init_db():
    sql_path = os.path.join(settings.BASE_DIR, "data/sample_sales.sql")
    if not os.path.exists(sql_path):
        print("SQL file not found.")
        return
        
    with open(sql_path, "r") as f:
        sql_script = f.read()
    
    # Split by semicolon simple check
    statements = sql_script.split(';')
    
    with engine.connect() as conn:
        for stmt in statements:
            if stmt.strip():
                conn.execute(text(stmt))
        conn.commit()
    print("Database initialized.")

if __name__ == "__main__":
    init_db()
